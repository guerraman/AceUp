# backend/core/counter.py

CARD_VALUES = {
    "A": 11, "2": 2, "3": 3, "4": 4, "5": 5,
    "6": 6,  "7": 7, "8": 8, "9": 9,
    "10": 10, "J": 10, "Q": 10, "K": 10
}

def card_value(rank: str) -> int:
    return CARD_VALUES.get(rank, 0)


def hand_value(cards: list[str]) -> int:
    """Calcula el valor óptimo de una mano (As vale 11 o 1 según convenga)."""
    total, aces = 0, 0
    for r in cards:
        if r == "A":
            aces += 1
            total += 11
        else:
            total += card_value(r)
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def is_soft(cards: list[str]) -> bool:
    """True si la mano tiene un As contando como 11 (mano blanda)."""
    total, aces = 0, 0
    for r in cards:
        if r == "A":
            aces += 1
            total += 11
        else:
            total += card_value(r)
    return aces > 0 and total <= 21


def is_pair(cards: list[str]) -> bool:
    """True si exactamente 2 cartas con el mismo valor numérico."""
    if len(cards) != 2:
        return False
    return card_value(cards[0]) == card_value(cards[1])


def dealer_up_value(rank: str) -> int:
    """Valor de la carta visible del dealer para indexar las tablas."""
    return 11 if rank == "A" else card_value(rank)
