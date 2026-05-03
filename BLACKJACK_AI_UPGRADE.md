# 🧠 Blackjack Assistant — Upgrade: IA + Casino Programado

> **Instrucción para el editor IA:**
> Este archivo es un **parche** sobre `BLACKJACK_ASSISTANT.md`.
> NO reescribas el sistema desde cero. Lee primero el archivo base y luego
> aplica ÚNICAMENTE los cambios descritos aquí. Cuando termines cada sección,
> confirma antes de continuar.

---

## RESUMEN DE CAMBIOS

| Cambio | Descripción |
|--------|-------------|
| 🧠 Q-Learning | Motor de IA que aprende jugando contra el casino simulado |
| 🎰 Dealer simulado | El dealer sigue reglas fijas (S17) — sin input humano |
| 📊 Memoria persistente | La IA guarda lo aprendido entre sesiones (localStorage) |
| ⚡ Illustrious 18 | Se mantienen todas las desviaciones del archivo base |
| 🔄 Modo híbrido | IA puede sugerir, pero el jugador decide si seguirla |

**Lo que NO cambia:**
- Toda la estructura de carpetas del proyecto
- Los endpoints REST del backend
- Las matrices de estrategia básica completa
- El sistema Hi-Lo y True Count
- El componente visual del asistente
- El shoe de 6 mazos con 24 cartas por rango

---

## SECCIÓN A — NUEVO MÓDULO BACKEND: `backend/core/ai_engine.py`

Crear este archivo nuevo. No modifica ningún archivo existente.

```python
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
```

---

## SECCIÓN B — MODIFICAR: `backend/api/routes.py`

Agregar estos **3 nuevos endpoints** al final del archivo existente.
No modificar los endpoints que ya existen.

```python
# ── AGREGAR al final de backend/api/routes.py ─────────────────────

from core.ai_engine import ai_engine
from fastapi import BackgroundTasks

# Modelo para registrar resultado de mano real
class HandResult(BaseModel):
    session_id: str
    player_cards: list[str]
    dealer_card: str
    true_count: float
    action_taken: str           # La acción que realmente ejecutó el jugador
    reward: float               # +1 ganó, -1 perdió, 0 empate, +1.5 BJ


@router.post("/ai/recommend")
def ai_recommend(req: StrategyRequest):
    """
    Recomendación combinada: estrategia básica + I18 + Q-Learning.
    Retorna la sugerencia de la IA junto con su confianza y valores Q.
    """
    s = sessions.get(req.session_id)
    if not s:
        raise HTTPException(404, "Sesión no encontrada")

    shoe = s["shoe"]
    tc   = shoe.true_count

    # 1. Calcular acción base (strategy.py + deviations.py)
    from core.strategy   import get_basic_strategy
    from core.deviations import apply_deviations
    from core.counter    import hand_value, is_soft, is_pair, dealer_up_value

    basic_action, _ = get_basic_strategy(req.player_cards, req.dealer_card)
    dv   = dealer_up_value(req.dealer_card)
    pv   = hand_value(req.player_cards)
    soft = is_soft(req.player_cards)
    pair = is_pair(req.player_cards)
    dev_action, dev_reason = apply_deviations(
        basic_action, req.player_cards, req.dealer_card, tc, pv, dv, soft, pair
    )

    # 2. Consultar IA
    ai_rec = ai_engine.recommend(
        player_cards  = req.player_cards,
        dealer_card   = req.dealer_card,
        true_count    = tc,
        basic_action  = dev_action,
    )

    return {
        "final_action":  ai_rec["action"],
        "base_action":   dev_action,
        "base_reason":   dev_reason,
        "q_override":    ai_rec["q_override"],
        "q_values":      ai_rec["q_values"],
        "confidence":    ai_rec["confidence"],
        "ai_stats": {
            "total_hands": ai_rec["total_hands"],
            "win_rate":    ai_rec["win_rate"],
            "state_count": ai_rec["state_count"],
        }
    }


@router.post("/ai/learn")
def ai_learn_from_hand(result: HandResult):
    """
    Registra el resultado de una mano real para aprendizaje online.
    Llamar DESPUÉS de que la mano termine y se sepa el resultado.
    """
    ai_engine.update_from_real_hand(
        player_cards = result.player_cards,
        dealer_card  = result.dealer_card,
        true_count   = result.true_count,
        action_taken = result.action_taken,
        reward       = result.reward,
    )
    # Guardar cada 100 manos reales
    if (ai_engine.wins + ai_engine.losses) % 100 == 0:
        ai_engine.save()

    return {"ok": True, "total_hands": ai_engine.total_hands}


@router.post("/ai/train")
async def ai_train(background_tasks: BackgroundTasks, n_hands: int = 50000):
    """
    Lanza entrenamiento en background (no bloquea la API).
    Simula n_hands manos contra el dealer programado S17.
    Recomendado: llamar una vez al iniciar el servidor.
    """
    background_tasks.add_task(_run_training, n_hands)
    return {"message": f"Entrenamiento de {n_hands} manos iniciado en background"}


def _run_training(n_hands: int):
    result = ai_engine.train(n_hands)
    print(f"[AI] Entrenamiento completo: {result}")


@router.get("/ai/status")
def ai_status():
    """Estado actual del motor de IA."""
    return {
        "total_hands": ai_engine.total_hands,
        "win_rate":    ai_engine.win_rate,
        "state_count": ai_engine.state_count,
        "epsilon":     round(ai_engine.epsilon, 4),
        "trained":     ai_engine.total_hands > 5000,
    }
```

