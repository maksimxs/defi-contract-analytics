import string, traceback, requests, datetime, decimal, json, time
from Modules.Statistics import BaseStatistics

decimal.getcontext().prec = 100
function_signatures = {
    "9c2d5dc0": "PlantLamon",
    "5b080411": "ReinvestLamon",
    "5b6b431d": "Withdraw",
    "a277e150": "createFair",
    "d7f0ff52": "setDefaultRef",
    "715018a6": "renounceOwnership",
    "f2fde38b": "transferOwnership",
    "53fefd7d": "changeMaxDeposit"
}

START_SIGNATURE_INDEX = 2
START_DATA_INDEX = START_SIGNATURE_INDEX + 8
NULL_ADDRESS = "0x0000000000000000000000000000000000000000"
_DECIMALS = 18

INIT_MAX_INCOME_MULTIPLIER = decimal.Decimal("3")
INIT_SECOND_PERCENT = decimal.Decimal("288680")
AFFILIATE_PERCENT_USDT = decimal.Decimal("100")
class TradeFair(dict):
    def __getitem__(self, key):
        if not isinstance(key, (int)):
            raise KeyError("Key must be int")

        if key not in self:
            self[key] = self._get_default_value()

        return self.get(key)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)

    def _get_default_value(self):
        default_values = {
            "player1": NULL_ADDRESS,
            "player2": NULL_ADDRESS,
            "lamons": decimal.Decimal("0"),
            "timestamp": decimal.Decimal("0"),
            "winner": NULL_ADDRESS,
            "roll": decimal.Decimal("0")
        }
        return default_values

class TradeFairs(dict):
    def __getitem__(self, key):
        if (not key.startswith("0x")) or len(key) != 42 or any([letter not in string.hexdigits for letter in key[2:]]):
            raise ValueError(f"Key is not address: {key}")

        if key not in self:
            self[key] = self._get_default_value()

        return self.get(key)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)

    def _get_default_value(self):
        return TradeFair()

class WaitingFairs(dict):
    def __getitem__(self, key):
        if not isinstance(key, (int)):
            raise KeyError("Key must be int")

        if key not in self:
            self[key] = self._get_default_value()

        return self.get(key)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)

    def _get_default_value(self):
        return NULL_ADDRESS

class User(dict):
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
            "deposit": decimal.Decimal("0"),
            "reinvested": decimal.Decimal("0"),
            "earned": decimal.Decimal("0"),
            "withdrawn": decimal.Decimal("0"),
            "lamons": decimal.Decimal("0"),
            "timestamp": decimal.Decimal("0"),
            "partner": NULL_ADDRESS,
            "refsTotal": decimal.Decimal("0"),
            "refs1level": decimal.Decimal("0"),
            "refearnUSDT": decimal.Decimal("0"),
            "percentage": decimal.Decimal("0"),
            "maxEarnings": decimal.Decimal("0"),
            "totalEarnings": decimal.Decimal("0")
        }
        return default_values

