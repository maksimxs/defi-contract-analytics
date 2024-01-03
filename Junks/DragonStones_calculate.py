costs = [
    [1000, 4000, 10000, 25000, 50000],
    [1500, 5000, 12500, 30000, 60000],
    [2000, 6000, 15000, 35000, 70000],
    [2500, 7000, 17500, 40000, 80000],
    [3000, 8000, 20000, 45000, 100000]
]

yields = [
    [75, 321, 854, 2266, 4792],
    [114, 406, 1081, 2750, 5813],
    [154, 494, 1313, 3245, 6854],
    [195, 583, 1549, 3750, 7917],
    [238, 675, 1792, 4266, 10000]
]

COST_1_MANA = 0.0001
rows = len(yields)
columns = len(yields[0])

for i in range(columns):
    print(f"\nLEVEL: {i+1}")
    for e in range(rows):
        _cost, _yield = costs[e][i], yields[e][i]
        cost = _cost * 100
        print(f"Tower: {e+1} {_cost * COST_1_MANA} BNB | {_yield / cost * 24 * 100}% Per Day")