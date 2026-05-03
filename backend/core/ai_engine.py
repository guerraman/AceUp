# backend/core/ai_engine.py
"""
Motor de Q-Learning para el Blackjack Assistant.
Aprende jugando manos simuladas contra un dealer programado (S17).
Se entrena en segundo plano y mejora con cada sesión real.

ALGORITMO: Q-Learning con epsilon-greedy y decay automático.
No requiere API externa. Corre 100% en el servidor.
"""
import json
import os
import math
import random
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ── Constantes ────────────────────────────────────────────────────
RANKS   = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
RV      = {"A":11,"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"8":8,"9":9,
           "10":10,"J":10,"Q":10,"K":10}
HI_LO   = {"A":-1,"2":1,"3":1,"4":1,"5":1,"6":1,"7":0,"8":0,"9":0,
           "10":-1,"J":-1,"Q":-1,"K":-1}
PER_RANK = 24       # 4 cartas/mazo × 6 mazos
ACTIONS  = ["H","S","D","P","R"]

# Hiperparámetros Q-Learning
ALPHA         = 0.1    # Tasa de aprendizaje
GAMMA         = 0.95   # Factor de descuento
EPSILON_START = 0.30   # Exploración inicial
EPSILON_MIN   = 0.03   # Mínima exploración
EPSILON_DECAY = 0.9999 # Decay por mano simulada

Q_FILE = Path("data/q_table.json")


# ── Utilidades de cartas ──────────────────────────────────────────
def card_val(r: str) -> int:
    return RV.get(r, 10)

def hand_value(cards: list[str]) -> int:
    total, aces = 0, 0
    for r in cards:
        if r == "A": aces += 1; total += 11
        else: total += card_val(r)
    while total > 21 and aces > 0:
        total -= 10; aces -= 1
    return total

def is_soft(cards: list[str]) -> bool:
    total, aces = 0, 0
    for r in cards:
        if r == "A": aces += 1; total += 11
        else: total += card_val(r)
    return aces > 0 and total <= 21

def is_pair(cards: list[str]) -> bool:
    return len(cards) == 2 and card_val(cards[0]) == card_val(cards[1])

def dealer_up_val(r: str) -> int:
    return 11 if r == "A" else card_val(r)


# ── Estado Q ──────────────────────────────────────────────────────
def state_key(player_total: int, dealer_up: int, soft: bool,
              pair: bool, tc_bucket: int) -> str:
    """
    Clave de estado compacta para la Q-table.
    tc_bucket: True Count redondeado y limitado entre -5 y +5.
    """
    return f"{player_total}_{dealer_up}_{int(soft)}_{int(pair)}_{tc_bucket}"

def tc_bucket(tc: float) -> int:
    return max(-5, min(5, round(tc)))


