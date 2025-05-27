"""
Database class
"""
import sqlite3
import os

class Db:
    """
    Handles database
    """
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_file_path = os.path.join(self.script_dir, "../telegram_project.db")
        self.conn = sqlite3.connect(self.db_file_path, check_same_thread=False)
        self.cursor = self.conn.cursor()

    def select_all_notifications(self):
        """

        :return: all active notifications
        """
        sql = "SELECT * FROM notifications"
        self.cursor.execute(sql)
        sql_data = self.cursor.fetchall()
        return sql_data

    def select_user_notifications(self, telegram_id):
        """

        :param telegram_id: user's id
        :return: all active notifications of the user
        """
        sql = "SELECT * FROM notifications WHERE telegram_id = ?"
        self.cursor.execute(sql, (telegram_id, ))
        sql_data = self.cursor.fetchall()
        return sql_data

    def select_notification(self, notification_id):
        """

        :param notification_id: notification_id
        :return: all active notifications of the user
        """
        sql = "SELECT * FROM notifications WHERE id = ?"
        self.cursor.execute(sql, (notification_id, ))
        sql_data = self.cursor.fetchall()
        return sql_data

    def get_notification_last_sent(self, notification_id):
        """

        :param notification_id: notification id
        :return: last_sent date of the notification
        """
        sql = "SELECT last_sent FROM notifications WHERE id = ?"
        self.cursor.execute(sql, (notification_id, ))
        self.conn.commit()
        sql_data = self.cursor.fetchall()
        return sql_data[0][0]

    def register_user(self, telegram_id):
        """

        :param telegram_id:  user's id

        Inserts (registrates) the user into the database
        """
        sql = "INSERT INTO users (telegram_id) VALUES (?);"
        self.cursor.execute(sql, (telegram_id, ))
        self.conn.commit()

    def set_notification(self, telegram_id, chat_id, interval, command, coin, currency, days):
        """

        :param telegram_id: user's id
        :param chat_id: chat id
        :param interval: message interval
        :param command: message command
        :param coin: command coin
        :param currency: command currency
        :param days: command days (in charts)

        Inserts new notification into the database
        :return: the inserted notification's id
        """
        sql = "INSERT INTO notifications (telegram_id, chat_id, interval, command, coin, currency, days) VALUES (?, ?, ?, ?, ?, ?, ?);"
        self.cursor.execute(sql, (telegram_id, chat_id, interval, command, coin, currency, days))
        self.conn.commit()

        return self.cursor.lastrowid

    def update_notification_date(self, notification_id):
        """

        :param notification_id: notification id

        Updates the last_sent date in the database
        """
        sql = "UPDATE notifications SET last_sent = CURRENT_TIMESTAMP WHERE id = ?;"
        self.cursor.execute(sql, (notification_id, ))
        self.conn.commit()

    def delete_notification(self, notification_id):
        """
        :param notification_id: notification id

        Deletes the notification from the database
        """
        sql = "DELETE FROM notifications WHERE id = ?;"
        self.cursor.execute(sql, (notification_id, ))
        self.conn.commit()

    def select_statistic(self, statistic):
        """

        :param statistic: column to select
        :return: selected column
        """
        sql = f"SELECT {statistic} FROM notifications"
        self.cursor.execute(sql)
        sql_data = self.cursor.fetchall()
        return sql_data

    def conn_close(self):
        """

        closes the database connection
        """
        self.conn.close()

