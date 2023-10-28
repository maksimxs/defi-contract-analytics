import json
import os
from dotenv import load_dotenv
from Modules import DatabaseManager, Config
from Modules.Statistics import VipGarage, HogwardsOnline, LamonReboot
from project_utils import configuration_validate, check_internet_connection

config_folder = "Settings"
config_file = "config.json"
config_path = os.path.join(config_folder, config_file)


def main():
    configuration_validate()
    config = Config(config_file_path=config_path)
    is_internet_connection = check_internet_connection()

    project_name = "VipGarage"
    config = config.get(project_name)

    database_manager = DatabaseManager(config=config, internet_connection=is_internet_connection)

    if is_internet_connection:
        load_dotenv()
        database_manager.sync_database()
    else:
        print("[-] No internet connection -> passing sync database")

    if project_name == "VipGarage":
        _statistics = VipGarage()
    elif project_name == "HogwardsOnline":
        _statistics = HogwardsOnline()
    elif project_name == "LamonReboot":
        _statistics = LamonReboot()
    else:
        1/0

    for transaction in database_manager.get_transactions():
        _statistics.fetch_transaction(transaction)
    _statistics.print_analytics()




if __name__ == '__main__':
    main()