class LamonReboot(BaseStatistics):
    def __init__(self):
        with open("Resources/LamonReboot/battle_rolls.txt", "r") as file:
            self.__battle_rolls = json.load(file)

        self.contract_balance = decimal.Decimal("0")
        self.lost_profit = decimal.Decimal("0")

        self.user = User()
        self.tradefair = TradeFairs()
        self.waitingFairs = WaitingFairs()

        self.defaultRef = "0x328b887aad7f5523ae643682f4ed42b35246dea4"
        self.owner = "0x44488c5ad94688450bf242d855f588ae53077b1b"

    def fetch_transaction(self, transaction):
        transaction = {
            "hash": transaction[0],
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
            case "PlantLamon":
                self._fetch_PlantLamon(transaction=transaction)
            case "ReinvestLamon":
                self._fetch_ReinvestLamon(transaction=transaction)
            case "Withdraw":
                self._fetch_Withdraw(transaction=transaction)
            case "createFair":
                self._fetch_createFair(transaction=transaction)
            case "setDefaultRef":
                self._fetch_setDefaultRef(transaction=transaction)
            case "renounceOwnership":
                self._fetch_renounceOwnership(transaction=transaction)
            case "transferOwnership":
                self._fetch_transferOwnership(transaction=transaction)
            case "changeMaxDeposit":
                pass

            case _:
                print(f"{function_name} | {transaction['hash']}")

        del self.transaction

    def _fetch_renounceOwnership(self, transaction):
        self.owner = NULL_ADDRESS

    def _fetch_transferOwnership(self, transaction):
        newOwner = "0x" + transaction["data"][64*0+24:64*1]
        self.owner = newOwner

    def _fetch_PlantLamon(self, transaction):
        amount = decimal.Decimal(int(transaction["data"][:64*1], 16))
        partner = "0x" + transaction["data"][64*1+24:64*2]
        user = self.user

        self.contract_balance += amount
        _msgSender = transaction["from"]

        self.__updateprePayment(_msgSender)

        user[_msgSender]["deposit"] += amount
        user[_msgSender]["maxEarnings"] = amount * INIT_MAX_INCOME_MULTIPLIER
        user[_msgSender]["totalEarnings"] = 0

        if user[_msgSender]["percentage"] == 0:
            ref = self.defaultRef if user[partner]["deposit"] == 0 else partner
            user[ref]["refs1level"] += 1
            user[ref]["refsTotal"] += 1
            user[user[ref]["partner"]]["refsTotal"] += 1
            user[_msgSender]["partner"] = ref
            user[_msgSender]["percentage"] = INIT_SECOND_PERCENT

        self.__traverseTree(user[_msgSender]["partner"], amount)

    def _fetch_ReinvestLamon(self, transaction):
        amount = decimal.Decimal(int(transaction["data"][:64*1], 16))
        _msgSender = transaction["from"]
        user = self.user

        fee = (amount * 30) // 1000
        self.__updateprePayment(_msgSender)
        user[_msgSender]["lamons"] -= amount
        user[_msgSender]["maxEarnings"] += amount * INIT_MAX_INCOME_MULTIPLIER
        user[_msgSender]["totalEarnings"] = 0
        user[_msgSender]["deposit"] += amount
        user[_msgSender]["reinvested"] += amount

        user[self.owner]["lamons"] += fee

    def _fetch_Withdraw(self, transaction):
        amount = decimal.Decimal(int(transaction["data"][:64*1], 16))
        _msgSender = transaction["from"]
        user = self.user

        self.contract_balance -= amount

        self.__updateprePayment(_msgSender)
        fee = (amount * 50) // 1000
        amount -= fee

        user[_msgSender]["lamons"] -= amount
        user[_msgSender]["withdrawn"] += amount
        user[_msgSender]["totalEarnings"] += amount
        user[_msgSender]["percentage"] = INIT_SECOND_PERCENT

    def _fetch_setDefaultRef(self, transaction):
        _newDefaultRef = "0x" + transaction["data"][24:64*1]
        self.defaultRef = _newDefaultRef

    def _fetch_createFair(self, transaction):
        waitingFairs = self.waitingFairs
        _msgSender = transaction["from"]
        fairType = int(transaction["data"][:64*1], 16)

        self.__updateprePayment(_msgSender)
        fairCreator = waitingFairs[fairType]

        if fairCreator == NULL_ADDRESS:
            self.__createFair(fairType)
        else:
            self.__joinFair(fairType, fairCreator)
            self.__fightFair(fairType, fairCreator)

    def __createFair(self, fairType):
        user = self.user
        tradefair = self.tradefair
        waitingFairs = self.waitingFairs

        block_timestamp = self.transaction["block_timestamp"]
        _msgSender = self.transaction["from"]


        tradefair[_msgSender][fairType]["timestamp"] = block_timestamp
        tradefair[_msgSender][fairType]["player1"] = _msgSender
        tradefair[_msgSender][fairType]["player2"] = NULL_ADDRESS
        tradefair[_msgSender][fairType]["winner"] = NULL_ADDRESS
        tradefair[_msgSender][fairType]["lamons"] = self.getFairType(fairType)
        tradefair[_msgSender][fairType]["roll"] = 0
        user[_msgSender]["lamons"] -= tradefair[_msgSender()][fairType]["lamons"]
        waitingFairs[fairType] = _msgSender

    def __joinFair(self, fairType, fairCreator):
        tradefair = self.tradefair
        user = self.user
        waitingFairs = self.waitingFairs

        block_timestamp = self.transaction["block_timestamp"]
        _msgSender = self.transaction["from"]


        tradefair[fairCreator][fairType]["timestamp"] = block_timestamp
        tradefair[fairCreator][fairType]["player2"] = _msgSender
        user[_msgSender]["lamons"] -= tradefair[fairCreator][fairType]["lamons"]
        waitingFairs[fairType] = NULL_ADDRESS

    def _fightFair(self, fairType, fairCreator):
        user = self.user
        tradefair = self.tradefair

        random = self.__get_battle_roll(fairCreator, fairType, self.transaction["block_number"]) # IDK HOW RECEIVE block.prevrandao
        wAmount = tradefair[fairCreator][fairType]["lamons"] * 2
        fee = (wAmount * 50) // 1000

        winner = tradefair[fairCreator][fairType]["player1"] if random < 50 else tradefair[fairCreator][fairType]["player2"]
        # loser = tradefair[fairCreator][fairType].player1 if random >= 50 else tradefair[fairCreator][fairType]["player2"]

        user[winner]["lamons"] += wAmount
        tradefair[fairCreator][fairType]["winner"] = winner
        tradefair[fairCreator][fairType]["roll"] = random

        user[self.owner]["lamons"] += fee

    def __get_battle_roll(self, fairCreator, fairType, block_number):
        block_number = block_number + 1
        key = f"{fairCreator}_{fairType}_{block_number}"
        roll = self.__battle_rolls.get(key, None)
        if not (roll is None):
            return roll
        url = "https://rpc.ankr.com/bsc"
        data = {
            "method": "eth_call",
            "params": [
                {"to": "0xfEA20421C1C73a451b7c0D5A4414aC14e63e0414",
                 "data": "0xb54f57ee" + fairCreator[2:].zfill(64) + hex(fairType)[2:].zfill(64)},
                block_number],
            "id": 1,
            "json-rpc": "2.0"
        }
        try:
            response = requests.post(url, json=data)
            result = response.json()["result"]
            roll = [int(result[i:i + 64], 16) for i in range(2, len(result), 64)][5]
            self.__battle_rolls[key] = roll
            with open("Resources/LamonReboot/battle_rolls.txt", "w") as file:
                json.dump(self.__battle_rolls, file, indent=4, ensure_ascii=False)
            return roll
        except:
            traceback.print_exc()
            return self.__get_battle_roll(fairCreator, fairType, block_number)

    def getFairType(self, fairType):
        return [5, 25, 50][fairType] * decimal.Decimal(10 ** 18)

    def __traverseTree(self, account, value):
        user = self.user

        if value != 0:
            feeUSDT = ((value * AFFILIATE_PERCENT_USDT) // decimal.Decimal(1000));
            user[account]["lamons"] += feeUSDT
            user[account]["refearnUSDT"] += feeUSDT
            account = user[account]["partner"]

    def __updateprePayment(self, account):
        block_timestamp = self.transaction["block_timestamp"]
        user = self.user

        lost_reward = 0
        reward_time = decimal.Decimal(block_timestamp) - decimal.Decimal(user[account]["timestamp"])
        if reward_time > 86400:
            lost_time = reward_time - 86400
            reward_time = 86400
            lost_reward += (((user[account]["deposit"] // decimal.Decimal(100)) * user[account]["percentage"]) //
                      decimal.Decimal(10000000000)) * lost_time
        reward = (((user[account]["deposit"] // decimal.Decimal(100)) * user[account]["percentage"]) //
                  decimal.Decimal(10000000000)) * reward_time
        if reward > user[account]["maxEarnings"]:
            lost_reward += reward - user[account]["maxEarnings"]
        self.lost_profit += lost_reward

        pending = self.checkReward(account)
        user[account]["timestamp"] = block_timestamp
        user[account]["lamons"] += pending
        user[account]["earned"] += pending

    def checkReward(self, account):
        block_timestamp = self.transaction["block_timestamp"]
        user = self.user

        RewardTime = decimal.Decimal(block_timestamp) - decimal.Decimal(user[account]["timestamp"])
        RewardTime = decimal.Decimal(86400) if RewardTime >= 86400 else RewardTime
        reward = (((user[account]["deposit"] // decimal.Decimal(100)) * user[account]["percentage"]) //
                   decimal.Decimal(10000000000)) * RewardTime

        return user[account]["maxEarnings"] if reward > user[account]["maxEarnings"] else reward


    @staticmethod
    def get_function_name(signature):
        signature = signature.lower()
        function_name = function_signatures.get(signature, "UnknownFunction")
        return function_name

    def print_analytics(self):
        result_message = ""

        real_contract_balance = self.get_contract_balance()
        result_message += f"\nDune: {self.contract_balance / 10**_DECIMALS} USDT | Chain: {real_contract_balance / 10**_DECIMALS} USDT | Difference: {abs(real_contract_balance - self.contract_balance) / 10**_DECIMALS} USDT"

        not_invested = sum([user_value['lamons'] for user_value in self.user.values()])
        total_earned = sum([user_value['earned'] for user_value in self.user.values()])
        result_message += f"\n\nNot invested money: {not_invested / 10**_DECIMALS} USDT"
        result_message += f"\nTotal Earned: {total_earned / 10**_DECIMALS} USDT"

        daily_income = sum([user_value['deposit'] // 100 * INIT_SECOND_PERCENT // decimal.Decimal("10000000000") * 86400 for user_value in self.user.values()])
        pending_reward = decimal.Decimal("0")
        self.transaction = {"block_timestamp": int(time.time())}
        for user, user_value in self.user.items():
            pending_reward += self.checkReward(user)
            self.__updateprePayment(user)

        result_message += f"\nTotal lost profit: {self.lost_profit / 10 ** _DECIMALS} USDT"
        result_message += f"\n\nDaily Income: {daily_income / 10 ** _DECIMALS} USDT"
        day_alive = (real_contract_balance - not_invested - pending_reward) / daily_income

        percent = decimal.Decimal(1e18) * INIT_SECOND_PERCENT // decimal.Decimal("10000000000") * 86400 / decimal.Decimal(1e18)
        result_message += f"\n\nPredict: {day_alive.quantize(decimal.Decimal('0.00000001'))} Days / Payback: {day_alive.quantize(decimal.Decimal('0.00000001')) * percent} %"
        result_message += "\n\n\n"
        print(result_message)
        result_message = "# " + datetime.datetime.now().strftime("%Y %m.%d %H:%M:%S") + result_message
        self.save_analytics(message=result_message)

    def save_analytics(self, message):
        with open("Reports/LamonReboot.txt", "a") as file:
            file.write(message)

    def get_contract_balance(self, block_number="latest"):
        url = "https://rpc.ankr.com/bsc"
        data = {
            "method": "eth_call",
            "params": [
                {"to": "0x55d398326f99059fF775485246999027B3197955",
                 "data": "0x70a08231" + "fea20421c1c73a451b7c0d5a4414ac14e63e0414".zfill(64)},
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