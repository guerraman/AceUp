# 🃏 Blackjack Assistant — Especificaciones para Implementación

> **Instrucción para el editor IA:** Lee este archivo completo antes de escribir cualquier código.
> Implementa el sistema exactamente como se describe. Cuando termines una sección, confirma
> antes de continuar con la siguiente.

---

## RESUMEN DEL PROYECTO

Construir una aplicación web full-stack que asiste a un jugador de Blackjack en tiempo real.
El sistema debe:

1. Registrar cada carta jugada y descontarla del mazo (6 barajas = 312 cartas)
2. Calcular el conteo Hi-Lo (Running Count y True Count) en tiempo real
3. Recomendar la acción óptima (Hit/Stand/Double/Split/Surrender) usando estrategia básica completa
4. Aplicar desviaciones Illustrious 18 + Fab 4 basadas en el True Count
5. Recomendar el tamaño de apuesta usando Kelly Criterion parcial
6. Manejar manos divididas (Split) con recomendación independiente por mano
7. Dar consejo de seguro (Insurance) basado en probabilidades reales del mazo restante
8. Persistir el estado del mazo entre manos dentro de una sesión
9. Permitir "Siguiente mano" (conserva conteo) y "Finalizar juego" (resetea todo)

---

## STACK TECNOLÓGICO

```
backend/   → Python 3.11 + FastAPI + SQLite
frontend/  → React 18 + Vite + Zustand + Tailwind CSS
deploy/    → Docker + docker-compose + Nginx
```

**Instalar dependencias backend:**
```bash
pip install fastapi uvicorn websockets sqlalchemy pydantic python-dotenv pytest pytest-cov
```

