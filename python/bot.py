"""
Telegram bot class
"""
from functools import wraps

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

from notifier import Notifier
from crypto_api import CryptoAPI
from db import Db
from lib import seconds_convert
from logger import logger


class TelegramBot:
    """
    Handles the bot
    """
    def __init__(self):
        self.bot_token = "8145193204:AAHtiVS05KEP6nkLwZfFRd5D2hv4NRzb4MM"
        self.bot_username = "@amputate_bot"

        self.crypto_api = CryptoAPI()
        self.db = Db()
        self.notifier = Notifier()

        self.delete_select = 1

        self.start_bot()

    def restore_notifications(self, bot):
        """

        :param bot: bot app used for sending messages
        Resumes each non-closed notification
        """
        logger.info("Restoring notifications...")
        notifications = self.db.select_all_notifications()
        for notification in notifications:
            (notification_id, telegram_id, chat_id, interval, command, coin, currency, days, _) = notification
            self.notifier.resume_notification(bot, notification_id, chat_id, interval, command, coin, currency, days)

    @staticmethod
    def log_command(func):
        """

        :param func: command function
        :return: wrapper that logs the function and then calls the actual function
        """

        @wraps(func)
        async def command_wrapper(self, update, context, *args, **kwargs):
            """
            async because the functions for commands are async
            :param self: class
            :param update: telegram chat update
            :param context: telegram message context
            :param args: it can work for any number of arguments
            :param kwargs: same but for named arguments
            :return: wrapper
            """
            user = update.effective_user
            first_name = user.first_name
            last_name = user.last_name if user.last_name else ""
            logger.info(
                f"User {user.id} ({first_name} {last_name}) called command: {func.__name__}"
            )
            return await func(self, update, context, *args, **kwargs)

        return command_wrapper

    # COMMANDS
    @log_command
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """

        :param update: telegram chat update
        :param context: telegram message context
        Sends a response for the start command
        """
        _ = context
        self.db.register_user(update.message.from_user.id)
        await update.message.reply_text("Hello! I am ready to glitch the system for infinite money glitch (before they patch).")

    @log_command
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """

        :param update: telegram chat update
        :param context: telegram message context
        Sends a response for the help command
        """
        _ = context
        await update.message.reply_text("""Type "/" for command list\n If you need further help on how to use commands, you can visit the documentation: https://shorturl.at/cdtVR""")

    @log_command
    async def my_notifications_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """

        :param update: telegram chat update
        :param context: telegram message context
        Sends a list of the user's active notifications
        """
        _ = context
        notifications = self.db.select_user_notifications(update.message.from_user.id)
        if notifications:
            reply = "Here is the list of your notifications:\n"
            i = 0
            for notification in notifications:
                i += 1
                if notification[7] != 0 and notification[7]:
                    days = f"{notification[7]} days"
                else:
                    days = ""

                reply += f"{i}: {seconds_convert(notification[3])} {notification[4]} {notification[5]} {notification[6]} {days}\n"
        else:
            reply = "You have no active notifications."

        await update.message.reply_text(reply)

    @log_command
    async def delete_notifications_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """

        :param update: telegram chat update
        :param context: telegram message context
        Sends a list of the user's active notifications and starts 'handle_delete_selection' via 'delete_select'
        """
        await self.my_notifications_command(update, context)
        notifications = self.db.select_user_notifications(update.message.from_user.id)
        if notifications:
            await update.message.reply_text("Reply with the number of the notification to delete.")
            return self.delete_select

    @log_command
    async def handle_delete_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """

        :param update: telegram chat update
        :param context: telegram message context

        Follow-up function to 'delete_notifications_command' that gives the option to delete a notification by typing a number
        """
        _ = context
        notifications = self.db.select_user_notifications(update.message.from_user.id)
        try:
            if notifications:
                notif_dict = {}
                i = 0
                for notification in notifications:
                    i += 1
                    notif_dict[i] = int(notification[0])

                user_input = update.message.text.strip()
                if user_input.isdigit() and len(user_input.split()) == 1:
                    selected_index = int(user_input)
                    self.db.delete_notification(notif_dict[selected_index])
                    await update.message.reply_text(f"Deleted notification {selected_index}")
                else:
                    raise Exception
        except Exception as e:
            await update.message.reply_text("Invalid input. Please enter a valid number.")
            logger.error(f"Error type {type(e).__name__}: {e}")

        return ConversationHandler.END

    @log_command
    async def current_price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """

        :param update: telegram chat update
        :param context: telegram message context
        Sends a response from the current price command function in the crypto api class
        """
        try:
            args = {
                "coin": context.args[0],
                "currency": context.args[1]
            }

            await update.message.reply_text(self.crypto_api.f_current_price_command(args), parse_mode="HTML")
        except IndexError:
            await update.message.reply_text("Missing token or currency (e.g. <i>current_price bitcoin usd</i>)", parse_mode="HTML")

    @log_command
    async def price_chart_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """

        :param update: telegram chat update
        :param context: telegram message context
        Sends a response (chart) from the price days command function in the crypto api class
        """
        try:
            args = {
                "coin": context.args[0],
                "currency": context.args[1],
                "days": context.args[2]
            }

            reply = self.crypto_api.f_price_chart_command(args)

            if type(reply) == dict:
                await update.message.reply_photo(photo=reply["img"], caption=reply["reply"])
            else:
                await update.message.reply_text(reply, parse_mode="HTML")
        except IndexError:
            await update.message.reply_text("Missing argument (e.g. <i>price_chart bitcoin usd 30</i>)", parse_mode="HTML")

    @log_command
    async def price_candlestick_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """

        :param update: telegram chat update
        :param context: telegram message context
        Sends a response (candlestick chart) from the price days command function in the crypto api class
        """
        try:
            args = {
                "coin": context.args[0],
                "currency": context.args[1],
                "days": context.args[2]
            }

            reply = self.crypto_api.f_price_candlestick_command(args)
            if type(reply) == dict:
                await update.message.reply_photo(photo=reply["img"], caption=reply["reply"])
            else:
                await update.message.reply_text(reply, parse_mode="HTML")
        except IndexError:
            await update.message.reply_text("Missing argument (e.g. <i>price_candlestick bitcoin usd 30</i>)", parse_mode="HTML")

    @log_command
    async def notify_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """

        :param update: telegram chat update
        :param context: telegram message context
        Starts to send periodic price information to the telegram chat with the notify price command funtion
        """
        reply = self.notifier.f_notify_command(update, context)
        await update.message.reply_text(reply, parse_mode="HTML")

    # RESPONSES
    @staticmethod
    def handle_response(text: str) -> str:
        """

        :param text: message sent by the user
        Sends a response to non-command messages
        """
        lower_text: str = text.lower()
        if "hello" in lower_text:
            return "What's up, ready to abuse the system?💸💸"
        if "what" in lower_text:
            return "Vorp? 👽"

        return "Use a command first"

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """

        :param update: telegram chat update
        :param context: telegram message context
        Handles the user's message
        """
        _ = context
        message_type = update.message.chat.type  # group or private chat
        text: str = update.message.text
        user = update.message.from_user
        first_name = user.first_name
        last_name = user.last_name if user.last_name else ""

        logger.info(f"User '{first_name} {last_name}' ({update.message.chat.id}) in {message_type}: '{text}'")

        if message_type == "group":
            if self.bot_username in text:
                no_username_text: str = text.replace(self.bot_username, "").strip()
                response: str = self.handle_response(no_username_text)
            else:
                return
        else:
            response: str = self.handle_response(text)

        logger.info(f"Bot: {response}")
        await update.message.reply_text(response)

    @staticmethod
    async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """

        :param update: telegram chat update
        :param context: telegram message context
        Function called in case of an error, prints the error
        """
        logger.error(f"Update {update} caused error {context.error}")


    def start_bot(self):
        """

        Starts the bot
        """
        logger.info("Starting bot...")
        app = Application.builder().token(self.bot_token).build()
        self.restore_notifications(app.bot)

        # COMMANDS
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("current_price", self.current_price_command))
        app.add_handler(CommandHandler("price_chart", self.price_chart_command))
        app.add_handler(CommandHandler("price_candlestick", self.price_candlestick_command))
        app.add_handler(CommandHandler("notify", self.notify_command))
        app.add_handler(CommandHandler("my_notifications", self.my_notifications_command))
        app.add_handler(ConversationHandler(
            entry_points=[CommandHandler("delete_notifications", self.delete_notifications_command)],
            states={
                self.delete_select: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_delete_selection)],
            },
            fallbacks=[]
        ))

        # MESSAGES
        app.add_handler(MessageHandler(filters.TEXT, self.handle_message))

        # ERRORS
        app.add_error_handler(self.error)

        # Polls the bot
        logger.info("Polling...")
        app.run_polling(poll_interval=3)


import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), HealthCheckHandler)
    print(f"Health check server listening on port {port}")
    server.serve_forever()

if __name__ == "__main__":
    # Start health check server in background
    threading.Thread(target=run_health_server, daemon=True).start()

    # Start your Telegram bot (blocking call)
    telegram_bot = TelegramBot()

