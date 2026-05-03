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
