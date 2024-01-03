import json, string, traceback, requests, datetime
import time

from Modules.Statistics import BaseStatistics

function_signatures = {
    "273e0bd3": "ReplenishBalance",
    "ba98d6c5": "BuyCharacter",
    "4d6ce1e5": "Deposit",
    "f9186f0a": "BankDividends",
    "5b6b431d": "Withdraw",
    "b8ebd7f7": "MakeBid",  # Unused chain-Elixir
    "f192553e": "StartNewRound",  # Unused chain-Elixir
    "7a1a7456": "WitchCraft",
    "78e70088": "WithdrawElixir",
    "6f699ab2": "createBattle",
    "f2fde38b": "transferOwnership",  # Unused
    "715018a6": "renounceOwnership"  # Unused
}
START_SIGNATURE_INDEX = 2
START_DATA_INDEX = START_SIGNATURE_INDEX + 8
NULL_ADDRESS = "0x0000000000000000000000000000000000000000"
OWNER1_RECEIVER = "0x797878AD12bcE357b853E8E499dD68D4D883283b"
OWNER2_RECEIVER = "0xD60673A98F2424C315a40c3cEC6e4Ff5dcB74eb9"
PERCENT = 120
AFFILIATE_PERCENTS_1 = [30, 10]
AFFILIATE_PERCENTS_2 = [40, 15]
AFFILIATE_PERCENTS_3 = [50, 20]
AFFILIATE_PERCENTS_4 = [70, 25]
AFFILIATE_PERCENTS_5 = [100, 30]
_DECIMALS = 18


class User(dict):
    def __getitem__(self, key):
        if (not key.startswith("0x")) or len(key) != 42 or any([letter not in string.hexdigits for letter in key[2:]]):
            raise ValueError(f"Key is not address: {key}")
        if key not in self:
            self[key] = self._get_default_value()

        # for i in self.get(key, {}).values():
        #     if isinstance(i, int) and i < 0:
        #         print(1)
        return self.get(key)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)

    def _get_default_value(self):
        default_values = {
            "character": 0,
            "money": 0,
            "frozen": 0,
            "token_hold": 0,
            "elixir": 0,
            "deposit": 0,
            "earned": 0,
            "total_earned": 0,
            "withdrawn": 0,
            "timestamp": 0,
            "percentage": 0,
            "partner": NULL_ADDRESS
        }
        return default_values


class UserStats(dict):
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
            "skill": 0,
            "skill_timestamp": 0,
            "replenished": 0,
            "refsTotal": 0,
            "refs1level": 0,
            "turnover": 0,
            "turnover_total": 0,
            "refearnUSDT": 0,
            "status": 0
        }
        return default_values

class Forest_Battle(dict):
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
            "money": 0,
            "timestamp": 0,
            "winner": NULL_ADDRESS,
            "roll": 0
        }
        return default_values

class Forest(dict):
    def __getitem__(self, key):
        if (not key.startswith("0x")) or len(key) != 42 or any([letter not in string.hexdigits for letter in key[2:]]):
            raise ValueError(f"Key is not address: {key}")
        if key not in self:
            self[key] = self._get_default_value()
        return self.get(key)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)

    def _get_default_value(self):
        return Forest_Battle()

class waitingBattles(dict):
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