**Instalar dependencias frontend:**
```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install zustand axios
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

---

## ESTRUCTURA DE CARPETAS

Crear exactamente esta estructura:

```
blackjack-assistant/
├── backend/
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── shoe.py           ← Gestión del mazo
│   │   ├── counter.py        ← Valores Hi-Lo y cálculos
│   │   ├── strategy.py       ← Matrices de estrategia básica
│   │   ├── deviations.py     ← Illustrious 18 + Fab 4
│   │   └── bankroll.py       ← Kelly Criterion + Bet Spreading
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py         ← Endpoints REST
│   │   └── websocket.py      ← Canal tiempo real
│   ├── models/
│   │   ├── __init__.py
│   │   ├── session.py
│   │   └── hand.py
│   └── tests/
│       ├── test_strategy.py
│       ├── test_deviations.py
│       └── test_shoe.py
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── api/
│       │   └── client.js
│       ├── store/
│       │   └── gameStore.js
│       └── components/
│           ├── HandDisplay.jsx
│           ├── CardPicker.jsx
│           ├── ActionBox.jsx
│           ├── InsuranceBox.jsx
│           ├── SplitManager.jsx
│           ├── ShoeBar.jsx
│           ├── BetAdvisor.jsx
│           └── CountDisplay.jsx
├── docker-compose.yml
├── docker-compose.prod.yml
└── nginx.conf
```

---

## SECCIÓN 1 — BACKEND: GESTIÓN DEL MAZO

### Archivo: `backend/core/shoe.py`

**Regla crítica:** Cada rango tiene exactamente `4 cartas/mazo × 6 mazos = 24 cartas`.
Los rangos son: A, 2, 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K → 13 rangos × 24 = **312 cartas totales**.

```python
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
```

---

## SECCIÓN 2 — BACKEND: LÓGICA DE CARTAS

### Archivo: `backend/core/counter.py`

```python
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
```

---

## SECCIÓN 3 — BACKEND: MATRICES DE ESTRATEGIA BÁSICA

### Archivo: `backend/core/strategy.py`

**Importante:** Estas matrices son para 6 mazos, dealer planta Soft 17 (S17), DAS permitido,
Surrender tardío disponible. NO modificar sin base matemática.

**Leyenda:** `H`=Hit, `S`=Stand, `D`=Double, `Ds`=Double-o-Stand, `P`=Split, `R`=Surrender

```python
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
```

---

## SECCIÓN 4 — BACKEND: DESVIACIONES ILLUSTRIOUS 18 + FAB 4

### Archivo: `backend/core/deviations.py`

**Las desviaciones se aplican DESPUÉS de la estrategia básica.**
**El seguro representa el 33% de la ganancia total por desviaciones — es la más importante.**

```python
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
    """
    Verifica si alguna desviación aplica y sobreescribe la acción básica.
    Retorna (nueva_accion, descripcion_desviacion) o (basic_action, "").
    """
    tc = true_count

    # ════════════════════════════════════════════════════════════════
    # FAB 4 — Surrender por conteo (verificar PRIMERO)
    # ════════════════════════════════════════════════════════════════

    if player_total == 15 and dealer_val == 10 and tc >= 0:
        return "R", f"[Fab4] 15 vs 10 con TC {tc:.1f} ≥ 0 → Rendirse"

    if player_total == 14 and dealer_val == 10 and tc >= 3:
        return "R", f"[Fab4] 14 vs 10 con TC {tc:.1f} ≥ 3 → Rendirse"

    if player_total == 15 and dealer_val == 9 and tc >= 2:
        return "R", f"[Fab4] 15 vs 9 con TC {tc:.1f} ≥ 2 → Rendirse"

    if player_total == 15 and dealer_val == 11 and tc >= 1:
        return "R", f"[Fab4] 15 vs As con TC {tc:.1f} ≥ 1 → Rendirse"

    # ════════════════════════════════════════════════════════════════
    # ILLUSTRIOUS 18 — por orden de impacto en EV
    # ════════════════════════════════════════════════════════════════

    # 1. Seguro (Insurance) — 33% de ganancia total por desviaciones
    #    Se maneja en get_insurance_advice(), no aquí.

    # 2. 16 vs 10: Stand si TC >= 0
    if player_total == 16 and dealer_val == 10 and not soft and tc >= 0:
        return "S", f"[I18] 16 vs 10 con TC {tc:.1f} ≥ 0 → Plantarse"

    # 3. 15 vs 10: Stand si TC >= 4
    if player_total == 15 and dealer_val == 10 and not soft and tc >= 4:
        return "S", f"[I18] 15 vs 10 con TC {tc:.1f} ≥ 4 → Plantarse"

    # 4. 10,10 vs 6: Split si TC >= 4
    if pair and player_total == 20 and dealer_val == 6 and tc >= 4:
        return "P", f"[I18] 10,10 vs 6 con TC {tc:.1f} ≥ 4 → Dividir"

    # 5. 10,10 vs 5: Split si TC >= 5
    if pair and player_total == 20 and dealer_val == 5 and tc >= 5:
        return "P", f"[I18] 10,10 vs 5 con TC {tc:.1f} ≥ 5 → Dividir"

    # 6. 11 vs A (S17): Double si TC >= 1
    if player_total == 11 and dealer_val == 11 and tc >= 1:
        return "D", f"[I18] 11 vs As con TC {tc:.1f} ≥ 1 → Doblar (regla S17)"

    # 7. 10 vs A: Double si TC >= 4
    if player_total == 10 and dealer_val == 11 and tc >= 4:
        return "D", f"[I18] 10 vs As con TC {tc:.1f} ≥ 4 → Doblar"

    # 8. 10 vs 10: Double si TC >= 4
    if player_total == 10 and dealer_val == 10 and tc >= 4:
        return "D", f"[I18] 10 vs 10 con TC {tc:.1f} ≥ 4 → Doblar"

    # 9. 12 vs 3: Stand si TC >= 2
    if player_total == 12 and dealer_val == 3 and not soft and tc >= 2:
        return "S", f"[I18] 12 vs 3 con TC {tc:.1f} ≥ 2 → Plantarse"

    # 10. 12 vs 2: Stand si TC >= 3
    if player_total == 12 and dealer_val == 2 and not soft and tc >= 3:
        return "S", f"[I18] 12 vs 2 con TC {tc:.1f} ≥ 3 → Plantarse"

    # 11. 13 vs 2: Hit si TC <= -1
    if player_total == 13 and dealer_val == 2 and not soft and tc <= -1:
        return "H", f"[I18] 13 vs 2 con TC {tc:.1f} ≤ -1 → Pedir carta"

    # 12. 9 vs 2: Double si TC >= 1
    if player_total == 9 and dealer_val == 2 and not soft and tc >= 1:
        return "D", f"[I18] 9 vs 2 con TC {tc:.1f} ≥ 1 → Doblar"

    # 13. 9 vs 7: Double si TC >= 3
    if player_total == 9 and dealer_val == 7 and not soft and tc >= 3:
        return "D", f"[I18] 9 vs 7 con TC {tc:.1f} ≥ 3 → Doblar"

    # 14. 16 vs 9: Stand si TC >= 5
    if player_total == 16 and dealer_val == 9 and not soft and tc >= 5:
        return "S", f"[I18] 16 vs 9 con TC {tc:.1f} ≥ 5 → Plantarse"

    # 15. 13 vs 3: Hit si TC <= -2
    if player_total == 13 and dealer_val == 3 and not soft and tc <= -2:
        return "H", f"[I18] 13 vs 3 con TC {tc:.1f} ≤ -2 → Pedir carta"

    return basic_action, ""  # Sin desviación


