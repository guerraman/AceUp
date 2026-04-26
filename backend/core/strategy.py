# backend/core/strategy.py
from .counter import hand_value, is_soft, is_pair, dealer_up_value, card_value

# ─── MANOS DURAS ──────────────────────────────────────────────────
# Clave: total del jugador → {valor_dealer: accion}
HARD_TABLE = {
    # 5, 6, 7, 8: siempre Hit
    5:  {2:"H",3:"H",4:"H",5:"H",6:"H",7:"H",8:"H",9:"H",10:"H",11:"H"},
    6:  {2:"H",3:"H",4:"H",5:"H",6:"H",7:"H",8:"H",9:"H",10:"H",11:"H"},
    7:  {2:"H",3:"H",4:"H",5:"H",6:"H",7:"H",8:"H",9:"H",10:"H",11:"H"},
    8:  {2:"H",3:"H",4:"H",5:"H",6:"H",7:"H",8:"H",9:"H",10:"H",11:"H"},
    # 9: Doblar vs 3-6, Hit resto
    9:  {2:"H",3:"D",4:"D",5:"D",6:"D",7:"H",8:"H",9:"H",10:"H",11:"H"},
    # 10: Doblar vs 2-9, Hit vs 10/A
    10: {2:"D",3:"D",4:"D",5:"D",6:"D",7:"D",8:"D",9:"D",10:"H",11:"H"},
    # 11: Doblar siempre (incluso vs As en S17)
    11: {2:"D",3:"D",4:"D",5:"D",6:"D",7:"D",8:"D",9:"D",10:"D",11:"D"},
    # 12: Plantarse vs 4-6, Hit resto
    12: {2:"H",3:"H",4:"S",5:"S",6:"S",7:"H",8:"H",9:"H",10:"H",11:"H"},
    # 13-16: Plantarse vs 2-6, Hit vs 7+
    13: {2:"S",3:"S",4:"S",5:"S",6:"S",7:"H",8:"H",9:"H",10:"H",11:"H"},
    14: {2:"S",3:"S",4:"S",5:"S",6:"S",7:"H",8:"H",9:"H",10:"H",11:"H"},
    15: {2:"S",3:"S",4:"S",5:"S",6:"S",7:"H",8:"H",9:"H",10:"H",11:"H"},
    16: {2:"S",3:"S",4:"S",5:"S",6:"S",7:"H",8:"H",9:"H",10:"H",11:"H"},
    # 17+: Siempre Stand
    17: {k:"S" for k in [2,3,4,5,6,7,8,9,10,11]},
    18: {k:"S" for k in [2,3,4,5,6,7,8,9,10,11]},
    19: {k:"S" for k in [2,3,4,5,6,7,8,9,10,11]},
    20: {k:"S" for k in [2,3,4,5,6,7,8,9,10,11]},
    21: {k:"S" for k in [2,3,4,5,6,7,8,9,10,11]},
}

# ─── MANOS BLANDAS (con As) ────────────────────────────────────────
# Clave: total de la mano blanda
SOFT_TABLE = {
    # A,2 (Soft 13): Doblar vs 5-6
    13: {2:"H",3:"H",4:"H",5:"D",6:"D",7:"H",8:"H",9:"H",10:"H",11:"H"},
    # A,3 (Soft 14): Doblar vs 5-6
    14: {2:"H",3:"H",4:"H",5:"D",6:"D",7:"H",8:"H",9:"H",10:"H",11:"H"},
    # A,4 (Soft 15): Doblar vs 4-6
    15: {2:"H",3:"H",4:"D",5:"D",6:"D",7:"H",8:"H",9:"H",10:"H",11:"H"},
    # A,5 (Soft 16): Doblar vs 4-6
    16: {2:"H",3:"H",4:"D",5:"D",6:"D",7:"H",8:"H",9:"H",10:"H",11:"H"},
    # A,6 (Soft 17): Doblar vs 3-6
    17: {2:"H",3:"D",4:"D",5:"D",6:"D",7:"H",8:"H",9:"H",10:"H",11:"H"},
    # A,7 (Soft 18): CRÍTICO — Ds vs 3-6, Stand vs 2/7/8, Hit vs 9/10/A
    18: {2:"S",3:"Ds",4:"Ds",5:"Ds",6:"Ds",7:"S",8:"S",9:"H",10:"H",11:"H"},
    # A,8+ (Soft 19-21): Siempre Stand
    19: {k:"S" for k in [2,3,4,5,6,7,8,9,10,11]},
    20: {k:"S" for k in [2,3,4,5,6,7,8,9,10,11]},
    21: {k:"S" for k in [2,3,4,5,6,7,8,9,10,11]},
}

