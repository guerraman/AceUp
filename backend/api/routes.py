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

# Almacen en memoria
sessions: dict[str, dict] = {}


class CardAction(BaseModel):
    rank: str
    target: str
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


@router.post("/session/new")
def new_session():
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
        raise HTTPException(404, "Sesion no encontrada")
    return {
        "session_id": session_id,
        "hands_played": s["hands_played"],
        "shoe": s["shoe"].to_dict(),
    }


@router.post("/card/add")
def add_card(action: CardAction):
    s = sessions.get(action.session_id)
    if not s:
        raise HTTPException(404, "Sesion no encontrada")

    shoe: Shoe = s["shoe"]
    if shoe.cards.get(action.rank, 0) <= 0:
        raise HTTPException(400, f"No quedan cartas del rango {action.rank}")

    shoe.use_card(action.rank)

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
    s = sessions.get(action.session_id)
    if not s:
        raise HTTPException(404, "Sesion no encontrada")
    s["shoe"].undo_card(action.rank)
    return {"shoe": s["shoe"].to_dict()}


@router.post("/strategy")
def get_strategy(req: StrategyRequest):
    s = sessions.get(req.session_id)
    if not s:
        raise HTTPException(404, "Sesion no encontrada")

    shoe: Shoe = s["shoe"]
    tc = shoe.true_count
    dv = dealer_up_value(req.dealer_card)
    pv = hand_value(req.player_cards)
    soft = is_soft(req.player_cards)
    pair = is_pair(req.player_cards)

    basic_action, basic_reason = get_basic_strategy(req.player_cards, req.dealer_card)

    final_action, deviation_reason = apply_deviations(
        basic_action, req.player_cards, req.dealer_card,
        tc, pv, dv, soft, pair
    )

    bet = get_bet_recommendation(tc, req.bankroll, req.min_bet)

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


@router.post("/hand/next")
def next_hand(session_id: str):
    s = sessions.get(session_id)
    if not s:
        raise HTTPException(404, "Sesion no encontrada")
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
    s = sessions.get(session_id)
    if not s:
        raise HTTPException(404, "Sesion no encontrada")
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