def get_insurance_advice(player_cards: list[str], prob_ten: float, true_count: float) -> dict:
    """
    Consejo de seguro cuando el dealer muestra As.
    El seguro es rentable matemáticamente solo cuando TC >= 3
    (probabilidad de carta de valor 10 > 33.3%).
    """
    from .counter import hand_value
    pv = hand_value(player_cards)
    is_bj = len(player_cards) == 2 and pv == 21
    pct_ten = round(prob_ten * 100, 1)
    tc_str = f"{true_count:.1f}"

    if is_bj:
        return {
            "verdict": "RECHAZA el seguro",
            "type": "reject",
            "reason": (
                f"Tienes Blackjack. El seguro equivale a 'even money' (cobras 1:1 garantizado). "
                f"Estadísticamente conviene rechazarlo: si el dealer NO tiene BJ cobras 3:2. "
                f"Cartas de valor 10 restantes: {pct_ten}%."
            )
        }

    if true_count >= 3:
        return {
            "verdict": "CONSIDERA el seguro",
            "type": "consider",
            "reason": (
                f"TC = +{tc_str} — mazo cargado de 10s ({pct_ten}% de cartas valen 10, "
                f"necesitas >33.3%). El seguro puede ser matemáticamente rentable ahora."
            )
        }

    return {
        "verdict": "RECHAZA el seguro",
        "type": "reject",
        "reason": (
            f"Solo el {pct_ten}% de las cartas valen 10 (necesitas >33.3%). "
            f"TC = {tc_str}. El seguro favorece al casino en este momento."
        )
    }
```

---

## SECCIÓN 5 — BACKEND: BANKROLL Y APUESTAS

### Archivo: `backend/core/bankroll.py`

```python
# backend/core/bankroll.py

BET_SPREAD = [
    # (tc_min, tc_max, units, note)
    (float('-inf'), -1,   0,  "Wonging Out — abandona la mesa"),
    (-1,             1,   1,  "EV negativo o neutro — apuesta mínima"),
    ( 1,             2,   2,  "Ventaja ~+0.5% — apuesta moderada"),
    ( 2,             3,   4,  "Ventaja ~+1.0% — apuesta media"),
    ( 3,             4,   8,  "Ventaja ~+1.5% — apuesta alta"),
    ( 4,   float('inf'), 12,  "Ventaja máxima — apuesta completa"),
]


def get_units(true_count: float) -> tuple[int, str]:
    """Retorna (unidades, nota) según el True Count."""
    for tc_min, tc_max, units, note in BET_SPREAD:
        if tc_min <= true_count < tc_max:
            return units, note
    return 12, "Ventaja máxima"


