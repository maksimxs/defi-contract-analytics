import string, traceback, requests, datetime, decimal
import time

from Modules.Statistics import BaseStatistics

decimal.getcontext().prec = 100
function_signatures = {
    "306d8620": "addMana",
    "69a191cb": "collectMoney",
    "aa5f7e26": "compound",
    "d68cf49d": "upgradeTower",
    "ffe873cb": "upgradeTreasury",
    "54876921": "withdrawMoney"
}
START_SIGNATURE_INDEX = 2
START_DATA_INDEX = START_SIGNATURE_INDEX + 8
NULL_ADDRESS = "0x0000000000000000000000000000000000000000"
_DECIMALS = 18

REFERRAL_MANA = 5

class Tower(dict):
    def __getitem__(self, key):
        if (not key.startswith("0x")) or len(key) != 42 or any([letter not in string.hexdigits for letter in key[2:]]):
            raise ValueError(f"Key is not address: {key}")
        if key not in self:
            self[key] = self._get_default_value()

        return self.get(key)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)

    def _get_default_value(self):
        default_values = {
            "mana": decimal.Decimal("0"),
            "emeralds": decimal.Decimal("0"),
            "emeralds2": decimal.Decimal("0"),
            "yield": decimal.Decimal("0"),
            "timestamp": 0,
            "hrs": 0,
            "ref": NULL_ADDRESS,
            "refs": 0,
            "refDeps": decimal.Decimal("0"),
            "affiliateDeps": decimal.Decimal("0"),
            "treasury": 0,
            "isAffiliate": False,
            "mages": [0, 0, 0, 0, 0]
        }
        return default_values

