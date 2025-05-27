"""
Notifier class
"""
import threading
import asyncio
import time
from datetime import datetime as dt, timezone

from telegram import Update
from telegram.ext import ContextTypes
import schedule

from crypto_api import CryptoAPI
from db import Db
from logger import logger

class Notifier:
    """
    Handles notifications
    """
    def __init__(self):
        self.db = Db()
        self.crypto_api = CryptoAPI()

        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()

    @staticmethod
    async def send_scheduled_message(bot, chat_id, message_function):
        """

        :param bot: bot app for sending messages
        :param chat_id: chat id
        :param message_function: function for the command

        Sends the message in the chat
        """
        reply = message_function()

        if isinstance(reply, dict):
            reply["img"].seek(0)

            await bot.send_photo(chat_id, photo=reply["img"], caption=reply["reply"], parse_mode="HTML")
        else:
            await bot.send_message(chat_id, reply, parse_mode="HTML")

    def run_async_send_scheduled_message(self, bot, notification_id, chat_id, message_function):
        """

        :param bot: bot app for sending messages
        :param notification_id: notification id
        :param chat_id: chat id
        :param message_function: function for the command

        Runs the message sending coroutine and updates the last_sent date in database
        """
        db = Db()
        db.update_notification_date(notification_id)
        notification = db.select_notification(notification_id)
        db.conn_close()
        if notification:
            asyncio.run_coroutine_threadsafe(self.send_scheduled_message(bot, chat_id, message_function), self.loop)

    def schedule_new_message(self, bot, notification_id, chat_id, freq, message_function):
        """

        :param bot: bot app for sending messages
        :param notification_id: notification id
        :param chat_id: chat id
        :param freq: notification frequency
        :param message_function: function for the command

        Starts the schedule of sending the message in the chat every freq seconds
        """
        schedule.every(freq).seconds.do(
            lambda: self.run_async_send_scheduled_message(bot, notification_id, chat_id, message_function))
        while True:
            schedule.run_pending()
            time.sleep(1)

    def f_notify_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """

        :param update: telegram chat update
        :param context: telegram message context

        Sets up a notification for a command
        """
        try: # attribute validation
            freq_val = int(context.args[0])
            freq_unit = context.args[1]
            command = context.args[2]
            coin = context.args[3]
            currency = context.args[4]
            days = int(context.args[5]) if 5 < len(context.args) else 0

            if freq_val <= 0:
                raise ValueError

            match freq_unit:
                case "m" | "min" | "mins" | "minute" | "minutes":
                    freq_unit = "minutes"
                    freq_val_sec = freq_val * 60
                case "h" | "hour" | "hours":
                    freq_unit = "hours"
                    freq_val_sec = freq_val * 3600
                case "d" | "day" | "days":
                    freq_unit = "days"
                    freq_val_sec = freq_val * 86400
                case _:
                    raise ValueError

            coin_list = self.crypto_api.get_coin_list()
            if coin_list != "Error API":
                if coin not in coin_list:
                    raise ValueError
            else:
                bot_reply = "API error raised, while validating coin. Please try again later."
                return bot_reply

            currency_list = self.crypto_api.get_currency_list()
            if currency_list != "Error API":
                if currency not in currency_list:
                    raise ValueError
            else:
                bot_reply = "API error raised, while validating currency. Please try again later."
                return bot_reply
        except ValueError:
            bot_reply = "Please enter valid information (e.g. <i>notify 1 min price_chart bitcoin usd 30</i>)"
            return bot_reply
        except IndexError:
            bot_reply = "Missing argument (e.g. <i>notify 1 min price_chart bitcoin usd 30</i>)"
            return bot_reply

        try: # command validation
            getattr(self.crypto_api, "f_" + command + "_command")
        except AttributeError:
            logger.error("Setting up notification raised an error (invalid command)")
            bot_reply = f"There is no command {command}"
            return bot_reply

        telegram_id = update.message.from_user.id
        chat_id = update.message.chat.id
        notification_id = self.db.set_notification(telegram_id, chat_id, freq_val_sec, command, coin, currency, days)
        bot = context.application.bot

        args = {
            "coin": coin,
            "currency": currency,
            "days": int(days),
            "notification_id": notification_id
        }

        threading.Thread(target=self.schedule_new_message, args=(
        bot, notification_id, chat_id, freq_val_sec, lambda: getattr(self.crypto_api, "f_" + command + "_command")(args)),
                         daemon=True).start()

        bot_reply = f"You are now being notified with the {command} command of {coin} in {currency} every {freq_val} {freq_unit}"

        return bot_reply

    def send_first_to_schedule(self, bot, notification_id, chat_id, interval, command, args):
        """

        :param bot: bot app for sending messages
        :param notification_id: notification id
        :param chat_id: chat id
        :param interval: notification interval
        :param command: notification command
        :param args: command arguments

        Send the notification's message after the interval time minus time passed while the script wasn't active
        and starts the schedule with the normal interval
        """
        self.run_async_send_scheduled_message(bot, notification_id, chat_id,
                                              lambda: getattr(self.crypto_api, "f_" + command + "_command")(args))

        threading.Thread(target=self.schedule_new_message, args=(
        bot, notification_id, chat_id, interval, lambda: getattr(self.crypto_api, "f_" + command + "_command")(args)),
                         daemon=True).start()

    def resume_notification(self, bot, notification_id, chat_id, interval, command, coin, currency, days):
        """

        :param bot: bot app for sending messages
        :param notification_id: notification id
        :param chat_id: chat id
        :param interval: notification interval
        :param command: notification command
        :param coin: command coin
        :param currency: command currency
        :param days: command days (in charts)

        Starts a function for the notification's message after the delay (interval time minus time passed while the script wasn't active, which is min. 0)
        and start the regular notification timer. In other words, sends the first message after a delay and after that goes back to the normal interval
        """
        args = {
            "coin": coin,
            "currency": currency,
            "days": int(days),
            "notification_id": notification_id
        }

        db = Db()
        last_sent = db.get_notification_last_sent(notification_id)
        db.conn_close()

        time_pased = time.time() - dt.strptime(last_sent, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc).timestamp()
        delay = max(0, interval - time_pased)

        logger.info(f"Resuming notification {notification_id}")

        threading.Timer(delay, self.send_first_to_schedule,
                        args=(bot, notification_id, chat_id, interval, command, args)).start()