def get_bet_recommendation(
    true_count: float,
    bankroll: float,
    min_bet: float = 10.0
) -> dict:
    """
    Calcula la apuesta recomendada usando Kelly Criterion parcial (0.5×).

    Kelly completo: f* = edge / varianza
    Varianza del BJ: ~1.33
    Edge por punto TC sobre 1: ~0.5%

    Usamos 0.5× Kelly para reducir volatilidad.
    """
    units, note = get_units(true_count)

    if units == 0:
        return {
            "units": 0,
            "amount": 0,
            "action": "wong_out",
            "message": note,
            "edge_pct": round((true_count - 1) * 0.5, 2),
        }

    # Ventaja estimada
    edge = max(0, (true_count - 1) * 0.005)

    # Kelly parcial
    kelly_full = edge / 1.33 if edge > 0 else 0
    kelly_half = kelly_full * 0.5
    kelly_amount = kelly_half * bankroll

    # Apuesta basada en bet spread
    spread_amount = units * min_bet

    # Usar el menor de los dos para proteger el bankroll
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
```

---

## SECCIÓN 6 — BACKEND: API PRINCIPAL

### Archivo: `backend/main.py`

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

app = FastAPI(title="Blackjack Assistant API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0"}
```

### Archivo: `backend/api/routes.py`

```python
# backend/api/routes.py
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.shoe import Shoe
from core.counter import hand_value, is_soft, is_pair, dealer_up_value
from core.strategy import get_basic_strategy
from core.deviations import apply_deviations, get_insurance_advice
from core.bankroll import get_bet_recommendation

router = APIRouter()

# Almacén en memoria (en producción usar Redis o DB)
sessions: dict[str, dict] = {}


# ─── Modelos ─────────────────────────────────────────────────────
class CardAction(BaseModel):
    rank: str
    target: str  # "player", "dealer", "split_0", "split_1"
    session_id: str

class UndoCard(BaseModel):
    rank: str
    target: str
    session_id: str

class StrategyRequest(BaseModel):
    player_cards: list[str]
    dealer_card: str
    session_id: str
    bankroll: float = 1000.0
    min_bet: float = 10.0


# ─── Sesiones ────────────────────────────────────────────────────
@router.post("/session/new")
def new_session():
    """Crea nueva sesión con zapato de 6 mazos fresco."""
    sid = str(uuid.uuid4())
    shoe = Shoe()
    sessions[sid] = {
        "shoe": shoe,
        "hands_played": 0,
        "current_player": [],
        "current_dealer": None,
        "split_hands": [[], []],
    }
    return {"session_id": sid, "shoe": shoe.to_dict()}


@router.get("/session/{session_id}")
def get_session_state(session_id: str):
    s = sessions.get(session_id)
    if not s:
        raise HTTPException(404, "Sesión no encontrada")
    return {
        "session_id": session_id,
        "hands_played": s["hands_played"],
        "shoe": s["shoe"].to_dict(),
    }


# ─── Cartas ──────────────────────────────────────────────────────
@router.post("/card/add")
def add_card(action: CardAction):
    """Registra una carta jugada y actualiza el conteo."""
    s = sessions.get(action.session_id)
    if not s:
        raise HTTPException(404, "Sesión no encontrada")

    shoe: Shoe = s["shoe"]
    if shoe.cards.get(action.rank, 0) <= 0:
        raise HTTPException(400, f"No quedan cartas del rango {action.rank}")

    shoe.use_card(action.rank)

    # Actualizar estado interno de la mano
    if action.target == "dealer":
        s["current_dealer"] = action.rank
    elif action.target == "player":
        s["current_player"].append(action.rank)
    elif action.target == "split_0":
        s["split_hands"][0].append(action.rank)
    elif action.target == "split_1":
        s["split_hands"][1].append(action.rank)

    return {"shoe": shoe.to_dict()}


@router.post("/card/undo")
def undo_card(action: UndoCard):
    """Revierte una carta registrada por error."""
    s = sessions.get(action.session_id)
    if not s:
        raise HTTPException(404, "Sesión no encontrada")
    s["shoe"].undo_card(action.rank)
    return {"shoe": s["shoe"].to_dict()}


# ─── Estrategia ──────────────────────────────────────────────────
@router.post("/strategy")
def get_strategy(req: StrategyRequest):
    """
    Calcula la acción óptima para la mano actual.
    Aplica estrategia básica + desviaciones por conteo.
    """
    s = sessions.get(req.session_id)
    if not s:
        raise HTTPException(404, "Sesión no encontrada")

    shoe: Shoe = s["shoe"]
    tc = shoe.true_count
    dv = dealer_up_value(req.dealer_card)
    pv = hand_value(req.player_cards)
    soft = is_soft(req.player_cards)
    pair = is_pair(req.player_cards)

    # 1. Estrategia básica
    basic_action, basic_reason = get_basic_strategy(req.player_cards, req.dealer_card)

    # 2. Desviaciones por conteo
    final_action, deviation_reason = apply_deviations(
        basic_action, req.player_cards, req.dealer_card,
        tc, pv, dv, soft, pair
    )

    # 3. Apuesta recomendada
    bet = get_bet_recommendation(tc, req.bankroll, req.min_bet)

    # 4. Consejo de seguro (solo si el dealer muestra As)
    insurance = None
    if req.dealer_card == "A":
        insurance = get_insurance_advice(req.player_cards, shoe.prob_ten, tc)

    reason = deviation_reason if deviation_reason else basic_reason

    return {
        "action": final_action,
        "label": _label(final_action),
        "color": _color(final_action),
        "reason": reason,
        "deviation_applied": bool(deviation_reason),
        "deviation_detail": deviation_reason,
        "player_total": pv,
        "is_soft": soft,
        "is_pair": pair,
        "true_count": round(tc, 2),
        "running_count": shoe.running_count,
        "bet_advice": bet,
        "insurance": insurance,
        "shoe": shoe.to_dict(),
    }


# ─── Control de mano ─────────────────────────────────────────────
@router.post("/hand/next")
def next_hand(session_id: str):
    """Avanza a la siguiente mano conservando el conteo del zapato."""
    s = sessions.get(session_id)
    if not s:
        raise HTTPException(404, "Sesión no encontrada")
    s["hands_played"] += 1
    s["current_player"] = []
    s["current_dealer"] = None
    s["split_hands"] = [[], []]
    return {
        "hands_played": s["hands_played"],
        "shoe": s["shoe"].to_dict(),
    }


@router.post("/game/finish")
def finish_game(session_id: str):
    """Finaliza el juego y resetea el zapato completamente."""
    s = sessions.get(session_id)
    if not s:
        raise HTTPException(404, "Sesión no encontrada")
    stats = {
        "hands_played": s["hands_played"],
        "cards_dealt": s["shoe"].cards_dealt,
        "final_running_count": s["shoe"].running_count,
    }
    s["shoe"].reset()
    s["hands_played"] = 0
    s["current_player"] = []
    s["current_dealer"] = None
    s["split_hands"] = [[], []]
    return {"message": "Juego finalizado. Nuevo mazo listo.", "stats": stats}


# ─── Helpers ─────────────────────────────────────────────────────
def _label(action: str) -> str:
    return {
        "H": "PEDIR (Hit)", "S": "PLANTARSE (Stand)",
        "D": "DOBLAR (Double Down)", "Ds": "DOBLAR (Double Down)",
        "P": "DIVIDIR (Split)", "R": "RENDIRSE (Surrender)",
    }.get(action, action)

def _color(action: str) -> str:
    return {
        "H": "hit", "S": "stand", "D": "double",
        "Ds": "double", "P": "split", "R": "surrender",
    }.get(action, "idle")
```