# ─── PARES ─────────────────────────────────────────────────────────
# Clave: rango de la carta (ambas iguales)
PAIRS_TABLE = {
    "A":  {k:"P" for k in [2,3,4,5,6,7,8,9,10,11]},   # Siempre Split
    "K":  {k:"S" for k in [2,3,4,5,6,7,8,9,10,11]},   # Nunca Split (como 10)
    "Q":  {k:"S" for k in [2,3,4,5,6,7,8,9,10,11]},
    "J":  {k:"S" for k in [2,3,4,5,6,7,8,9,10,11]},
    "10": {k:"S" for k in [2,3,4,5,6,7,8,9,10,11]},   # Nunca Split
    "9":  {2:"P",3:"P",4:"P",5:"P",6:"P",7:"S",8:"P",9:"P",10:"S",11:"S"},
    "8":  {k:"P" for k in [2,3,4,5,6,7,8,9,10,11]},   # Siempre Split
    "7":  {2:"P",3:"P",4:"P",5:"P",6:"P",7:"P",8:"H",9:"H",10:"H",11:"H"},
    "6":  {2:"P",3:"P",4:"P",5:"P",6:"P",7:"H",8:"H",9:"H",10:"H",11:"H"},
    "5":  {2:"D",3:"D",4:"D",5:"D",6:"D",7:"D",8:"D",9:"D",10:"H",11:"H"},  # Nunca Split, tratar como 10
    "4":  {2:"H",3:"H",4:"H",5:"P",6:"P",7:"H",8:"H",9:"H",10:"H",11:"H"},
    "3":  {2:"P",3:"P",4:"P",5:"P",6:"P",7:"P",8:"H",9:"H",10:"H",11:"H"},
    "2":  {2:"P",3:"P",4:"P",5:"P",6:"P",7:"P",8:"H",9:"H",10:"H",11:"H"},
}

# Labels en español para el frontend
ACTION_LABELS = {
    "H":  {"label": "PEDIR (Hit)",           "color": "hit"},
    "S":  {"label": "PLANTARSE (Stand)",      "color": "stand"},
    "D":  {"label": "DOBLAR (Double Down)",   "color": "double"},
    "Ds": {"label": "DOBLAR (Double Down)",   "color": "double"},
    "P":  {"label": "DIVIDIR (Split)",        "color": "split"},
    "R":  {"label": "RENDIRSE (Surrender)",   "color": "surrender"},
}

REASONS = {
    "H":  "Pide carta para mejorar tu mano.",
    "S":  "El riesgo de pasarte es alto. Plántate y deja que el dealer quiebre.",
    "D":  "Posición matemáticamente favorable. Dobla tu apuesta.",
    "Ds": "Dobla si puedes; si no, plántate.",
    "P":  "Dividir esta mano maximiza tu valor esperado.",
    "R":  "Rinde la mano y recupera la mitad de tu apuesta.",
}


def get_basic_strategy(player_cards: list[str], dealer_card: str) -> tuple[str, str]:
    """
    Retorna (accion, razon) según estrategia básica.
    No aplica desviaciones por conteo (eso lo hace deviations.py).
    """
    dv = dealer_up_value(dealer_card)
    pv = hand_value(player_cards)
    soft = is_soft(player_cards)
    pair = is_pair(player_cards)

    action = _lookup(player_cards, pv, soft, pair, dv)

    # Si la acción es "Ds" pero ya hay más de 2 cartas, no se puede doblar
    if action == "Ds" and len(player_cards) > 2:
        action = "S"

    reason = REASONS.get(action, "")
    return action, reason


def _lookup(cards, pv, soft, pair, dv):
    # Pares primero
    if pair:
        rank = cards[0]
        # Normalizar figuras a "10"
        if rank in ("K", "Q", "J"):
            rank = "10"
        table = PAIRS_TABLE.get(rank, {})
        return table.get(dv, "H")

    # Manos blandas
    if soft and pv in SOFT_TABLE:
        return SOFT_TABLE[pv].get(dv, "H")

    # Manos duras
    total = min(pv, 21)  # 21+ siempre Stand
    if total in HARD_TABLE:
        return HARD_TABLE[total].get(dv, "H")

    return "S" if pv >= 17 else "H"
