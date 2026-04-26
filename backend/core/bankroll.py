# backend/core/bankroll.py

BET_SPREAD = [
    (float('-inf'), -1,   0,  "Wonging Out — abandona la mesa"),
    (-1,             1,   1,  "EV negativo o neutro — apuesta minima"),
    ( 1,             2,   2,  "Ventaja ~+0.5% — apuesta moderada"),
    ( 2,             3,   4,  "Ventaja ~+1.0% — apuesta media"),
    ( 3,             4,   8,  "Ventaja ~+1.5% — apuesta alta"),
    ( 4,   float('inf'), 12,  "Ventaja maxima — apuesta completa"),
]


def get_units(true_count: float) -> tuple[int, str]:
    for tc_min, tc_max, units, note in BET_SPREAD:
        if tc_min <= true_count < tc_max:
            return units, note
    return 12, "Ventaja maxima"


def get_bet_recommendation(
    true_count: float,
    bankroll: float,
    min_bet: float = 10.0
) -> dict:
    units, note = get_units(true_count)

    if units == 0:
        return {
            "units": 0,
            "amount": 0,
            "action": "wong_out",
            "message": note,
            "edge_pct": round((true_count - 1) * 0.5, 2),
        }

    edge = max(0, (true_count - 1) * 0.005)
    kelly_full = edge / 1.33 if edge > 0 else 0
    kelly_half = kelly_full * 0.5
    kelly_amount = kelly_half * bankroll
    spread_amount = units * min_bet
    recommended = min(spread_amount, kelly_amount) if kelly_amount > 0 else spread_amount

    return {
        "units": units,
        "amount": round(recommended, 2),
        "spread_amount": spread_amount,
        "kelly_amount": round(kelly_amount, 2),
        "edge_pct": round(edge * 100, 2),
        "kelly_pct": round(kelly_half * 100, 3),
        "message": note,
        "true_count": round(true_count, 1),
    }