---

## SECCIÓN 7 — FRONTEND: STORE ZUSTAND

### Archivo: `frontend/src/store/gameStore.js`

```javascript
// frontend/src/store/gameStore.js
import { create } from 'zustand'
import axios from 'axios'

const API = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1' })

export const useGameStore = create((set, get) => ({
  // ─── Estado ──────────────────────────────────────────────────
  sessionId: null,
  playerCards: [],
  dealerCard: null,
  splitHands: [[], []],
  inSplit: false,
  activeSplitHand: 0,
  target: 'player',         // 'player' | 'dealer' | 'split_0' | 'split_1'
  shoe: {},
  runningCount: 0,
  trueCount: 0,
  handsPlayed: 0,
  recommendation: null,
  betAdvice: null,
  insurance: null,
  isLoading: false,
  bankroll: 1000,
  minBet: 10,

  // ─── Acciones ────────────────────────────────────────────────
  initSession: async () => {
    const { data } = await API.post('/session/new')
    set({
      sessionId: data.session_id,
      shoe: data.shoe.cards,
      runningCount: 0,
      trueCount: 0,
    })
  },

  setTarget: (target) => set({ target }),

  addCard: async (rank) => {
    const { sessionId, target, playerCards, dealerCard, splitHands, inSplit, shoe } = get()

    // Verificar disponibilidad
    if ((shoe[rank] || 0) <= 0) return

    // Actualizar estado local optimistamente
    if (target === 'dealer') {
      set({ dealerCard: rank })
    } else if (target === 'player') {
      set({ playerCards: [...playerCards, rank] })
    } else if (target === 'split_0') {
      const h = [...splitHands]; h[0] = [...h[0], rank]
      set({ splitHands: h })
    } else if (target === 'split_1') {
      const h = [...splitHands]; h[1] = [...h[1], rank]
      set({ splitHands: h })
    }

    // Registrar en backend
    const { data } = await API.post('/card/add', { rank, target, session_id: sessionId })
    const newShoe = data.shoe

    set({
      shoe: newShoe.cards,
      runningCount: newShoe.running_count,
      trueCount: newShoe.true_count,
    })

    // Calcular estrategia automáticamente
    await get().fetchStrategy()
  },

  removeCard: async (rank, target) => {
    const { sessionId } = get()
    await API.post('/card/undo', { rank, target, session_id: sessionId })

    // Actualizar estado local
    const s = get()
    if (target === 'dealer') {
      set({ dealerCard: null })
    } else if (target === 'player') {
      const idx = s.playerCards.lastIndexOf(rank)
      if (idx !== -1) {
        const cards = [...s.playerCards]
        cards.splice(idx, 1)
        set({ playerCards: cards })
      }
    }

    await get().fetchStrategy()
  },

  fetchStrategy: async () => {
    const { sessionId, playerCards, dealerCard, bankroll, minBet } = get()
    if (playerCards.length < 2 || !dealerCard) {
      set({ recommendation: null, betAdvice: null, insurance: null })
      return
    }
    set({ isLoading: true })
    try {
      const { data } = await API.post('/strategy', {
        player_cards: playerCards,
        dealer_card: dealerCard,
        session_id: sessionId,
        bankroll,
        min_bet: minBet,
      })
      set({
        recommendation: data,
        betAdvice: data.bet_advice,
        insurance: data.insurance,
        trueCount: data.true_count,
        runningCount: data.running_count,
        shoe: data.shoe.cards,
      })
    } finally {
      set({ isLoading: false })
    }
  },

  enterSplit: () => {
    const { playerCards } = get()
    if (playerCards.length !== 2) return
    const base = playerCards[0]
    set({
      inSplit: true,
      splitHands: [[base], [base]],
      playerCards: [],
      activeSplitHand: 0,
      target: 'split_0',
    })
  },

  nextHand: async () => {
    const { sessionId } = get()
    const { data } = await API.post(`/hand/next?session_id=${sessionId}`)
    set({
      playerCards: [],
      dealerCard: null,
      splitHands: [[], []],
      inSplit: false,
      activeSplitHand: 0,
      target: 'player',
      recommendation: null,
      betAdvice: null,
      insurance: null,
      handsPlayed: data.hands_played,
      shoe: data.shoe.cards,
      runningCount: data.shoe.running_count,
      trueCount: data.shoe.true_count,
    })
  },

  finishGame: async () => {
    const { sessionId } = get()
    await API.post(`/game/finish?session_id=${sessionId}`)
    await get().initSession()
    set({
      playerCards: [],
      dealerCard: null,
      splitHands: [[], []],
      inSplit: false,
      handsPlayed: 0,
      recommendation: null,
      betAdvice: null,
      insurance: null,
    })
  },

  setBankroll: (amount) => set({ bankroll: amount }),
  setMinBet: (amount) => set({ minBet: amount }),
}))
```

