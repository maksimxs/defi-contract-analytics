import string, traceback, requests, datetime, decimal
import time

from Modules.Statistics import BaseStatistics

decimal.getcontext().prec = 100
function_signatures = {
    "61e708c8": "buyTools",
    "a3fdad11": "collectCash",
    "9c74a4eb": "convertCash",
    "788b8bf8": "upgradeGarage",
    "884fa9a5": "withdrawCash"
}
START_SIGNATURE_INDEX = 2
START_DATA_INDEX = START_SIGNATURE_INDEX + 8
NULL_ADDRESS = "0x0000000000000000000000000000000000000000"
_DECIMALS = 18

REFERRAL_PERCENTS = [decimal.Decimal("4"), decimal.Decimal("3"), decimal.Decimal("2"), decimal.Decimal("1")]
GARAGE_PROFIT_PERCENTAGE = [decimal.Decimal("210"), decimal.Decimal("220"), decimal.Decimal("230"), decimal.Decimal("240"), decimal.Decimal("250"), decimal.Decimal("260")]
REFERRAL_STEP = decimal.Decimal("10")
ADMIN_FEE = decimal.Decimal("800")
MARKEING_FEE = decimal.Decimal("200")
REFERRAL_PROFIT_STEP = decimal.Decimal("100")
MAX_REFERRAL_PROFIT_STEP = decimal.Decimal("1000")
MAX_GARAGE_PROFIT = decimal.Decimal(23000)
MAX_GARAGE_COUNT = 6
MAX_PROFIT_LIMIT = decimal.Decimal("86400")
PERCENTS_DIVIDER = decimal.Decimal("10000")
TIME_STEP = decimal.Decimal("86400")

MANAGER = "0x12Fbef4CF5134666D74877697D18Ea08C747D272"
ADMINWALLET = "0xEF7d920B05D3f0b3a0151440a5b1D7a84F2E6f42"
MARKETINGWALLET = "0x12D19080f19aBd7Eeaf6A9371AEe2d1EE47170Be"


class Garage(dict):
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
            "tools": decimal.Decimal("0"),
            "cash": decimal.Decimal("0"),
            "cash2": decimal.Decimal("0"),
            "timestamp": 0,
            "ref": NULL_ADDRESS,
            "DirectReferral": 0,
            "totalBuy": decimal.Decimal("0"),
            "referralProfit": [decimal.Decimal("0"), decimal.Decimal("0"), decimal.Decimal("0"), decimal.Decimal("0")],
            "cars": [0, 0, 0, 0, 0, 0],
            "garageBuyAmount": [0, 0, 0, 0, 0, 0],
            "profitEarned": [0, 0, 0, 0, 0, 0]
        }
        return default_values