class StreetVendor(BaseStatistics):
    def __init__(self):
        self.contract_balance = decimal.Decimal("0")
        self.towers = Tower()
        self.lost_profit = decimal.Decimal("0")
        self.total_earned = decimal.Decimal("0")

    def fetch_transaction(self, transaction):
        transaction = {"hash": transaction[0],
                       "block_number": transaction[1],
                       "block_timestamp": transaction[2],
                       "from": transaction[3],
                       "data": transaction[4],
                       "value": transaction[5]
                       }

        function_signature = transaction["data"][START_SIGNATURE_INDEX:START_DATA_INDEX]
        transaction["data"] = transaction["data"][START_DATA_INDEX:]
        self.transaction = transaction

        function_name = self.get_function_name(function_signature)

        match function_name:
            case "addMana":
                self.__fetch_addMana(transaction=transaction)

            case "collectMoney":
                self.__fetch_collectMoney(transaction=transaction)

            case "compound":
                self.__fetch_compound(transaction=transaction)

            case "upgradeTower":
                self.__fetch_upgradeTower(transaction=transaction)

            case "upgradeTreasury":
                self.__fetch_upgradeTreasury(transaction=transaction)

            case "withdrawMoney":
                self.__fetch_withdrawMoney(transaction=transaction)

            case _:
                print(f"{function_name} | {transaction['hash']}")

        # if self.contract_balance != self.get_contract_balance(transaction["block_number"]):
        #     print(f"ERR {transaction['hash']} | {function_name}")
        #     pass
        # else:
        #     print(f"{transaction['hash']} | {function_name}")

        del self.transaction

    def __fetch_addMana(self, transaction):
        ref = "0x" + transaction["data"][24:64*1]

        mana = decimal.Decimal(transaction["value"]) // decimal.Decimal(1e14)
        user = transaction["from"]

        if (self.towers[user]["timestamp"] == 0):
            if (ref != NULL_ADDRESS and self.towers[ref]["timestamp"] != 0):
                self.towers[user]["ref"] = ref
                self.towers[ref]["refs"] += 1
            self.towers[user]["timestamp"] = transaction["block_timestamp"]
            self.towers[user]["treasury"] = 0

        if self.towers[user]["ref"] != NULL_ADDRESS:
            refAddress = self.towers[user]["ref"]
            self.towers[refAddress]["mana"] += (mana * REFERRAL_MANA) // decimal.Decimal(100)
            self.towers[refAddress]["refDeps"] += mana

        self.towers[user]["mana"] += mana

        admin_fee = transaction["value"] * 5 // decimal.Decimal(100)
        self.contract_balance += transaction["value"] - admin_fee

    def __fetch_collectMoney(self, transaction):
        user = transaction["from"]
        self._syncTower(user)
        self.towers[user]["hrs"] = 0
        self.towers[user]["emeralds"] += self.towers[user]["emeralds2"]
        self.towers[user]["emeralds2"] = 0

    def __fetch_compound(self, transaction):
        emeralds = decimal.Decimal(int(transaction["data"][:64*1], 16))

        user = transaction["from"]
        self.towers[user]["emeralds"] -= emeralds
        amount = (emeralds * 12) // decimal.Decimal(1000)
        self.towers[user]["mana"] += amount

    def __fetch_withdrawMoney(self, transaction):
        emeralds = decimal.Decimal(int(transaction["data"][:64*1], 16))

        user = transaction["from"]
        self.towers[user]["emeralds"] -= emeralds
        amount = emeralds * int(1e12)
        amount = self.contract_balance if self.contract_balance < amount else amount

        self.contract_balance -= amount

    def __fetch_collectMoney(self, transaction):
        user = transaction["from"]

        self._syncTower(user)
        self.towers[user]["hrs"] = 0
        self.towers[user]["emeralds"] += self.towers[user]["emeralds2"]
        self.towers[user]["emeralds2"] = 0

    def __fetch_upgradeTower(self, transaction):
        towerId = int(transaction["data"][:64*1], 16)

        user = transaction["from"]

        self._syncTower(user)
        self.towers[user]["mages"][towerId] += 1
        mages = self.towers[user]["mages"][towerId]
        self.towers[user]["mana"] -= self.getUpgradePrice(towerId, mages)
        self.towers[user]["yield"] += self.getYield(towerId, mages)

    def __fetch_upgradeTreasury(self, transaction):
        user = transaction["from"]

        treasuryId = self.towers[user]["treasury"] + 1
        self._syncTower(user)
        price, _ = self.getTreasure(treasuryId)
        self.towers[user]["mana"] -= price
        self.towers[user]["treasury"] = treasuryId

    @staticmethod
    def getUpgradePrice(towerId, mageId):
        if (mageId == 1):
            return [690, 1900, 5900, 12900, 34900][towerId]
        if (mageId == 2):
            return [790, 2390, 6900, 13900, 39900][towerId]
        if (mageId == 3):
            return [990, 2900, 8600, 16900, 47500][towerId]
        if (mageId == 4):
            return [1200, 3600, 10900, 21900, 59900][towerId]
        if (mageId == 5):
            return [1490, 3990, 11990, 23900, 67500][towerId]

    def _syncTower(self, user):
        if (self.towers[user]["yield"] > 0):
            _, treasury = self.getTreasure(self.towers[user]["treasury"])
            hrs = self.transaction["block_timestamp"] // 3600 - self.towers[user]["timestamp"] // 3600
            if (hrs + self.towers[user]["hrs"]) > treasury:
                self.lost_profit += self.towers[user]["yield"] * hrs

                hrs = treasury - self.towers[user]["hrs"]
                hrs = 0 if hrs < 0 else hrs
            self.towers[user]["emeralds2"] += hrs * self.towers[user]["yield"]
            self.total_earned += hrs * self.towers[user]["yield"]
            self.towers[user]["hrs"] += hrs
        self.towers[user]["timestamp"] = self.transaction["block_timestamp"]

    @staticmethod
    def getYield(towerId, mageId):
        if (mageId == 1):
            return [66, 198, 669, 1585, 4649][towerId]
        if (mageId == 2):
            return [77, 252, 792, 1729, 5394][towerId]
        if (mageId == 3):
            return [97, 310, 1000, 2127, 6508][towerId]
        if (mageId == 4):
            return [119, 390, 1284, 2790, 8321][towerId]
        if (mageId == 5):
            return [150, 438, 1430, 3089, 9501][towerId]


    @staticmethod
    def getTreasure(treasureId):
        if (treasureId == 0):
            return (0, 24)
        if (treasureId == 1):
            return (1000, 30)
        if (treasureId == 2):
            return (1500, 36)
        if (treasureId == 3):
            return (2000, 42)
        if (treasureId == 4):
            return (2500, 48)


    @staticmethod
    def get_function_name(signature):
        signature = signature.lower()
        function_name = function_signatures.get(signature, "UnknownFunction")
        return function_name

    def print_analytics(self):
        result_message = ""
        real_contract_balance = self.get_contract_balance()
        result_message += f"\nDune: {self.contract_balance / 10**_DECIMALS} BNB | Chain: {real_contract_balance / 10**_DECIMALS} BNB | Difference: {abs(real_contract_balance - self.contract_balance) / 10**_DECIMALS} BNB"

        not_invested = sum([i['emeralds'] + i['emeralds2'] for i in self.towers.values()])
        result_message += f"\n\nNot invested money: {not_invested / int(1e6)} BNB"
        result_message += f"\nTotal Earned: {self.total_earned / int(1e6)} BNB"

        nature_daily = decimal.Decimal("0")
        wait_claim = decimal.Decimal("0")
        now_timestamp = int(time.time())
        for user, tower in self.towers.items():
            nature_daily += decimal.Decimal(tower["yield"]) * 24

            _, treasury = self.getTreasure(self.towers[user]["treasury"])
            hrs = now_timestamp // 3600 - self.towers[user]["timestamp"] // 3600
            if (hrs + self.towers[user]["hrs"]) > treasury:
                self.lost_profit += self.towers[user]["yield"] * hrs

                hrs = treasury - self.towers[user]["hrs"]
                hrs = 0 if hrs < 0 else hrs
            wait_claim += self.towers[user]["yield"] * hrs

        result_message += f"\nTotal lost profit: {self.lost_profit / int(1e6)} BNB"
        result_message += f"\n\nNature Daily: {nature_daily / int(1e6)} BNB"

        day_alive = (real_contract_balance - ((not_invested + wait_claim) * int(1e12))) / (nature_daily * int(1e12))
        result_message += f"\n\nPredict: {day_alive.quantize(decimal.Decimal('0.00000001'))} Days / Payback: {day_alive.quantize(decimal.Decimal('0.00000001')) * (319+324)/2 / 100} %"

        result_message += "\n\n\n"
        print(result_message)
        result_message = "# " + datetime.datetime.now().strftime("%Y %m.%d %H:%M:%S") + result_message
        self.save_analytics(message=result_message)

    def save_analytics(self, message):
        with open("Reports/StreetVendor.txt", "a") as file:
            file.write(message)

    def get_contract_balance(self, block_number="latest"):
        url = "https://rpc.ankr.com/bsc"
        data = {
            "method": "eth_getBalance",
            "params": ["0xc27B094EcA1687c1025a6292169303Cb8803abd3",
                block_number],
            "id": 1,
            "json-rpc": "2.0"
        }
        try:
            response = requests.post(url, json=data)
            return decimal.Decimal(int(response.json()["result"][2:], 16))
        except:
            traceback.print_exc()
            return self.get_contract_balance()