---

## SECCIÓN 8 — FRONTEND: COMPONENTES CLAVE

### ActionBox — colores por acción

```javascript
// frontend/src/components/ActionBox.jsx
import { useGameStore } from '../store/gameStore'

const ACTION_CONFIG = {
  H:  { label: 'PEDIR (Hit)',           bg: '#EAF3DE', border: '#639922', color: '#3B6D11' },
  S:  { label: 'PLANTARSE (Stand)',     bg: '#E6F1FB', border: '#185FA5', color: '#185FA5' },
  D:  { label: 'DOBLAR (Double Down)',  bg: '#FAEEDA', border: '#BA7517', color: '#854F0B' },
  Ds: { label: 'DOBLAR (Double Down)',  bg: '#FAEEDA', border: '#BA7517', color: '#854F0B' },
  P:  { label: 'DIVIDIR (Split)',       bg: '#EEEDFE', border: '#534AB7', color: '#3C3489' },
  R:  { label: 'RENDIRSE (Surrender)', bg: '#FCEBEB', border: '#A32D2D', color: '#A32D2D' },
}

export function ActionBox() {
  const { recommendation, isLoading, enterSplit } = useGameStore()

  if (isLoading) return <div className="p-4 text-center text-gray-400">Calculando...</div>

  if (!recommendation) return (
    <div className="p-4 text-center rounded-xl border border-gray-200 bg-gray-50">
      <p className="text-gray-400">Añade tus cartas para ver la recomendación</p>
    </div>
  )

  const cfg = ACTION_CONFIG[recommendation.action] || ACTION_CONFIG.H

  return (
    <div className="rounded-xl border-2 p-4 text-center transition-all"
         style={{ background: cfg.bg, borderColor: cfg.border }}>
      <h2 className="text-xl font-semibold mb-1" style={{ color: cfg.color }}>
        {cfg.label}
      </h2>
      <p className="text-sm text-gray-600">{recommendation.reason}</p>

      {recommendation.deviation_applied && (
        <span className="inline-block mt-2 px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded">
          ⚡ Desviación I18 aplicada
        </span>
      )}

      {recommendation.action === 'P' && (
        <button onClick={enterSplit}
                className="mt-3 px-4 py-1 text-sm border rounded hover:bg-white transition">
          Simular split →
        </button>
      )}
    </div>
  )
}
```

