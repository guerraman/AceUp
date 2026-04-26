# backend/core/deviations.py

def apply_deviations(
    basic_action: str,
    player_cards: list[str],
    dealer_card: str,
    true_count: float,
    player_total: int,
    dealer_val: int,
    soft: bool,
    pair: bool,
) -> tuple[str, str]:
    tc = true_count

    # FAB 4 — Surrender por conteo (verificar PRIMERO)
    if player_total == 15 and dealer_val == 10 and tc >= 0:
        return "R", f"[Fab4] 15 vs 10 con TC {tc:.1f} >= 0 -> Rendirse"
    if player_total == 14 and dealer_val == 10 and tc >= 3:
        return "R", f"[Fab4] 14 vs 10 con TC {tc:.1f} >= 3 -> Rendirse"
    if player_total == 15 and dealer_val == 9 and tc >= 2:
        return "R", f"[Fab4] 15 vs 9 con TC {tc:.1f} >= 2 -> Rendirse"
    if player_total == 15 and dealer_val == 11 and tc >= 1:
        return "R", f"[Fab4] 15 vs As con TC {tc:.1f} >= 1 -> Rendirse"

    # ILLUSTRIOUS 18
    if player_total == 16 and dealer_val == 10 and not soft and tc >= 0:
        return "S", f"[I18] 16 vs 10 con TC {tc:.1f} >= 0 -> Plantarse"
    if player_total == 15 and dealer_val == 10 and not soft and tc >= 4:
        return "S", f"[I18] 15 vs 10 con TC {tc:.1f} >= 4 -> Plantarse"
    if pair and player_total == 20 and dealer_val == 6 and tc >= 4:
        return "P", f"[I18] 10,10 vs 6 con TC {tc:.1f} >= 4 -> Dividir"
    if pair and player_total == 20 and dealer_val == 5 and tc >= 5:
        return "P", f"[I18] 10,10 vs 5 con TC {tc:.1f} >= 5 -> Dividir"
    if player_total == 11 and dealer_val == 11 and tc >= 1:
        return "D", f"[I18] 11 vs As con TC {tc:.1f} >= 1 -> Doblar"
    if player_total == 10 and dealer_val == 11 and tc >= 4:
        return "D", f"[I18] 10 vs As con TC {tc:.1f} >= 4 -> Doblar"
    if player_total == 10 and dealer_val == 10 and tc >= 4:
        return "D", f"[I18] 10 vs 10 con TC {tc:.1f} >= 4 -> Doblar"
    if player_total == 12 and dealer_val == 3 and not soft and tc >= 2:
        return "S", f"[I18] 12 vs 3 con TC {tc:.1f} >= 2 -> Plantarse"
    if player_total == 12 and dealer_val == 2 and not soft and tc >= 3:
        return "S", f"[I18] 12 vs 2 con TC {tc:.1f} >= 3 -> Plantarse"
    if player_total == 13 and dealer_val == 2 and not soft and tc <= -1:
        return "H", f"[I18] 13 vs 2 con TC {tc:.1f} <= -1 -> Pedir carta"
    if player_total == 9 and dealer_val == 2 and not soft and tc >= 1:
        return "D", f"[I18] 9 vs 2 con TC {tc:.1f} >= 1 -> Doblar"
    if player_total == 9 and dealer_val == 7 and not soft and tc >= 3:
        return "D", f"[I18] 9 vs 7 con TC {tc:.1f} >= 3 -> Doblar"
    if player_total == 16 and dealer_val == 9 and not soft and tc >= 5:
        return "S", f"[I18] 16 vs 9 con TC {tc:.1f} >= 5 -> Plantarse"
    if player_total == 13 and dealer_val == 3 and not soft and tc <= -2:
        return "H", f"[I18] 13 vs 3 con TC {tc:.1f} <= -2 -> Pedir carta"

    return basic_action, ""


def get_insurance_advice(player_cards: list[str], prob_ten: float, true_count: float) -> dict:
    from .counter import hand_value
    pv = hand_value(player_cards)
    is_bj = len(player_cards) == 2 and pv == 21
    pct_ten = round(prob_ten * 100, 1)
    tc_str = f"{true_count:.1f}"

    if is_bj:
        return {
            "verdict": "RECHAZA el seguro",
            "type": "reject",
            "reason": f"Tienes Blackjack. Rechazar seguro es mejor EV. 10s restantes: {pct_ten}%."
        }
    if true_count >= 3:
        return {
            "verdict": "CONSIDERA el seguro",
            "type": "consider",
            "reason": f"TC = +{tc_str} — mazo cargado de 10s ({pct_ten}%). Seguro rentable."
        }
    return {
        "verdict": "RECHAZA el seguro",
        "type": "reject",
        "reason": f"Solo {pct_ten}% son 10s (necesitas >33.3%). TC = {tc_str}. No tomar seguro."
    }
