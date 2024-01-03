costs = [
    [690, 1900, 5900, 12900, 34900],
    [790, 2390, 6900, 13900, 39900],
    [990, 2900, 8600, 16900, 47500],
    [1200, 3600, 10900, 21900, 59900],
    [1490, 3990, 11990, 23900, 67500]
]

yields = [
    [66, 198, 669, 1585, 4649],
    [77, 252, 792, 1729, 5394],
    [97, 310, 1000, 2127, 6508],
    [119, 390, 1284, 2790, 8321],
    [150, 438, 1430, 3089, 9501]
]

COST_1_MANA = 0.0001
rows = len(yields)
columns = len(yields[0])

for i in range(columns):
    print(f"\nLEVEL: {i+1}")
    for e in range(rows):
        _cost, _yield = costs[e][i], yields[e][i]
        _cost = _cost * (10 / 12)
        cost = _cost * 100

        print(f"Tower: {e+1} {_cost * COST_1_MANA} BNB ({_cost} MANA) | {_yield / cost * 24 * 100}% Per Day | {cost / (_yield*24)} Days")

# Predict: 32.63412238 Days / Payback: 104.9187034517 %
