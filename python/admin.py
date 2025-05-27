"""
Admin for stats
"""
import sys
from collections import Counter

from InquirerPy import inquirer

from db import Db

class Admin:
    """
    Handles the admin console with the statistics
    """
    def __init__(self):
        self.db = Db()

        self.main_menu()

    @staticmethod
    def give_options(options, title="Select an option: "):
        """

        :param options: options in selection menu
        :param title: title of option menu
        :return: user's choice
        """
        print("\t")
        choice = inquirer.select(
            message=title,
            choices=options,
            pointer=">"
        ).execute()
        return choice

    def statistic_menu(self, statistic):
        """

        :param statistic: database column
        Shows the most used values of the specified column
        """
        for i in range(5):
            print("\n")

        if statistic not in ["command", "coin", "currency"]:
            sys.exit()

        sql_data = self.db.select_statistic(statistic)

        if sql_data:
            data = []
            for arr in sql_data:  # Convert to a normal array
                data.append(arr[0])

            data_count = Counter(data)  # Count element occurrences
            data_count = dict(data_count)  # Counter object back to dictionary
            sorted_data = dict(sorted(data_count.items(), key=lambda x: x[1], reverse=True))  # Sort by value (returns a list)

            print(f"Most used {statistic.capitalize()}:\n")
            for key, value in sorted_data.items():
                print(f"{key}: {value}")

            choice = self.give_options(["Back to main menu"])
            if choice == "Back to main menu":

                self.main_menu()
        else:
            print("Database is empty")

    def main_menu(self):
        """

        Shows the main menu
        """
        for i in range(5):
            print("\n")
        options_dict = {
            "Commands": "command",
            "Coins": "coin",
            "Currencies": "currency"
        }

        choice = self.give_options(["Commands", "Coins", "Currencies"], "Select a statistic: ")

        self.statistic_menu(options_dict[choice])




admin = Admin()