### BetAdvisor

```javascript
// frontend/src/components/BetAdvisor.jsx
import { useGameStore } from '../store/gameStore'

export function BetAdvisor() {
  const { betAdvice, trueCount } = useGameStore()
  if (!betAdvice) return null

  const isWong = betAdvice.units === 0
  const isFav = trueCount >= 3
  const isUnfav = trueCount <= -3

  return (
    <div className={`rounded-lg border p-3 text-sm ${
      isWong  ? 'bg-red-50 border-red-300' :
      isFav   ? 'bg-green-50 border-green-300' :
      isUnfav ? 'bg-orange-50 border-orange-300' :
               'bg-gray-50 border-gray-200'
    }`}>
      <div className="flex justify-between items-center">
        <span className="font-medium">
          {isWong ? '🚫 Abandona la mesa' : `💰 Apuesta: ${betAdvice.units} unidad${betAdvice.units !== 1 ? 'es' : ''}`}
        </span>
        <span className="text-xs text-gray-500">TC: {trueCount.toFixed(1)}</span>
      </div>
      <p className="text-xs text-gray-500 mt-1">{betAdvice.message}</p>
      {betAdvice.edge_pct > 0 && (
        <p className="text-xs text-green-600 mt-1">Ventaja estimada: +{betAdvice.edge_pct}%</p>
      )}
    </div>
  )
}
```

---

## SECCIÓN 9 — DOCKER

### `docker-compose.yml`

```yaml
version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - PYTHONPATH=/app

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev -- --host
    environment:
      - VITE_API_URL=http://localhost:8000/api/v1
    depends_on:
      - backend
```

### `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `frontend/Dockerfile`

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json .
RUN npm install
COPY . .
CMD ["npm", "run", "dev", "--", "--host"]
```

---

## SECCIÓN 10 — TESTS OBLIGATORIOS

### `backend/tests/test_strategy.py`

```python
# Implementar estos tests. Todos deben pasar antes de hacer deploy.
import pytest
from core.strategy import get_basic_strategy
from core.deviations import apply_deviations, get_insurance_advice

class TestHardHands:
    def test_16_vs_7_hits(self):
        action, _ = get_basic_strategy(["9", "7"], "7")
        assert action == "H"

    def test_13_vs_6_stands(self):
        action, _ = get_basic_strategy(["7", "6"], "6")
        assert action == "S"

    def test_11_always_doubles(self):
        for dealer in ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]:
            action, _ = get_basic_strategy(["6", "5"], dealer)
            assert action == "D", f"11 vs {dealer} debe ser Double"

