import datetime
import sqlite3
import time
from dune_client.types import QueryParameter
from dune_client.client import DuneClient
from dune_client.query import QueryBase


class DatabaseManager:

    def __init__(self, config, internet_connection=False):
        self.database_name = f"Databases/{config.get('name')}.sql"
        self.config = config
        self.__internet_connection = internet_connection
        self.create_database_file()

    def create_database_file(self):
        with sqlite3.connect(self.database_name) as connection:
            cursor = connection.cursor()
            self.__create_table(cursor=cursor)

    def get_transactions(self):
        with sqlite3.connect(self.database_name) as connection:
            cursor = connection.cursor()
            query = f"SELECT * FROM {self.config.get('name')}_transactions ORDER BY block_number ASC"
            cursor.execute(query)
            while True:
                row = cursor.fetchone()
                if row is None:
                    break
                yield row

    def get_last_fetched_block_number(self):
        with sqlite3.connect(self.database_name) as connection:
            cursor = connection.cursor()
            query = f"SELECT block_number FROM {self.config.get('name')}_transactions ORDER BY block_number DESC LIMIT 1"
            cursor.execute(query)
            last_block_number = cursor.fetchone()
        if last_block_number is None:
            return 0
        return last_block_number[0]

    def sync_database(self):
        if not self.__internet_connection:
            raise ValueError("No internet connection")

        previous_execution_dune_timestamp = self.config.get("previous_execution_dune_timestamp")
        now_timestamp = int(time.time())
        difference_timestamp = now_timestamp - previous_execution_dune_timestamp

        days_ago = difference_timestamp//(24*60*60)
        suffix_days_ago = f"{days_ago}d"
        print(f"[+] Last update database was: {suffix_days_ago if days_ago else ''} {difference_timestamp % 86400 // 3600:02}:{(difference_timestamp % 3600) // 60:02}:{difference_timestamp % 60:02} ago")

        if difference_timestamp < self.config.get("database_update_frequency_seconds"):
            return

        last_fetched_block_number = self.get_last_fetched_block_number()
        new_transactions, column_names = self.__get_new_contract_transactions(block_number=last_fetched_block_number)
        new_transactions = [[new_transaction[column_name] for column_name in column_names] for new_transaction in new_transactions]
        with sqlite3.connect(self.database_name) as connection:
            cursor = connection.cursor()
            query = f"INSERT OR IGNORE INTO {self.config.get('name')}_transactions (hash, block_number, block_timestamp, \"from\", data) VALUES (?, ?, ?, ?, ?)"
            cursor.executemany(query, new_transactions)
            connection.commit()
        self.config.set("previous_execution_dune_timestamp", now_timestamp)
        print(f"[+] Added {len(new_transactions)} transactions")
        print(f"[+] Last fetched block: {self.get_last_fetched_block_number()}")
        print("[+] Checking sync dune with blockchain")
        block_time,  last_block_number, late_in_blocks, time_difference = self.__get_sync_dune_with_blockchain()
        print(f"\tBlock Time : {block_time}\n"
              f"\tLast block : {last_block_number}\n"
              f"\tLate in blocks : {late_in_blocks}\n"
              f"\tTime difference : {time_difference}s")

    def __create_table(self, cursor):
        query = f"CREATE TABLE IF NOT EXISTS {self.config.get('name')}_transactions (hash BLOB UNIQUE, block_number INTEGER, block_timestamp INTEGER, \"from\" BLOB, data BLOB)"
        cursor.execute(query)

    def __get_new_contract_transactions(self, block_number):
        query = QueryBase(
            query_id=3095752,
            params=[
                QueryParameter.number_type(name="last_block_number", value=block_number - 1),
                QueryParameter.text_type(name="address", value=self.config.get("contract_address")),
                QueryParameter.text_type(name="chain", value=self.config.get("chain")),
            ],
        )
        results = self.__run_query_dune(query=query)
        rows = results.result.rows
        column_names = results.result.metadata.column_names
        return rows, column_names

    def __get_sync_dune_with_blockchain(self):
        query = QueryBase(
            query_id=3094920,
            params=[
                QueryParameter.text_type(name="chain", value=self.config.get("chain")),
                QueryParameter.text_type(name="timezone_offset", value=self.config.get("timezone_offset")),
            ],
        )
        result = self.__run_query_dune(query=query)
        result = result.result.rows[0]
        block_time,  last_block_number, late_in_blocks, time_difference = result["block_time"], result["last_block_number"], result["late_in_blocks"], result["time_difference"]
        return block_time, last_block_number, late_in_blocks, time_difference

    @staticmethod
    def __run_query_dune(query, performance="medium"):
        dune = DuneClient.from_env()
        results = dune.run_query(query=query, performance=performance)
        return results