class SmartGarage(BaseStatistics):
    def __init__(self):
        self.contract_balance = decimal.Decimal("0")
        self.garages = Garage()
        self.lost_profit = decimal.Decimal("0")
        self.total_earned = decimal.Decimal("0")

    def fetch_transaction(self, transaction):
        transaction = {"hash": transaction[0],
                       "block_number": transaction[1],
                       "block_timestamp": transaction[2],
                       "from": transaction[3],
                       "data": transaction[4]
                       }

        function_signature = transaction["data"][START_SIGNATURE_INDEX:START_DATA_INDEX]
        transaction["data"] = transaction["data"][START_DATA_INDEX:]
        self.transaction = transaction

        function_name = self.get_function_name(function_signature)

        match function_name:
            case "buyTools":
                self.__fetch_buyTools(transaction=transaction)

            case "withdrawCash":
                self.__fetch_withdrawCash(transaction=transaction)

            case "collectCash":
                self.__fetch_collectCash(transaction=transaction)

            case "convertCash":
                self.__fetch_convertCash(transaction=transaction)

            case "upgradeGarage":
                self.__fetch_upgradeGarage(transaction=transaction)

            case _:
                print(f"{function_name} | {transaction['hash']}")

        del self.transaction

    def __fetch_buyTools(self, transaction):
        ref = "0x" + transaction["data"][24:64*1]
        amount = int(transaction["data"][64*1:64*2], 16)
        amount = decimal.Decimal(amount)

        tools = amount
        adminFee = (amount * ADMIN_FEE) // PERCENTS_DIVIDER
        marketingFee = (amount * MARKEING_FEE) // PERCENTS_DIVIDER

        self.contract_balance += amount - (adminFee + marketingFee)

        user = transaction["from"]

        if (self.garages[user]["timestamp"] == 0):
            ref = MANAGER if self.garages[ref]["timestamp"] == 0 else ref
            self.garages[ref]["DirectReferral"] += 1
            self.garages[user]["ref"] = ref
            self.garages[user]["timestamp"] = transaction["block_timestamp"]

        ref = self.garages[user]["ref"]
        if ref != NULL_ADDRESS:
            upline = ref
            for i in range(len(REFERRAL_PERCENTS)):
                if upline != NULL_ADDRESS:
                    commission = (tools * REFERRAL_PERCENTS[i]) // 100
                    self.garages[upline]["tools"] += commission // 2
                    self.garages[upline]["cash"] += (commission // 2) * 100
                    self.garages[upline]["referralProfit"][i] += commission
                    upline = self.garages[upline]["ref"]
                else:
                    break

        self.garages[user]["tools"] += tools
        self.garages[user]["totalBuy"] += tools

    def __fetch_withdrawCash(self, transaction):
        user = transaction["from"]
        cash = self.garages[user]["cash"]
        self.garages[user]["cash"] = 0
        amount = cash // 100
        amount = self.contract_balance if self.contract_balance < amount else amount
        self.contract_balance -= amount

    def __fetch_convertCash(self, transaction):
        _cashAmount = int(transaction["data"][START_DATA_INDEX:], 16)

        user = transaction["from"]
        self.garages[user]["cash"] -= _cashAmount
        amount = _cashAmount // 100
        self.garages[user]["tools"] += amount

    def __fetch_collectCash(self, transaction):
        user = transaction["from"]
        self.__syncGarage(user)
        self.garages[user]["cash"] += self.garages[user]["cash2"]
        self.total_earned += self.garages[user]["cash2"]
        self.garages[user]["cash2"] = 0

    def __fetch_upgradeGarage(self, transaction):
        garageId = int(transaction["data"][START_DATA_INDEX:], 16)

        user = transaction["from"]
        self.__syncGarage(user)
        self.garages[user]["cars"][garageId] += 1
        carLevel = self.garages[user]["cars"][garageId]
        self.garages[user]["garageBuyAmount"][garageId] += self.__getUpgradePrice(
            garageId,
            carLevel
        )
        self.garages[user]["tools"] -= self.__getUpgradePrice(garageId, carLevel)

    def __syncGarage(self, user):
        lost_duration = 0

        duration = self.transaction["block_timestamp"] - self.garages[user]["timestamp"]

        if duration > MAX_PROFIT_LIMIT:
            lost_duration = duration - MAX_PROFIT_LIMIT
            duration = MAX_PROFIT_LIMIT


        totalProfit = 0
        for i in range(MAX_GARAGE_COUNT):
            if self.garages[user]["garageBuyAmount"][i] > 0:
                profitPercentage = GARAGE_PROFIT_PERCENTAGE[i] + ((GARAGE_PROFIT_PERCENTAGE[i] * self.__getLeadershipBonus(user)) //
                                                                  PERCENTS_DIVIDER)
                profitAmount = (self.garages[user]["garageBuyAmount"][i] *
                                profitPercentage) // PERCENTS_DIVIDER
                profitAmount = (profitAmount * duration) // TIME_STEP

                maxGarageProfit = self.garages[user]["garageBuyAmount"][i] * MAX_GARAGE_PROFIT / PERCENTS_DIVIDER
                if (self.garages[user]["profitEarned"][i] + profitAmount >= maxGarageProfit):
                    profitAmount = maxGarageProfit - self.garages[user]["profitEarned"][i]
                    self.garages[user]["cars"][i] = 0
                    self.garages[user]["profitEarned"][i] = 0
                    self.garages[user]["garageBuyAmount"][i] = 0
                    lost_duration = 0
                else:
                    self.garages[user]["profitEarned"][i] += profitAmount
                totalProfit += profitAmount

                # if not lost_duration is None:
                self.lost_profit += ((profitAmount * lost_duration) // TIME_STEP) * 100

        self.garages[user]["cash2"] += totalProfit * 100
        self.garages[user]["timestamp"] = self.transaction["block_timestamp"]

    def __getLeadershipBonus(self, user):
        referralStep = self.garages[user]["DirectReferral"] // REFERRAL_STEP
        referralProfit = referralStep * REFERRAL_PROFIT_STEP
        if (referralProfit > MAX_REFERRAL_PROFIT_STEP):
            referralProfit = MAX_REFERRAL_PROFIT_STEP
        return referralProfit


    def __getUpgradePrice(self, garageId, carLevel):
        if (carLevel == 1):
            upgradePrice = [
                5,
                50,
                100,
                500,
                1000,
                5000
            ][garageId]

        if (carLevel == 2):
            upgradePrice = [
                10,
                60,
                150,
                600,
                1500,
                6000
            ][garageId]


        if (carLevel == 3):
            upgradePrice = [
                15,
                70,
                200,
                700,
                2000,
                7000
            ][garageId];
        if (carLevel == 4):
            upgradePrice = [
                20,
                80,
                250,
                800,
                2500,
                8000
            ][garageId]
        return decimal.Decimal(upgradePrice) * decimal.Decimal(10 ** 18)

    @staticmethod
    def get_function_name(signature):
        signature = signature.lower()
        function_name = function_signatures.get(signature, "UnknownFunction")
        return function_name

    def print_analytics(self):
        result_message = ""
        real_contract_balance = self.get_contract_balance()
        result_message += f"\nDune: {self.contract_balance / 10**_DECIMALS} | Chain: {real_contract_balance / 10**_DECIMALS} USDT | Difference: {abs(real_contract_balance - self.contract_balance) / 10**_DECIMALS} USDT"

        not_invested = sum([i['cash'] for i in self.garages.values()])
        result_message += f"\n\nNot invested money: {not_invested / 10**_DECIMALS / 100} USDT"
        result_message += f"\nTotal Earned: {self.total_earned / 10**_DECIMALS / 100} USDT"

        nature_daily = 0
        MAX_daily = 0
        wait_claim = 0
        now_timestamp = int(time.time())
        for user, garage in self.garages.items():
            for i in range(MAX_GARAGE_COUNT):
                if garage["garageBuyAmount"][i] > 0:
                    nature_percent = GARAGE_PROFIT_PERCENTAGE[i] + ((GARAGE_PROFIT_PERCENTAGE[i] * self.__getLeadershipBonus(user)) // PERCENTS_DIVIDER)
                    max_percent = GARAGE_PROFIT_PERCENTAGE[i] + ((GARAGE_PROFIT_PERCENTAGE[i] * 1000) // PERCENTS_DIVIDER)
                    nature_daily += (garage["garageBuyAmount"][i] * nature_percent) // PERCENTS_DIVIDER
                    MAX_daily += (garage["garageBuyAmount"][i] * max_percent) // PERCENTS_DIVIDER

                    lost_duration = 0
                    duration = now_timestamp - garage["timestamp"]
                    if duration > MAX_PROFIT_LIMIT:
                        lost_duration = duration - MAX_PROFIT_LIMIT
                        duration = MAX_PROFIT_LIMIT

                    profitPercentage = GARAGE_PROFIT_PERCENTAGE[i] + (
                                (GARAGE_PROFIT_PERCENTAGE[i] * self.__getLeadershipBonus(user)) //
                                PERCENTS_DIVIDER)
                    profitAmount = (self.garages[user]["garageBuyAmount"][i] *
                                    profitPercentage) // PERCENTS_DIVIDER
                    profitAmount = (profitAmount * duration) // TIME_STEP

                    maxGarageProfit = self.garages[user]["garageBuyAmount"][i] * MAX_GARAGE_PROFIT / PERCENTS_DIVIDER
                    if (self.garages[user]["profitEarned"][i] + profitAmount >= maxGarageProfit):
                        profitAmount = maxGarageProfit - self.garages[user]["profitEarned"][i]
                        self.garages[user]["cars"][i] = 0
                        self.garages[user]["profitEarned"][i] = 0
                        self.garages[user]["garageBuyAmount"][i] = 0
                        lost_duration = 0
                    else:
                        self.garages[user]["profitEarned"][i] += profitAmount
                    wait_claim += profitAmount

                    # if not lost_duration is None:
                    self.lost_profit += ((profitAmount * lost_duration) // TIME_STEP) * 100

        result_message += f"\nTotal lost profit: {self.lost_profit / 10 ** _DECIMALS / 100} USDT + Wait claim: {wait_claim // 10**18} USDT"
        result_message += f"\n\nNature Daily: {nature_daily / 10**18} USDT"
        result_message += f"\nMAX Daily: {MAX_daily / 10**18} USDT"
        day_alive = (real_contract_balance - (not_invested // 10**2) - wait_claim) / nature_daily
        result_message += f"\n\nPredict: {day_alive.quantize(decimal.Decimal('0.00000001'))} Days / Payback: {day_alive.quantize(decimal.Decimal('0.00000001')) * 240 / 100} %"
        result_message += "\n\n\n"
        print(result_message)
        result_message = "# " + datetime.datetime.now().strftime("%Y %m.%d %H:%M:%S") + result_message
        self.save_analytics(message=result_message)

    def save_analytics(self, message):
        with open("Reports/SmartGarage.txt", "a") as file:
            file.write(message)

    def get_contract_balance(self, block_number="latest"):
        url = "https://rpc.ankr.com/bsc"
        data = {
            "method": "eth_call",
            "params": [
                {"to": "0x55d398326f99059fF775485246999027B3197955",
                 "data": "0x70a08231" + "66F3F995929D0d50450bF39832bc31307edB59A3".zfill(64)},
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