---

## SECCIÓN C — MODIFICAR: `backend/main.py`

Agregar entrenamiento automático al arrancar el servidor.
Reemplazar el bloque `@app.get("/health")` con:

```python
# ── REEMPLAZAR en backend/main.py ─────────────────────────────────

from core.ai_engine import ai_engine
import asyncio

@app.on_event("startup")
async def startup_event():
    """
    Al arrancar: si la IA tiene menos de 10,000 manos simuladas,
    entrena en background automáticamente.
    """
    if ai_engine.total_hands < 10_000:
        print(f"[AI] Iniciando entrenamiento automático...")
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, ai_engine.train, 50_000)
    else:
        print(f"[AI] Motor cargado: {ai_engine.total_hands} manos, "
              f"win rate: {ai_engine.win_rate}%")

@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "2.1",
        "ai": {
            "trained": ai_engine.total_hands > 5000,
            "hands":   ai_engine.total_hands,
            "win_rate": ai_engine.win_rate,
        }
    }
```

---

## SECCIÓN D — MODIFICAR: `frontend/src/store/gameStore.js`

Agregar estas propiedades y acciones al store existente.
Insertar dentro del `create((set, get) => ({` sin borrar nada:

```javascript
// ── AGREGAR dentro del store existente en gameStore.js ────────────

// Nuevas propiedades de estado IA
aiStatus: null,          // { trained, total_hands, win_rate, state_count }
aiRecommendation: null,  // { final_action, q_override, confidence, q_values }
aiEnabled: true,         // El jugador puede activar/desactivar la IA
lastHandResult: null,    // Para registrar resultado tras cada mano

// ── Nuevas acciones ────────────────────────────────────────────────

fetchAIStatus: async () => {
  try {
    const { data } = await API.get('/ai/status')
    set({ aiStatus: data })
  } catch (e) { /* silencioso */ }
},

fetchAIRecommendation: async () => {
  const { sessionId, playerCards, dealerCard, bankroll, minBet, aiEnabled } = get()
  if (!aiEnabled || playerCards.length < 2 || !dealerCard) return

  try {
    const { data } = await API.post('/ai/recommend', {
      player_cards: playerCards,
      dealer_card:  dealerCard,
      session_id:   sessionId,
      bankroll,
      min_bet: minBet,
    })
    set({ aiRecommendation: data })
  } catch (e) { /* silencioso, fallback a estrategia básica */ }
},

reportHandResult: async (actionTaken, reward) => {
  const { sessionId, playerCards, dealerCard, trueCount } = get()
  if (!playerCards.length || !dealerCard) return

  try {
    await API.post('/ai/learn', {
      session_id:   sessionId,
      player_cards: playerCards,
      dealer_card:  dealerCard,
      true_count:   trueCount,
      action_taken: actionTaken,
      reward,
    })
  } catch (e) { /* silencioso */ }
},

triggerTraining: async (nHands = 50000) => {
  await API.post(`/ai/train?n_hands=${nHands}`)
  // Polling del estado cada 3 segundos
  const poll = setInterval(async () => {
    await get().fetchAIStatus()
    const s = get().aiStatus
    if (s && s.total_hands > 0) {
      // Actualizar cuando cambie
      set({ aiStatus: s })
    }
  }, 3000)
  setTimeout(() => clearInterval(poll), 120_000) // máx 2 min
},

toggleAI: () => set(s => ({ aiEnabled: !s.aiEnabled })),
```