class TestSoftHands:
    def test_soft_18_vs_9_hits(self):
        action, _ = get_basic_strategy(["A", "7"], "9")
        assert action == "H"

    def test_soft_18_vs_6_doubles(self):
        action, _ = get_basic_strategy(["A", "7"], "6")
        assert action in ("D", "Ds")

    def test_soft_18_vs_7_stands(self):
        action, _ = get_basic_strategy(["A", "7"], "7")
        assert action == "S"

class TestPairs:
    def test_aces_always_split(self):
        action, _ = get_basic_strategy(["A", "A"], "10")
        assert action == "P"

    def test_eights_always_split(self):
        action, _ = get_basic_strategy(["8", "8"], "A")
        assert action == "P"

    def test_tens_never_split(self):
        action, _ = get_basic_strategy(["10", "10"], "6")
        assert action == "S"

    def test_fives_never_split(self):
        action, _ = get_basic_strategy(["5", "5"], "6")
        assert action == "D"  # Tratar como 10 duro

class TestDeviations:
    def test_insurance_at_tc3(self):
        result = get_insurance_advice(["8", "6"], 0.35, 3.0)
        assert result["type"] == "consider"

    def test_no_insurance_below_tc3(self):
        result = get_insurance_advice(["8", "6"], 0.30, 2.0)
        assert result["type"] == "reject"

    def test_16_vs_10_stand_at_tc0(self):
        action, reason = apply_deviations("H", ["9","7"], "10", 0.0, 16, 10, False, False)
        assert action == "S"
        assert "I18" in reason

    def test_fab4_15_vs_10_surrender_at_tc0(self):
        action, reason = apply_deviations("H", ["8","7"], "10", 0.0, 15, 10, False, False)
        assert action == "R"
        assert "Fab4" in reason
```

---

## SECCIÓN 11 — VARIABLES DE ENTORNO

### `backend/.env`

```env
DATABASE_URL=sqlite:///./blackjack.db
DEBUG=true
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### `frontend/.env`

```env
VITE_API_URL=http://localhost:8000/api/v1
```

---

## REGLAS CRÍTICAS PARA EL EDITOR IA

> Lee estas reglas antes de escribir cualquier línea de código.

1. **El mazo siempre tiene 24 cartas por rango** (PER_RANK = 4 × 6 = 24). Si usas otro número el conteo será incorrecto.

2. **Las desviaciones se aplican DESPUÉS de la estrategia básica**, nunca antes. La función `apply_deviations()` recibe la acción básica y la sobreescribe si aplica.

3. **El Fab 4 se verifica ANTES que el Illustrious 18** dentro de `apply_deviations()`.

4. **El seguro se maneja en `get_insurance_advice()`**, separado de las desviaciones de juego.

5. **`Ds` (Double-or-Stand)** solo es válido con exactamente 2 cartas. Con más cartas, convertir a `S`.

6. **El True Count usa `max(0.5, cards_left / 52)`** para evitar divisiones por cero al final del zapato.

7. **El store Zustand actualiza el shoe optimistamente** y luego confirma con el backend.

8. **`finishGame()`** debe resetear el shoe a 312 cartas y crear nueva sesión en el backend.

9. **`nextHand()`** conserva el Running Count y True Count del shoe actual.

10. **Los tests deben pasar al 100%** antes de cualquier deploy. Ejecutar con `pytest tests/ -v`.

---

## CÓMO EMPEZAR

```bash
# 1. Clonar / crear el proyecto
mkdir blackjack-assistant && cd blackjack-assistant

# 2. Levantar con Docker (recomendado)
docker-compose up --build

# 3. O desarrollo local:
# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (nueva terminal)
cd frontend && npm install && npm run dev

# 4. Verificar que funciona
curl http://localhost:8000/health
# → {"status": "ok", "version": "2.0"}

# 5. Correr tests
cd backend && pytest tests/ -v --cov=core
```

---

*Especificaciones generadas a partir del Reporte Técnico de Estrategia Avanzada de Blackjack.*
*Basado en: Estrategia Básica S17, 6 mazos, DAS, sistema Hi-Lo, Illustrious 18 + Fab 4.*