class HogwardsOnline(BaseStatistics):
    def __init__(self):
        with open("Resources/HogwardsOnline/battle_rolls.txt", "r") as file:
            self.__battle_rolls = json.load(file)

        self.contract_balance = 0
        self.total_investors = 0
        self.user = User()
        self.user_stats = UserStats()
        self.forest = Forest()
        self.waiting_battles = waitingBattles()

        self.lost_profit = 0

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
            case "ReplenishBalance":
                self.__fetch_ReplenishBalance(transaction=transaction)

            case "BuyCharacter":
                self.__fetch_BuyCharacter(transaction=transaction)

            case "Deposit":
                self.__fetch_Deposit(transaction=transaction)

            case "BankDividends":
                self.__fetch_BankDividends(transaction=transaction)

            case "Withdraw":
                self.__fetch_Withdraw(transaction=transaction)

            case "createBattle":
                self.__fetch_createBattle(transaction=transaction)

            case "WithdrawElixir":
                self.__fetch_WithdrawElixir(transaction=transaction)

            case "StartNewRound":
                self.__fetch_WitchCraft(transaction=transaction)

            case "MakeBid":
                pass

            case "WitchCraft":
                pass

            case "renounceOwnership":
                pass

            case "transferOwnership":
                pass

            case _:
                print(f"{function_name} | {transaction['hash']}")

        del self.transaction

    def __fetch_ReplenishBalance(self, transaction):  # not add ELIXIR
        _msgSender = transaction["from"]

        amount = int(transaction["data"][:64 * 1], 16)
        tokenIndex = int(transaction["data"][64 * 1: 64 * 2], 16)

        if tokenIndex == 0:
            self.user[_msgSender]["money"] += amount
            self.user[_msgSender]["frozen"] += amount
            self.user_stats[_msgSender]["replenished"] += amount

            self.contract_balance += (amount * (1000 - 65)) // 1000

        else:
            self.user[_msgSender]["elixir"] += amount
            self.user[_msgSender]["token_hold"] = self.transaction["block_timestamp"] + (86400 * 7)
            self._updatePercentage(_msgSender)

    def __fetch_Deposit(self, transaction):
        _msgSender = transaction["from"]

        amount = int(transaction["data"][:64 * 1], 16)

        updateFrozen = 0 if self.user[_msgSender]["frozen"] <= amount else self.user[_msgSender]["frozen"] - amount
        self.user[_msgSender]["frozen"] = updateFrozen
        # if self.user[_msgSender]["money"] - amount < 0:
        #     print(1)
        self.user[_msgSender]["money"] -= amount
        self.user[_msgSender]["deposit"] += amount
        self.user[_msgSender]["timestamp"] = transaction["block_timestamp"]

        if self.user[_msgSender]["percentage"] == 0:
            self.user[_msgSender]["percentage"] = PERCENT
            self.user_stats[_msgSender]["status"] = 1
        self._referralAccrual(self.user[_msgSender]["partner"], amount)

    def _referralAccrual(self, account, value):
        if value > 0 and account != NULL_ADDRESS:
            for i in range(2):
                affPercent = AFFILIATE_PERCENTS_1[i]
                if self.user_stats[account]["status"] == 2:
                    affPercent = AFFILIATE_PERCENTS_2[i]
                elif self.user_stats[account]["status"] == 3:
                    affPercent = AFFILIATE_PERCENTS_3[i]
                elif self.user_stats[account]["status"] == 4:
                    affPercent = AFFILIATE_PERCENTS_4[i]
                elif self.user_stats[account]["status"] == 5:
                    affPercent = AFFILIATE_PERCENTS_5[i]
                feeUSDT = (value * affPercent) // 1000
                self.user[account]["money"] += feeUSDT
                self.user_stats[account]["refearnUSDT"] += feeUSDT
                self.user_stats[account]["turnover_total"] += value

                if i == 0:
                    self.user_stats[account]["turnover"] += value
                    self._updateRefStatus(account, self.user_stats[account]["turnover"])

                account = self.user[account]["partner"]
                if account == NULL_ADDRESS:
                    break

    def _updateRefStatus(self, account, turnover):
        decimalsMod = 10 ** _DECIMALS
        refStatus = 0
        if (turnover >= 0 and turnover < 2500 * decimalsMod):
            refStatus = 1
        elif (turnover >= 2500 * decimalsMod and turnover < 10000 * decimalsMod):
            refStatus = 2
        elif (turnover >= 10000 * decimalsMod and turnover < 50000 * decimalsMod):
            refStatus = 3
        elif (turnover >= 50000 * decimalsMod and turnover < 100000 * decimalsMod):
            refStatus = 4
        elif (turnover >= 100000 * decimalsMod):
            refStatus = 5

        if self.user_stats[account]["status"] != refStatus:
            self.user_stats[account]["status"] = refStatus
            self._updatePercentage(account)

    def _updatePercentage(self, account):
        updPercentage = PERCENT
        tokenBalance = self.user[account]["elixir"] // (10 ** _DECIMALS) if (
                    self.user[account]["elixir"] >= 1000) else 0
        additionalPerc = 1
        TOKENLIMIT = 50000 * 10 ** _DECIMALS

        if (tokenBalance <= TOKENLIMIT):
            updPercentage += tokenBalance // 1000 * additionalPerc if (tokenBalance >= 1000) else 0
        else:
            updPercentage += 50

        if self.user_stats[account]["status"] == 1:
            updPercentage += 0
        elif self.user_stats[account]["status"] == 2:
            updPercentage += 10
        elif self.user_stats[account]["status"] == 3:
            updPercentage += 20
        elif self.user_stats[account]["status"] == 4:
            updPercentage += 50
        elif self.user_stats[account]["status"] == 5:
            updPercentage += 100

        if self.user[account]["percentage"] != updPercentage:
            self.user[account]["percentage"] = updPercentage

    def __fetch_BankDividends(self, transaction):
        _msgSender = transaction["from"]

        pending = self._pendingReward(_msgSender)
        depo_end = (self.user[_msgSender]["deposit"] * 222) // 100

        if (pending > 0):
            self.user[_msgSender]["timestamp"] = transaction["block_timestamp"]
            self.user[_msgSender]["money"] += pending
            self.user[_msgSender]["total_earned"] += pending
            self.user[_msgSender]["earned"] += pending

        if (self.user[_msgSender]["earned"] >= depo_end):
            self.user[_msgSender]["deposit"] = 0
            self.user[_msgSender]["earned"] = 0
            self.user[_msgSender]["timestamp"] = 0

    def _pendingReward(self, account):
        DiffUnix = (self.transaction["block_timestamp"] - self.user[account]["timestamp"]) // 60
        IncomePerMinute = (self.user[account]["percentage"] * 10 ** _DECIMALS) // 1440
        Reward = 0

        if (DiffUnix > 0):
            if (self.user[account]["deposit"] < (84 * 10 ** _DECIMALS)):
                Reward = (self.user[account]["deposit"] * IncomePerMinute * DiffUnix) // 10 ** 22

                if Reward > (1 * 10 ** _DECIMALS):
                    self.lost_profit += Reward - 1 * 10 ** _DECIMALS

                Reward = (1 * 10 ** _DECIMALS) if (Reward >= (1 * 10 ** _DECIMALS)) else Reward


            else:
                if DiffUnix > 1440:
                    self.lost_profit += (self.user[account]["deposit"] * IncomePerMinute * (DiffUnix - 1440)) // 10 ** 22

                DiffUnix = 1440 if (DiffUnix > 1440) else DiffUnix
                Reward = (self.user[account]["deposit"] * IncomePerMinute * DiffUnix) // 10 ** 22

        return Reward

    def __fetch_Withdraw(self, transaction):
        _msgSender = transaction["from"]

        amount = int(transaction["data"][:64], 16)

        if self.user[_msgSender]["money"] - amount < 0:
            print(1)
        self.user[_msgSender]["money"] -= amount
        self.user[_msgSender]["withdrawn"] += amount

        self.contract_balance -= amount

    def __fetch_WitchCraft(self, transaction):
        _msgSender = transaction["from"]

        self.user_stats[_msgSender]["skill"] += 1

    def __fetch_createBattle(self, transaction):
        _msgSender = transaction["from"]

        battleType = int(transaction["data"][64*0:64*1], 16)

        Creator = self.waiting_battles[battleType]
        if Creator == NULL_ADDRESS:
            self._createBattle(battleType)
        else:
            self._joinBattle(battleType, Creator)
            self._fightBattle(battleType, Creator)

    def _joinBattle(self, battleType, Creator):
        _msgSender = self.transaction["from"]
        block_timestamp = self.transaction["block_timestamp"]

        self.forest[Creator][battleType]["timestamp"] = block_timestamp
        self.forest[Creator][battleType]["player2"] = _msgSender
        priceBattle = self.forest[Creator][battleType]["money"]
        updateFrozen = 0 if (self.user[_msgSender]["frozen"] <= priceBattle) else (self.user[_msgSender]["frozen"] - priceBattle)
        self.user[_msgSender]["frozen"] = updateFrozen
        self.user[_msgSender]["money"] -= priceBattle
        self.waiting_battles[battleType] = NULL_ADDRESS

    def _fightBattle(self, battleType, Creator):
        # random = 50 # IDK HOW RECEIVE block.prevrandao
        random = self.__get_battle_roll(battleType, Creator, self.transaction["block_number"]) # IDK HOW RECEIVE block.prevrandao
        wAmount = self.forest[Creator][battleType]["money"] * 2
        fee = (wAmount * 10) / 100

        skill1 = self.user_stats[self.forest[Creator][battleType]["player1"]]["skill"]
        skill2 = self.user_stats[self.forest[Creator][battleType]["player2"]]["skill"]
        chance = 50

        if (skill1 > skill2):
            diff = skill1 - skill2
            chance = 60 if (diff <= 20) else 75

        elif (skill1 < skill2):
            diff = skill2 - skill1
            chance = 40 if (diff <= 20) else 25

        winner = self.forest[Creator][battleType]["player1"] if random < chance else self.forest[Creator][battleType]["player2"]

        self.user[winner]["money"] += wAmount - fee

        self.forest[Creator][battleType]["winner"] = winner
        self.forest[Creator][battleType]["roll"] = random

        self.user[OWNER1_RECEIVER]["money"] += fee // 2
        self.user[OWNER2_RECEIVER]["money"] += fee // 2


    def _createBattle(self, battleType):
        block_timestamp = self.transaction["block_timestamp"]
        _msgSender = self.transaction["from"]

        self.forest[_msgSender][battleType]["timestamp"] = block_timestamp
        self.forest[_msgSender][battleType]["player1"] = _msgSender
        self.forest[_msgSender][battleType]["player2"] = NULL_ADDRESS
        self.forest[_msgSender][battleType]["winner"] = NULL_ADDRESS
        self.forest[_msgSender][battleType]["money"] = self._getBattleType(battleType)
        self.forest[_msgSender][battleType]["roll"] = 0
        priceBattle = self.forest[_msgSender][battleType]["money"]
        updateFrozen = 0 if self.user[_msgSender]["frozen"] <= priceBattle else self.user[_msgSender]["frozen"] - priceBattle
        self.user[_msgSender]["frozen"] = updateFrozen
        self.user[_msgSender]["money"] -= priceBattle
        self.waiting_battles[battleType] = _msgSender

    def _getBattleType(self, battleType):
        return [10000000000000000000, 50000000000000000000, 100000000000000000000][battleType]

    def __fetch_WithdrawElixir(self, transaction):
        _msgSender = transaction["from"]
        amount = int(transaction["data"][START_DATA_INDEX:], 16)

        self.user[_msgSender]["elixir"] -= amount
        self._updatePercentage(_msgSender)
    def __fetch_BuyCharacter(self, transaction):
        _msgSender = transaction["from"]

        character = int(transaction["data"][:64 * 1], 16)
        partner = "0x" + transaction["data"][64 * 1 + 24:+ 64 * 2]

        if self.total_investors >= 888:
            priceCharacter = 10 * 10 ** _DECIMALS

            self.user[_msgSender]["money"] -= priceCharacter
            updateFrozen = 0 if self.user[_msgSender]["frozen"] <= priceCharacter else self.user[_msgSender][
                                                                                           "frozen"] - priceCharacter
            self.user[_msgSender]["frozen"] = updateFrozen

        self.user[_msgSender]["character"] = character

        ref = NULL_ADDRESS if self.user_stats[partner]["status"] == 0 else partner
        self.user[_msgSender]["partner"] = ref
        self.user_stats[ref]["refs1level"] += 1
        self.user_stats[ref]["refsTotal"] += 1

        if self.user[ref]["partner"] != NULL_ADDRESS:
            self.user_stats[self.user[ref]["partner"]]["refsTotal"] += 1

        self.total_investors += 1

    @staticmethod
    def get_function_name(signature):
        signature = signature.lower()
        function_name = function_signatures.get(signature, "UnknownFunction")
        return function_name

    def __get_battle_roll(self, battleType, creator, block_number):
        block_number = block_number + 1
        key = f"{creator}_{battleType}_{block_number}"
        roll = self.__battle_rolls.get(key, None)
        if not (roll is None):
            return roll
        url = "https://rpc.ankr.com/bsc"
        data = {
            "method": "eth_call",
            "params": [
                {"to": "0x0a928147667879d024cAd8D7E384CCE828B7B3E7",
                "data": "0xb54f57ee" + creator[2:].zfill(64) + hex(battleType)[2:].zfill(64)},
            block_number],
            "id": 1,
            "json-rpc": "2.0"
        }
        try:
            response = requests.post(url, json=data)
            result = response.json()["result"]
            roll = [int(result[i:i+64], 16) for i in range(2, len(result), 64)][5]
            self.__battle_rolls[key] = roll
            with open("Resources/HogwardsOnline/battle_rolls.txt", "w") as file:
                json.dump(self.__battle_rolls, file, indent=4, ensure_ascii=False)
            return roll
        except:
            traceback.print_exc()
            self.__get_battle_roll(creator, battleType, block_number)

    def print_analytics(self):
        # TODO total lost by confiitions
        # TODO total lost by confiitions

        result_message = ""
        real_contract_balance = self.get_contract_balance()
        result_message += f"\nDune: {self.contract_balance / 10**_DECIMALS} | Chain: {real_contract_balance / 10**_DECIMALS} USDT | Difference: {abs(real_contract_balance - self.contract_balance) / 10**_DECIMALS} USDT"

        not_invested = sum([i['money'] for i in self.user.values()])
        result_message += f"\n\nNot invested money: {not_invested / 10**_DECIMALS} USDT"
        result_message += f"\nTotal Earned: {sum([i['total_earned'] for i in self.user.values()]) / 10**_DECIMALS} USDT"

        wait_claim = 0
        now_timestamp = int(time.time())
        for user in self.user.values():
            DiffUnix = (now_timestamp - user["timestamp"]) // 60
            IncomePerMinute = (user["percentage"] * 10 ** _DECIMALS) // 1440

            if (DiffUnix > 0):
                if (user["deposit"] < (84 * 10 ** _DECIMALS)):
                    reward = (user["deposit"] * IncomePerMinute * DiffUnix) // 10 ** 22
                    if reward > (1 * 10 ** _DECIMALS):
                        self.lost_profit += reward - 1 * 10 ** _DECIMALS
                    reward = (1 * 10 ** _DECIMALS) if (reward >= (1 * 10 ** _DECIMALS)) else reward
                else:
                    if DiffUnix > 1440:
                        self.lost_profit += (user["deposit"] * IncomePerMinute * (
                                    DiffUnix - 1440)) // 10 ** 22
                    DiffUnix = 1440 if (DiffUnix > 1440) else DiffUnix
                    reward = (user["deposit"] * IncomePerMinute * DiffUnix) // 10 ** 22
                wait_claim += reward

        result_message += f"\nTotal lost profit: {self.lost_profit / 10**_DECIMALS} USDT"

        nature_daily = 0
        MAX_daily = 0
        for i in self.user.values():
            nature_daily += (i["deposit"] * i["percentage"]) / 10**4
            MAX_daily += (i["deposit"] * 270) / 10**4

        result_message += f"\n\nNature Daily: {nature_daily / 10**_DECIMALS} USDT"
        result_message += f"\nMAX Daily: {MAX_daily / 10**_DECIMALS} USDT"

        day_alive = (real_contract_balance - not_invested - wait_claim) / nature_daily
        result_message += f"\n\nPredict: {day_alive} Days / Payback: {day_alive * 1.2} %"
        result_message += "\n\n\n"

        print(result_message)
        result_message = "# " + datetime.datetime.now().strftime("%Y %m.%d %H:%M:%S") + result_message
        self.save_analytics(message=result_message)

    def save_analytics(self, message):
        with open("Reports/HogwardsOnline.txt", "a") as file:
            file.write(message)

    def get_contract_balance(self):
            url = "https://rpc.ankr.com/bsc"
            data = {
                "method": "eth_call",
                "params": [
                    {"to": "0x55d398326f99059fF775485246999027B3197955",
                     "data": "0x70a08231" + "0a928147667879d024cad8d7e384cce828b7b3e7".zfill(64)},
                    "latest"],
                "id": 1,
                "json-rpc": "2.0"
            }
            try:
                response = requests.post(url, json=data)
                return int(response.json()["result"][2:], 16)
            except:
                traceback.print_exc()
                return self.get_contract_balance()