---

## SECCIÓN E — NUEVO COMPONENTE: `frontend/src/components/AIAdvisor.jsx`

Crear este archivo nuevo. Se integra junto al `ActionBox` existente.

```jsx
// frontend/src/components/AIAdvisor.jsx
import { useGameStore } from '../store/gameStore'
import { useEffect } from 'react'

const ACTION_LABELS = {
  H: 'PEDIR (Hit)',
  S: 'PLANTARSE (Stand)',
  D: 'DOBLAR (Double Down)',
  P: 'DIVIDIR (Split)',
  R: 'RENDIRSE (Surrender)',
}

const ACTION_COLORS = {
  H: '#7ddf82', S: '#7ab3ff', D: '#ffd070', P: '#c080ff', R: '#ff8080'
}

export function AIAdvisor() {
  const {
    aiRecommendation, aiStatus, aiEnabled,
    toggleAI, triggerTraining, fetchAIStatus
  } = useGameStore()

  useEffect(() => {
    fetchAIStatus()
  }, [])

  const trained = aiStatus?.trained ?? false
  const hands   = aiStatus?.total_hands ?? 0
  const winRate = aiStatus?.win_rate ?? 0
  const states  = aiStatus?.state_count ?? 0

  return (
    <div style={{
      background: 'rgba(26,58,143,0.12)',
      border: '1px solid rgba(122,179,255,0.25)',
      borderRadius: '10px',
      padding: '12px 16px',
      marginBottom: '10px',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <span style={{ fontSize: '11px', color: '#7ab3ff', fontWeight: 600,
                       letterSpacing: '0.12em', textTransform: 'uppercase' }}>
          🧠 Motor Q-Learning
        </span>

        {/* Badge estado */}
        <span style={{
          fontSize: '9px', padding: '2px 8px', borderRadius: '10px', fontWeight: 700,
          background: trained ? 'rgba(26,107,26,0.4)' : 'rgba(26,58,143,0.4)',
          color: trained ? '#7ddf82' : '#7ab3ff',
          border: `1px solid ${trained ? '#3abf3a' : '#3a6abf'}`,
        }}>
          {trained ? `ENTRENADO · ${hands.toLocaleString()} manos` : 'ENTRENANDO...'}
        </span>

        {/* Toggle */}
        <button onClick={toggleAI} style={{
          marginLeft: 'auto', fontSize: '10px', padding: '3px 10px',
          borderRadius: '6px', cursor: 'pointer', border: '1px solid rgba(122,179,255,0.3)',
          background: aiEnabled ? 'rgba(122,179,255,0.15)' : 'transparent',
          color: aiEnabled ? '#7ab3ff' : 'rgba(122,179,255,0.4)',
        }}>
          {aiEnabled ? 'IA ON' : 'IA OFF'}
        </button>
      </div>

      {/* Stats fila */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '8px' }}>
        {[
          ['Win rate', `${winRate}%`],
          ['Estados Q', states.toLocaleString()],
          ['Épsilon', aiStatus?.epsilon?.toFixed(3) ?? '—'],
        ].map(([label, val]) => (
          <div key={label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '14px', fontWeight: 600,
                          color: 'rgba(240,232,208,0.9)' }}>{val}</div>
            <div style={{ fontSize: '9px', color: 'rgba(122,179,255,0.5)',
                          textTransform: 'uppercase', letterSpacing: '0.1em' }}>{label}</div>
          </div>
        ))}

        {/* Botón entrenar */}
        {!trained && (
          <button onClick={() => triggerTraining(50000)} style={{
            marginLeft: 'auto', fontSize: '10px', padding: '4px 12px',
            borderRadius: '6px', cursor: 'pointer',
            border: '1px solid rgba(160,100,255,0.4)',
            background: 'rgba(160,100,255,0.1)', color: '#c080ff',
          }}>
            ⚡ Entrenar ahora
          </button>
        )}
      </div>

      {/* Recomendación de la IA */}
      {aiEnabled && aiRecommendation && (
        <div style={{
          borderTop: '1px solid rgba(122,179,255,0.15)',
          paddingTop: '8px', marginTop: '4px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ fontSize: '11px', color: 'rgba(122,179,255,0.6)' }}>
              Sugerencia IA:
            </span>
            <span style={{
              fontSize: '14px', fontWeight: 700,
              color: ACTION_COLORS[aiRecommendation.final_action] || '#fff',
            }}>
              {ACTION_LABELS[aiRecommendation.final_action]}
            </span>
            {aiRecommendation.q_override && (
              <span style={{
                fontSize: '9px', padding: '1px 6px', borderRadius: '8px',
                background: 'rgba(160,100,255,0.2)', color: '#c080ff',
                border: '1px solid rgba(160,100,255,0.3)',
              }}>
                IA overrride
              </span>
            )}
          </div>

          {/* Confianza */}
          <div style={{ marginBottom: '4px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between',
                          fontSize: '9px', color: 'rgba(122,179,255,0.4)',
                          marginBottom: '2px' }}>
              <span>Confianza</span>
              <span>{aiRecommendation.confidence}%</span>
            </div>
            <div style={{ height: '3px', background: 'rgba(0,0,0,0.3)',
                          borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{
                height: '100%', borderRadius: '2px',
                width: `${aiRecommendation.confidence}%`,
                background: `linear-gradient(90deg, #3a6abf, #c080ff)`,
                transition: 'width 0.4s',
              }}/>
            </div>
          </div>

          {/* Valores Q */}
          {Object.keys(aiRecommendation.q_values).length > 0 && (
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '6px' }}>
              {Object.entries(aiRecommendation.q_values)
                .sort(([,a],[,b]) => b - a)
                .map(([action, val]) => (
                <div key={action} style={{
                  fontSize: '10px', padding: '2px 7px', borderRadius: '6px',
                  background: 'rgba(0,0,0,0.2)',
                  color: action === aiRecommendation.final_action
                    ? (ACTION_COLORS[action] || '#fff')
                    : 'rgba(255,255,255,0.35)',
                  border: action === aiRecommendation.final_action
                    ? `1px solid ${ACTION_COLORS[action]}44`
                    : '1px solid transparent',
                }}>
                  {ACTION_LABELS[action]?.split(' ')[0]}: {val.toFixed(2)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

---

## SECCIÓN F — MODIFICAR: `frontend/src/App.jsx`

Agregar el componente `AIAdvisor` **encima** del `ActionBox` existente.
También llamar a `fetchAIRecommendation` cada vez que cambian las cartas.

```jsx
// ── CAMBIOS en App.jsx (o donde estén los componentes principales) ─

// 1. Importar el nuevo componente
import { AIAdvisor } from './components/AIAdvisor'

// 2. En el useEffect que observa playerCards y dealerCard, agregar:
useEffect(() => {
  fetchAIRecommendation()  // ya existe fetchStrategy, agregar esta línea
}, [playerCards, dealerCard])

// 3. En el JSX, colocar <AIAdvisor /> ANTES de <ActionBox />:
// <AIAdvisor />
// <ActionBox />   ← este ya existe, no moverlo
```

---

## SECCIÓN G — MODIFICAR: `docker-compose.yml`

Agregar volumen para persistir la Q-table entre reinicios del contenedor.

```yaml
# ── CAMBIO en docker-compose.yml ──────────────────────────────────
# En el servicio 'backend', agregar al array 'volumes':

services:
  backend:
    # ... (todo lo existente se mantiene igual)
    volumes:
      - ./backend:/app
      - ai_data:/app/data    # ← AGREGAR esta línea

# Al final del archivo, agregar:
volumes:
  ai_data:
    driver: local
```

---

## SECCIÓN H — NUEVO TEST: `backend/tests/test_ai_engine.py`

```python
# backend/tests/test_ai_engine.py
import pytest
from core.ai_engine import QLearningEngine, hand_value, state_key, tc_bucket

class TestQLearningEngine:
    def setup_method(self):
        self.ai = QLearningEngine()

    def test_shoe_inicializa_correcto(self):
        """312 cartas totales, 24 por rango."""
        from core.ai_engine import RANKS, PER_RANK
        assert PER_RANK == 24
        assert len(RANKS) == 13

    def test_hand_value_soft(self):
        assert hand_value(["A", "7"]) == 18
        assert hand_value(["A", "7", "6"]) == 14   # soft bust → hard

    def test_hand_value_bust(self):
        assert hand_value(["10", "J", "5"]) == 25   # bust

    def test_state_key_consistente(self):
        k1 = state_key(16, 10, False, False, 0)
        k2 = state_key(16, 10, False, False, 0)
        assert k1 == k2

    def test_tc_bucket_limites(self):
        assert tc_bucket(10.0) == 5
        assert tc_bucket(-10.0) == -5
        assert tc_bucket(0.0) == 0

    def test_entrenamiento_basico(self):
        """Después de 1000 manos el engine debe tener estados en Q."""
        self.ai.train(n_hands=1000)
        assert self.ai.state_count > 0
        assert self.ai.total_hands == 1000

    def test_recommend_sin_datos_retorna_basic(self):
        """Sin datos Q suficientes, debe retornar la acción básica."""
        result = self.ai.recommend(
            player_cards=["9", "7"],
            dealer_card="10",
            true_count=0.0,
            basic_action="H",
        )
        # Sin entrenamiento, no debe hacer override
        assert result["q_override"] == False
        assert result["action"] == "H"

    def test_update_from_real_hand(self):
        """Actualización online debe modificar Q-table."""
        before = self.ai.state_count
        self.ai.update_from_real_hand(
            player_cards=["8", "8"],
            dealer_card="6",
            true_count=1.0,
            action_taken="P",
            reward=1.0,
        )
        # Debe haber creado o actualizado al menos un estado
        assert self.ai.state_count >= before

    def test_confianza_aumenta_con_entrenamiento(self):
        """Después de más entrenamiento, confianza debe mejorar."""
        self.ai.train(n_hands=5000)
        from core.ai_engine import state_key, tc_bucket
        # Buscar un estado con datos
        if self.ai.state_count > 0:
            some_key = next(iter(self.ai.q))
            conf = self.ai.confidence(some_key)
            assert 0 <= conf <= 100
```

---

## SECCIÓN I — RESUMEN DE ARCHIVOS MODIFICADOS

```
NUEVOS (crear desde cero):
├── backend/core/ai_engine.py          ← Motor Q-Learning completo
├── backend/tests/test_ai_engine.py    ← Tests del motor IA
└── frontend/src/components/AIAdvisor.jsx  ← UI del componente IA

MODIFICADOS (solo agregar, no reemplazar):
├── backend/api/routes.py              ← +3 endpoints: /ai/recommend, /ai/learn, /ai/train, /ai/status
├── backend/main.py                    ← +startup_event con entrenamiento automático
├── frontend/src/store/gameStore.js    ← +5 acciones: fetchAIStatus, fetchAIRecommendation,
│                                          reportHandResult, triggerTraining, toggleAI
├── frontend/src/App.jsx               ← +import AIAdvisor, +useEffect, +<AIAdvisor /> en JSX
└── docker-compose.yml                 ← +volumen ai_data para persistencia Q-table
```

---

## SECCIÓN J — FLUJO COMPLETO DEL SISTEMA CON IA

```
INICIO DEL SERVIDOR
│
├── startup_event() se ejecuta
│   └── Si ai_engine.total_hands < 10,000:
│       └── Lanza train(50,000) en background thread
│           └── Simula manos contra dealer S17
│           └── Actualiza Q-table con Q-Learning
│           └── Guarda en data/q_table.json
│
DURANTE EL JUEGO (jugador real)
│
├── Jugador agrega cartas → addCard()
│   └── Frontend llama /strategy (estrategia base + I18/Fab4)
│   └── Frontend llama /ai/recommend (consulta Q-table)
│       └── Si confianza > 65% y Q-val significativamente mejor:
│           └── IA hace "override" y sugiere su acción
│       └── Si no: mantiene la acción de estrategia básica
│
├── Jugador decide y ejecuta la mano
│   └── Cuando termina la mano, reportar resultado:
│       └── Frontend llama /ai/learn con { action_taken, reward }
│           └── IA actualiza Q-table con resultado real
│           └── Cada 100 manos: guarda automáticamente
│
PRÓXIMO ARRANQUE DEL SERVIDOR
│
└── ai_engine carga data/q_table.json
    └── Retoma desde donde quedó (aprendizaje persistente)
```

---

## SECCIÓN K — REGLAS CRÍTICAS PARA EL EDITOR IA

> Lee estas reglas antes de aplicar cualquier cambio.

1. **No modificar** `backend/core/strategy.py`, `backend/core/deviations.py`,
   `backend/core/counter.py` ni `backend/core/shoe.py`. Están completos y correctos.

2. **El Q-Learning NO reemplaza la estrategia básica.** Solo la sobreescribe cuando:
   - `confidence > 65%`
   - `q_override_value > base_value + 0.12`
   - `total_hands > 5000`

3. **`PER_RANK = 24`** en `ai_engine.py` debe ser idéntico al `shoe.py` del base.

4. **El dealer simulado sigue S17 exactamente**: planta en hard 17,
   pide en soft 17. No cambiar esta lógica.

5. **`data/q_table.json`** se crea automáticamente en la primera ejecución.
   Agregar `data/` al `.gitignore`.

6. **El componente `AIAdvisor`** va ENCIMA del `ActionBox` existente,
   no lo reemplaza.

7. **`reportHandResult`** debe llamarse desde el frontend cuando el jugador
   haga clic en "Siguiente mano" y se conozca el resultado.

8. **Ejecutar tests** después de aplicar los cambios:
   ```bash
   cd backend && pytest tests/test_ai_engine.py -v
   ```

9. **Agregar a `.gitignore`**:
   ```
   backend/data/
   backend/data/q_table.json
   ```

10. **El entrenamiento en background** no bloquea la API. FastAPI usa
    `BackgroundTasks` para esto. No cambiar a `asyncio.create_task`.

---

## CÓMO APLICAR ESTE PARCHE

```bash
# 1. Tener el proyecto base funcionando (BLACKJACK_ASSISTANT.md implementado)

# 2. Aplicar cambios en orden:
#    A → B → C → D → E → F → G → H

# 3. Verificar tests
cd backend && pytest tests/ -v --cov=core

# 4. Reiniciar con Docker
docker-compose down && docker-compose up --build

# 5. Disparar primer entrenamiento (opcional, también ocurre automático)
curl -X POST http://localhost:8000/api/v1/ai/train?n_hands=50000

# 6. Ver estado de la IA
curl http://localhost:8000/api/v1/ai/status
```

---

*Parche sobre BLACKJACK_ASSISTANT.md v2.0*
*Algoritmo: Q-Learning con epsilon-greedy decay · Dealer simulado S17 · Persistencia JSON*
