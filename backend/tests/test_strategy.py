import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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
        assert action == "D"

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
