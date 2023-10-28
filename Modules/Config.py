import json

class ConfigDecoder(json.JSONDecoder):
    def decode(self, obj):
        data = json.loads(obj)
        for key, value in data.copy().items():
            if type(value) is dict:
                value = Config(data=value)
                value.data["name"] = key
                argument = value.data.get("previous_execution_dune_timestamp", 0)
                value.data["previous_execution_dune_timestamp"] = argument
                data[key] = value
        return data

class ConfigEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Config):
            return obj.data
        return super().default(obj)

class Config:
    def __init__(self, config_file_path=None, data=None, parent=None):
        self.parent = parent
        self.config_file_path = config_file_path
        if not config_file_path is None:
            self.load_config()
        else:
            self.data = data

    def load_config(self):
        with open(self.config_file_path, 'r') as file:
            self.data = json.load(file, cls=ConfigDecoder)
        for key, value in self.data.items():
            if isinstance(value, Config):
                value.parent = self

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
                return self.parent.get(key, default)
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save_config()