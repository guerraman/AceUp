# backend/core/shoe.py
from dataclasses import dataclass, field
from typing import Dict

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
TOTAL_DECKS = 6
PER_RANK = 4 * TOTAL_DECKS  # = 24 (NUNCA cambiar esta fórmula)

# Valores Hi-Lo para conteo
HI_LO = {
    "A": -1,
    "2": +1, "3": +1, "4": +1, "5": +1, "6": +1,
    "7":  0, "8":  0, "9":  0,
    "10": -1, "J": -1, "Q": -1, "K": -1
}


@dataclass
class Shoe:
    decks: int = TOTAL_DECKS
    cards: Dict[str, int] = field(
        default_factory=lambda: {r: PER_RANK for r in RANKS}
    )
    running_count: int = 0
    cards_dealt: int = 0

    def use_card(self, rank: str) -> bool:
        """Registra una carta jugada. Retorna False si no hay cartas de ese rango."""
        if self.cards.get(rank, 0) <= 0:
            return False
        self.cards[rank] -= 1
        self.cards_dealt += 1
        self.running_count += HI_LO.get(rank, 0)
        return True

    def undo_card(self, rank: str) -> bool:
        """Revierte una carta (para correcciones del usuario)."""
        if self.cards.get(rank, 0) >= PER_RANK:
            return False
        self.cards[rank] += 1
        self.cards_dealt -= 1
        self.running_count -= HI_LO.get(rank, 0)
        return True

    def reset(self):
        """Resetea el mazo completo (nuevo juego)."""
        self.cards = {r: PER_RANK for r in RANKS}
        self.running_count = 0
        self.cards_dealt = 0

    @property
    def cards_left(self) -> int:
        return sum(self.cards.values())

    @property
    def decks_remaining(self) -> float:
        """Nunca retornar menos de 0.5 para evitar división por cero."""
        return max(0.5, self.cards_left / 52)

    @property
    def true_count(self) -> float:
        """True Count = Running Count / Mazos Restantes"""
        return self.running_count / self.decks_remaining

    @property
    def prob_ten(self) -> float:
        """Probabilidad de que la siguiente carta valga 10."""
        tens = sum(self.cards[r] for r in ["10", "J", "Q", "K"])
        return tens / self.cards_left if self.cards_left > 0 else 0

    @property
    def net_edge(self) -> float:
        """
        Ventaja neta del jugador en %.
        Base house edge 6 mazos S17 DAS = ~0.44%
        Por cada punto de TC sobre 1: +0.5%
        """
        base = -0.44  # casa tiene ventaja base
        tc_bonus = max(0, (self.true_count - 1) * 0.5)
        return base + tc_bonus

    def to_dict(self) -> dict:
        return {
            "cards": self.cards,
            "running_count": self.running_count,
            "true_count": round(self.true_count, 2),
            "cards_left": self.cards_left,
            "decks_remaining": round(self.decks_remaining, 1),
            "prob_ten": round(self.prob_ten * 100, 1),
            "net_edge": round(self.net_edge, 2),
        }
