"""
Crypto api class
"""
import io
from datetime import datetime as dt, timedelta
import json
import os

import requests
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf

from db import Db
from lib import format_big_number
from logger import logger

class CryptoAPI:
    """
    Handles all API requests
    """
    def __init__(self):
        self.cg_headers = {'x-cg-demo-api-key': 'CG-FjmueCvkUBDvNyh8AFpdXpr3'}

        self.db = Db()

        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.coins_json = os.path.join(self.script_dir, "../coins.json")
        self.currencies_json = os.path.join(self.script_dir, "../currencies.json")
        self.save_coin_and_currency_list()


    def save_coin_and_currency_list(self):
        """

        Saves the coin and currency lists into json files for validation of commands
        """
        logger.info("Saving coin and currency lists")
        try:
            response = requests.get("https://api.coingecko.com/api/v3/coins/list")
            if response.status_code == 200:
                coins = response.json()
                with open(self.coins_json, "w") as f:
                    json.dump([coin['id'] for coin in coins], f)
            else:
                raise Exception("Failed to fetch coins list")
        except Exception as e:
            logger.error(f"Error caching coins list: {e}")

        try:
            response = requests.get("https://api.coingecko.com/api/v3/simple/supported_vs_currencies")
            if response.status_code == 200:
                currencies = response.json()
                with open(self.currencies_json, "w") as f:
                    json.dump(currencies, f)
            else:
                raise Exception
        except Exception as e:
            logger.error(f"Error caching currencies list: {e}")

    def get_coin_list(self):
        """

        :return: coin list from the json file
        """
        try:
            with open(self.coins_json, "r") as f:
                return set(json.load(f))
        except Exception as e:
            logger.error(f"Failed to load coins list: {e}")
            return "Error API"

    def get_currency_list(self):
        """

        :return: currency list from the json file
        """
        try:
            with open(self.currencies_json, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load currencies list from cache: {e}")
            return "Error API"

    def f_date_price(self, args):
        """

        :param args: dictionary of arguments for the function
        :return: reply: text reply with an error or the price
        """
        coin = args["coin"]
        currency = args["currency"]
        date = args["date"]

        url = f"https://api.coingecko.com/api/v3/coins/{coin}/history"
        params = {
            "ids": coin,
            "vs_currencies": currency,
            "date": date
        }

        response = requests.get(url, params=params, headers=self.cg_headers)
        if response.status_code == 200:
            data = response.json()
            price = data["market_data"]["current_price"][currency]
            bot_reply = price
        else:
            bot_reply = "Error API"
            logger.error("Historical price raised an error (failed to retrieve from api)")

        return bot_reply

    def f_current_price_command(self, args):
        """

        :param args: dictionary of arguments for the function
        :return: reply: text reply with an error or the price and its change
        """
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": args["coin"],
            "vs_currencies": args["currency"]
        }

        response = requests.get(url, params=params, headers=self.cg_headers)
        if response.status_code == 200:
            try:
                notification_id = args["notification_id"]
                last_sent_db = self.db.get_notification_last_sent(notification_id)
                history_date = dt.strptime(last_sent_db, "%Y-%m-%d %H:%M:%S").strftime('%d-%m-%Y') # last sent date
                reply_since = "the day the last notification was sent"
            except KeyError:
                history_date = (dt.now() - timedelta(1)).strftime('%d-%m-%Y') # yesterday's date
                reply_since = "yesterday"


            args["date"] = history_date

            try:
                data = response.json()
                price_current = data[params["ids"]][params["vs_currencies"]]
            except KeyError:
                bot_reply = "Invalid token or currency (e.g. <i>current_price bitcoin usd</i>)"
                logger.error("Current price raised an error (invalid token or currency)")
                return bot_reply
            price_history = self.f_date_price(args)

            price_history_one_perc = price_history / 100
            price_difference = round((price_current / price_history_one_perc) - 100, 3)
            price_current_formated = format_big_number(price_current)

            if price_difference < 0:
                bot_reply = f"The price of {params['ids'].capitalize()} has decreased by {price_difference}% since {reply_since} and is now {price_current_formated} {params['vs_currencies'].upper()}"
            elif price_difference > 0:
                bot_reply = f"The price of {params['ids'].capitalize()} has increased by {price_difference}% since {reply_since} and is now {price_current_formated} {params['vs_currencies'].upper()}"
            else:
                bot_reply = f"The price of {params['ids'].capitalize()} hasn't changed and is now {price_current_formated} {params['vs_currencies'].upper()}"
        else:
            bot_reply = "Failed to retrieve data from the API. Please try again later"

        return bot_reply

    def f_price_chart_command(self, args):
        """

        :param args: dictionary of arguments for the function
        :return: reply: array of a text reply and an image of chart in a buffer, or just a reply if unsuccessful
        """
        coin = args["coin"]
        currency = args["currency"]
        days = args["days"]

        try:
            days = int(days)
        except ValueError:
            bot_reply = "Please enter valid information (e.g. <i>price_chart bitcoin usd 30</i>)"
            logger.error("Price chart raised an error (days value is not an integer)")
            return bot_reply

        if days <= 0:
            bot_reply = "Please enter valid information (e.g. <i>price_chart bitcoin usd 30</i>)"
            logger.error("Price chart raised an error (days value is not above 0)")
            return bot_reply

        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
        params = {
            "vs_currency": currency,
            "days": days,
            "interval": "daily" if days > 7 else "" # Coin-gecko gives data every 5min for 1 day, 1 hour for 2-90 and daily above (unless set to daily)
        }

        response = requests.get(url, params=params, headers=self.cg_headers)
        data = response.json()
        if "error" in data:
            if data["error"] == "invalid vs_currency":
                logger.error("Price chart raised an error (invalid currency)")
                bot_reply = "Please enter a valid currency (e.g. <i>price_days bitcoin usd 30</i>)"
            elif data["error"] == "coin not found":
                logger.error("Price chart raised an error (invalid coin)")
                bot_reply = "Please enter a valid coin (e.g. <i>price_days bitcoin usd 30</i>)"
            else:
                logger.error(f"Price chart raised an error {data['error']}")
                bot_reply = "Failed to retrieve data from the API. Please try again later"
        else:
            plt.figure(figsize=(10, 7))
            if days > 7:
                x = [dt.utcfromtimestamp(sub_array[0] / 1000).strftime("%m-%d") for sub_array in data["prices"]]
                y = [sub_array[1] for sub_array in data["prices"]]

                plt.plot(x, y, label="Price", marker=".")

                plt.title(f"Price of {coin} for each day")
                plt.xlabel("Date [days]")
                days_divided = int(days / 30)

                plt.xticks(x[::(1 + days_divided)])
            elif days == 1:
                x = [dt.utcfromtimestamp(sub_array[0] / 1000).strftime("%m-%d %H:%M") for sub_array in data["prices"]][::6]
                y = [sub_array[1] for sub_array in data["prices"]][::6]

                plt.plot(x, y, label="Price", marker=".")

                plt.title(f"Price of {coin} every hour in the last day")
                plt.xlabel("Date [hours]")
                plt.xticks(x[::2])
            else:
                x = [dt.utcfromtimestamp(sub_array[0] / 1000).strftime("%m-%d %H:%M") for sub_array in data["prices"]]
                y = [sub_array[1] for sub_array in data["prices"]]

                plt.plot(x, y, label="Price", marker=".")

                plt.title(f"Price of {coin} every hour in the last {days} days")
                plt.xlabel("Date [hours]")
                plt.xticks(x[::days])

            plt.xticks(rotation=45)
            plt.legend(loc="upper left")
            plt.ylabel(f"Price [{currency}]")
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format="png")
            img_buffer.seek(0)
            plt.clf() # clears

            bot_reply = {
                "reply": f"Here is a chart of {coin} in {currency} in the last {days} days",
                "img": img_buffer
            }

        return bot_reply

    def f_price_candlestick_command(self, args):
        """

        :param args: dictionary of arguments for the function
        :return: reply: array of a text reply and an image of a candlestick chart in a buffer, or just a reply if unsuccessful
        """
        coin = args["coin"]
        currency = args["currency"]
        days = args["days"]

        try:
            days = int(days)
        except ValueError:
            bot_reply = "Please enter valid information (e.g. <i>price_candlestick bitcoin usd 30</i>)"
            logger.error("Price candlestick raised an error (days value is not an integer)")
            return bot_reply

        if days <= 0:
            bot_reply = "Please enter valid information (e.g. <i>price_candlestick bitcoin usd 30</i>)"
            logger.error("Price candlestick raised an error (days value is not above 0)")
            return bot_reply

        if days not in [1, 7, 14, 30, 90, 3651, 7, 14, 30, 90, 365]:
            bot_reply = "API allows only: 1, 7, 14, 30, 90 or 365 days"
            logger.error("Price candlestick raised an error (days value is not allowed)")
            return bot_reply

        url = f"https://api.coingecko.com/api/v3/coins/{coin}/ohlc"
        params = {
            "vs_currency": currency,
            "days": days
        }

        response = requests.get(url, params=params, headers=self.cg_headers)
        data = response.json()
        if "error" in data:
            if data["error"] == "invalid vs_currency":
                logger.error(f"Price candlestick raised an error (invalid currency)")
                bot_reply = "Please enter a valid currency (e.g. <i>price_candlestick bitcoin usd 30</i>)"
            elif data["error"] == "coin not found":
                logger.error(f"Price candlestick raised an error (invalud coin)")
                bot_reply = "Please enter a valid coin (e.g. <i>price_candlestick bitcoin usd 30</i>)"
            else:
                logger.error(f"Price candlestick raised an error ({data['error']})")
                bot_reply = "Failed to retrieve data from the API. Please try again later"
        else:
            interval_map = {1: "30 minutes", 7: "4 hours", 14: "4 hours", 30: "4 hours", 90: "4 days", 365: "4 days"}
            interval = interval_map[days]

            dataframe = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close"]) # sets-up the dataframe with pandas
            dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], unit="ms") # converts timestamp to normal datetime
            dataframe.set_index("timestamp", inplace=True) # sets the timestamp to the index instead of 0,1,2,3,...; inplace replaces the original

            img_buffer = io.BytesIO()
            mpf.plot(dataframe, type="candle", style="yahoo", title=f"Price of {coin} every {interval} in the last {days} days",
                    ylabel=f"Price [{currency}]", xlabel = "Date", tight_layout=True,
                    savefig={
                        "fname": img_buffer,
                        "format": "png"
                    }
            )
            img_buffer.seek(0)

            bot_reply = {
                "reply": f"Here is a candlestick chart of {coin} in {currency} in the last {days} days",
                "img": img_buffer
            }

        return bot_reply
