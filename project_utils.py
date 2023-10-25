import os
import json
import requests


def configuration_validate():
    config_folder = "Settings"
    config_file = "config.json"

    config_path = os.path.join(config_folder, config_file)

    if not os.path.exists(config_folder):
        os.makedirs(config_folder)

    if not os.path.exists(config_path):
        config_data = {"previous_execution_dune_timestamp": 0,
                       "database_update_frequency_seconds": 4 * 60 * 60,
                       "timezone_offset": 10}
        with open(config_path, 'w') as file:
            json.dump(config_data, file, indent=4, ensure_ascii=False)


def check_internet_connection():
    try:
        response = requests.get("http://www.google.com", timeout=10)
        if response.status_code == 200:
            return True
        else:
            return False
    except requests.ConnectionError:
        return False
