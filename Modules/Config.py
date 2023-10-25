import json


class ConfigEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Config):
            return obj.data
        return super().default(obj)

class Config:
    def __init__(self, config_file_path=None, data=None, parent=None):
        self.parent = parent
        if not config_file_path is None:
            self.config_file_path = config_file_path
            self.data = self.load_config()
        else:
            self.data = data

    def load_config(self):
        with open(self.config_file_path, 'r') as file:
            data = json.load(file)
        for key, value in data.copy().items():
            if type(value) is dict:
                data[key] = Config(data=value, parent=self)
                data[key].data["name"] = key
                data[key].data["previous_execution_dune_timestamp"] = data[key].data.get("previous_execution_dune_timestamp", 0)
        return data

    def save_config(self):
        if self.parent is None:
            with open(self.config_file_path, 'w') as file:
                json.dump(self, file, cls=ConfigEncoder, indent=4, ensure_ascii=False)
        else:
            self.parent.save_config()


    def get(self, key, default=None):
        if key in ("database_update_frequency_seconds", "timezone_offset"):
            if self.parent is None:
                return self.data.get(key, default)
            else:
                return self.parent.get(key, default=default)
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save_config()