# ── Motor Q-Learning ──────────────────────────────────────────────
class QLearningEngine:
    def __init__(self):
        self.q: dict[str, dict[str, float]] = {}
        self.epsilon = EPSILON_START
        self.total_hands = 0
        self.wins = 0
        self.losses = 0
        self.pushes = 0
        self._load()

    # ── Persistencia ─────────────────────────────────────────────
    def _load(self):
        Q_FILE.parent.mkdir(exist_ok=True)
        if Q_FILE.exists():
            try:
                with open(Q_FILE) as f:
                    data = json.load(f)
                    self.q          = data.get("q", {})
                    self.epsilon    = data.get("epsilon", EPSILON_START)
                    self.total_hands= data.get("total_hands", 0)
                    self.wins       = data.get("wins", 0)
                    self.losses     = data.get("losses", 0)
                    self.pushes     = data.get("pushes", 0)
            except Exception:
                pass

    def save(self):
        Q_FILE.parent.mkdir(exist_ok=True)
        with open(Q_FILE, "w") as f:
            json.dump({
                "q": self.q,
                "epsilon": self.epsilon,
                "total_hands": self.total_hands,
                "wins": self.wins,
                "losses": self.losses,
                "pushes": self.pushes,
            }, f, separators=(",", ":"))

    # ── Q-table access ────────────────────────────────────────────
    def get_q(self, key: str, action: str) -> float:
        return self.q.get(key, {}).get(action, 0.0)

    def set_q(self, key: str, action: str, value: float):
        if key not in self.q:
            self.q[key] = {}
        self.q[key][action] = round(value, 6)

    def best_action(self, key: str, valid: list[str]) -> str:
        best, best_v = valid[0], -float("inf")
        for a in valid:
            v = self.get_q(key, a)
            if v > best_v:
                best_v = v; best = a
        return best

    def confidence(self, key: str) -> float:
        """
        Confianza 0-100 basada en la diferencia entre la mejor
        y segunda mejor acción en el estado.
        """
        vals = list(self.q.get(key, {}).values())
        if len(vals) < 2:
            return 0.0
        sorted_v = sorted(vals, reverse=True)
        diff = sorted_v[0] - sorted_v[1]
        return round(min(100.0, diff * 100 + 50), 1)

    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses
        return round(self.wins / total * 100, 1) if total > 0 else 0.0

    @property
    def state_count(self) -> int:
        return len(self.q)

    # ── Recomendación para mano real ──────────────────────────────
    def recommend(
        self,
        player_cards: list[str],
        dealer_card: str,
        true_count: float,
        basic_action: str,
    ) -> dict:
        """
        Combina estrategia básica + Illustrious 18 + Q-Learning.
        Solo sobreescribe la estrategia base si la IA tiene alta
        confianza y el valor Q es significativamente mejor.
        """
        pv   = hand_value(player_cards)
        soft = is_soft(player_cards)
        pair = is_pair(player_cards)
        dv   = dealer_up_val(dealer_card)
        key  = state_key(pv, dv, soft, pair, tc_bucket(true_count))
        conf = self.confidence(key)

        q_action = None
        q_override = False

        if key in self.q and len(self.q[key]) >= 3:
            q_best  = self.best_action(key, ACTIONS)
            q_val   = self.get_q(key, q_best)
            base_val= self.get_q(key, basic_action)

            # Solo override si la diferencia es significativa y hay confianza
            if q_val > base_val + 0.12 and conf > 65 and self.total_hands > 5000:
                q_action  = q_best
                q_override = True

        final_action = q_action if q_override else basic_action

        return {
            "action":        final_action,
            "q_override":    q_override,
            "q_action":      q_action,
            "base_action":   basic_action,
            "confidence":    conf,
            "total_hands":   self.total_hands,
            "win_rate":      self.win_rate,
            "state_count":   self.state_count,
            "q_values":      self.q.get(key, {}),
        }

    # ── Actualización con resultado real ─────────────────────────
    def update_from_real_hand(
        self,
        player_cards: list[str],
        dealer_card: str,
        true_count: float,
        action_taken: str,
        reward: float,          # +1 win, -1 loss, 0 push, +1.5 BJ
    ):
        """
        Actualiza la Q-table con el resultado de una mano REAL
        (no simulada). Esto permite aprendizaje online.
        """
        pv   = hand_value(player_cards)
        soft = is_soft(player_cards)
        pair = is_pair(player_cards)
        dv   = dealer_up_val(dealer_card)
        key  = state_key(pv, dv, soft, pair, tc_bucket(true_count))

        old = self.get_q(key, action_taken)
        new_val = old + ALPHA * (reward - old)
        self.set_q(key, action_taken, new_val)

        if reward > 0:   self.wins += 1
        elif reward < 0: self.losses += 1
        else:            self.pushes += 1

    # ── Entrenamiento por simulación ─────────────────────────────
    def train(self, n_hands: int = 50_000) -> dict:
        """
        Entrena la IA simulando n_hands manos completas contra
        un dealer programado que sigue las reglas S17.
        Llámalo en un background task de FastAPI.
        """
        sim_shoe = {r: PER_RANK for r in RANKS}
        rc = {"count": 0, "dealt": 0}

        for _ in range(n_hands):
            # Reshuffle si queda menos de 1 mazo
            if sum(sim_shoe.values()) < 52:
                sim_shoe = {r: PER_RANK for r in RANKS}
                rc = {"count": 0, "dealt": 0}

            reward = self._simulate_hand(sim_shoe, rc)
            if reward is None:
                continue

            self.total_hands += 1
            # Decay epsilon
            self.epsilon = max(EPSILON_MIN, self.epsilon * EPSILON_DECAY)

            if reward > 0:   self.wins += 1
            elif reward < 0: self.losses += 1
            else:            self.pushes += 1

        self.save()
        return {
            "total_hands": self.total_hands,
            "state_count": self.state_count,
            "win_rate":    self.win_rate,
            "epsilon":     round(self.epsilon, 4),
        }

    def _deal(self, sim_shoe: dict, rc: dict) -> Optional[str]:
        available = [r for r in RANKS if sim_shoe.get(r, 0) > 0]
        if not available:
            return None
        total = sum(sim_shoe[r] for r in available)
        rnd = random.random() * total
        for r in available:
            rnd -= sim_shoe[r]
            if rnd <= 0:
                sim_shoe[r] -= 1
                rc["dealt"]  += 1
                rc["count"]  += HI_LO.get(r, 0)
                return r
        r = available[-1]
        sim_shoe[r] -= 1
        rc["dealt"] += 1
        rc["count"] += HI_LO.get(r, 0)
        return r

    def _dealer_play(self, dealer_cards: list, sim_shoe: dict, rc: dict) -> int:
        """Dealer sigue reglas S17: planta en hard 17, pide en soft 17."""
        while True:
            dv = hand_value(dealer_cards)
            if dv > 21: return dv
            if dv > 17: return dv
            if dv == 17 and not is_soft(dealer_cards): return dv
            card = self._deal(sim_shoe, rc)
            if not card: break
            dealer_cards.append(card)
        return hand_value(dealer_cards)

    def _reward(self, pv: int, dv: int) -> float:
        if pv > 21:  return -1.0
        if dv > 21:  return +1.0
        if pv > dv:  return +1.0
        if pv < dv:  return -1.0
        return 0.0

    def _simulate_hand(self, sim_shoe: dict, rc: dict) -> Optional[float]:
        """Simula una mano completa con política epsilon-greedy."""
        p1 = self._deal(sim_shoe, rc); d1 = self._deal(sim_shoe, rc)
        p2 = self._deal(sim_shoe, rc); d2 = self._deal(sim_shoe, rc)
        if not all([p1, d1, p2, d2]):
            return None

        player = [p1, p2]
        dealer = [d1, d2]

        pv   = hand_value(player)
        soft = is_soft(player)
        pair = is_pair(player)
        dv   = dealer_up_val(d1)
        decks= max(0.5, sum(sim_shoe.values()) / 52)
        tc   = rc["count"] / decks
        key  = state_key(pv, dv, soft, pair, tc_bucket(tc))

        # Acción epsilon-greedy
        if random.random() < self.epsilon:
            action = random.choice(ACTIONS)
        else:
            action = self.best_action(key, ACTIONS)

        # Ejecutar acción
        reward = self._execute_action(action, player, dealer, sim_shoe, rc, key, tc)
        return reward

    def _execute_action(self, action, player, dealer, sim_shoe, rc, key, tc):
        # SPLIT
        if action == "P" and is_pair(player):
            r1 = self._resolve_single([player[0], self._deal(sim_shoe, rc) or player[0]],
                                      dealer[:], sim_shoe, rc, dealer_up_val(dealer[0]), tc)
            r2 = self._resolve_single([player[1], self._deal(sim_shoe, rc) or player[1]],
                                      dealer[:], sim_shoe, rc, dealer_up_val(dealer[0]), tc)
            reward = (r1 + r2) / 2.0
            self._update_q(key, action, reward, None)
            return reward

        # SURRENDER
        if action == "R":
            reward = -0.5
            self._update_q(key, action, reward, None)
            return reward

        # DOUBLE
        if action == "D":
            card = self._deal(sim_shoe, rc)
            if card: player.append(card)
            dv_final = self._dealer_play(dealer[:], sim_shoe, rc)
            reward = self._reward(hand_value(player), dv_final) * 2.0
            self._update_q(key, action, reward, None)
            return reward

        # STAND
        if action == "S":
            dv_final = self._dealer_play(dealer[:], sim_shoe, rc)
            reward = self._reward(hand_value(player), dv_final)
            self._update_q(key, action, reward, None)
            return reward

        # HIT — seguir pidiendo según Q / basic
        while True:
            card = self._deal(sim_shoe, rc)
            if not card: break
            player.append(card)
            pv2 = hand_value(player)
            if pv2 >= 21: break
            dv_up = dealer_up_val(dealer[0])
            key2  = state_key(pv2, dv_up, is_soft(player), False, tc_bucket(tc))
            next_a = self.best_action(key2, ["H","S"]) if key2 in self.q else "H"
            if next_a != "H": break

        dv_final = self._dealer_play(dealer[:], sim_shoe, rc)
        reward = self._reward(hand_value(player), dv_final)
        self._update_q(key, action, reward, None)
        return reward

    def _resolve_single(self, hand, dealer, sim_shoe, rc, dv_up, tc):
        pv = hand_value(hand)
        while pv < 17:
            c = self._deal(sim_shoe, rc)
            if not c: break
            hand.append(c); pv = hand_value(hand)
        dv = self._dealer_play(dealer, sim_shoe, rc)
        return self._reward(pv, dv)

    def _update_q(self, key, action, reward, next_key):
        old     = self.get_q(key, action)
        next_max= max(self.q[next_key].values()) if next_key and next_key in self.q else 0.0
        new_val = old + ALPHA * (reward + GAMMA * next_max - old)
        self.set_q(key, action, new_val)


# Instancia global (singleton)
ai_engine = QLearningEngine()
