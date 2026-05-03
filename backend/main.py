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
