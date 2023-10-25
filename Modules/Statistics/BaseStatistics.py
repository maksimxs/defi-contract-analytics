from abc import ABC, abstractmethod
class BaseStatistics:
    def __init__(self):
        pass

    @abstractmethod
    def fetch_transaction(self, transaction):
        pass

    @abstractmethod
    def print_analytics(self):
        pass