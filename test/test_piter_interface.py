import unittest

from src.PiterInterface import (
    PiterInterface,
    SymbolError,
    ProbabilityValueError,
    InconsistentSystemError,
    UnderdeterminedSystemError,
    InvalidSolutionError,
    ImpossibleConditionError,
)


class TestPiterInterfaceBasic(unittest.TestCase):
    """Tests for PiterInterface solving and querying."""

    def test_basic_solve_without_preset_symbols(self):
        """Symbols should be auto-discovered from expressions."""
        pi = PiterInterface()
        pi.add_constraint("~(~d & m)")
        pi.add_probability("m", "True", 0.0001)
        pi.add_probability("d", "True", 0.001)
        total = pi.solve()
        self.assertAlmostEqual(total, 1.0, places=6)

    def test_basic_query(self):
        pi = PiterInterface()
        pi.add_constraint("~(~d & m)")
        pi.add_probability("m", "True", 0.0001)
        pi.add_probability("d", "True", 0.001)
        pi.solve()
        result = pi.query("m", "d")
        self.assertAlmostEqual(result, 0.1, places=6)

    def test_set_symbols_optional(self):
        """Pre-registering symbols should still work but not be required."""
        pi = PiterInterface()
        pi.set_symbols(["m", "d"])
        pi.add_constraint("~(~d & m)")
        pi.add_probability("m", "True", 0.0001)
        pi.add_probability("d", "True", 0.001)
        total = pi.solve()
        self.assertAlmostEqual(total, 1.0, places=6)


class TestPiterInterfaceValidation(unittest.TestCase):
    """Tests for input validation."""

    def test_probability_value_out_of_range_high(self):
        pi = PiterInterface()
        with self.assertRaises(ProbabilityValueError) as ctx:
            pi.add_probability("d", "True", 1.5)
        self.assertIn("1.5", str(ctx.exception))

    def test_probability_value_out_of_range_low(self):
        pi = PiterInterface()
        with self.assertRaises(ProbabilityValueError) as ctx:
            pi.add_probability("d", "True", -0.1)
        self.assertIn("-0.1", str(ctx.exception))

    def test_probability_value_exactly_zero(self):
        pi = PiterInterface()
        pi.add_probability("d", "True", 0.0)
        # Should not raise

    def test_probability_value_exactly_one(self):
        pi = PiterInterface()
        pi.add_probability("d", "True", 1.0)
        # Should not raise


class TestPiterInterfaceSystemErrors(unittest.TestCase):
    """Tests for contradictory, underdetermined, and overdetermined systems."""

    def test_contradictory_system(self):
        pi = PiterInterface()
        pi.add_probability("d", "True", 0.1)
        pi.add_probability("d", "True", 0.2)
        with self.assertRaises(InconsistentSystemError) as ctx:
            pi.solve()
        self.assertIn("contradictory", str(ctx.exception).lower())

    def test_overdetermined_consistent_system(self):
        """P(d)=0.5 and P(~d)=0.5 is overdetermined but consistent."""
        pi = PiterInterface()
        pi.add_probability("d", "True", 0.5)
        pi.add_probability("~d", "True", 0.5)
        total = pi.solve()
        self.assertAlmostEqual(total, 1.0, places=6)
        result = pi.query("d", "True")
        self.assertAlmostEqual(result, 0.5, places=6)

    def test_underdetermined_system_uses_optimizer(self):
        """Single equation with one symbol is underdetermined; optimizer should find a valid solution."""
        pi = PiterInterface()
        pi.add_probability("a", "True", 0.3)
        total = pi.solve()
        self.assertAlmostEqual(total, 1.0, places=6)


class TestPiterInterfaceQueryErrors(unittest.TestCase):
    """Tests for invalid queries."""

    def test_query_unknown_symbol_raises_symbol_error(self):
        """Querying a symbol not present in the finalized system should be rejected."""
        pi = PiterInterface()
        pi.add_probability("d", "True", 0.5)
        pi.add_probability("~d", "True", 0.5)
        pi.solve()
        with self.assertRaises(SymbolError) as ctx:
            pi.query("m", "d & ~d")
        self.assertIn("m", str(ctx.exception))

    def test_query_impossible_condition(self):
        """Querying a condition with zero probability should raise."""
        pi = PiterInterface()
        pi.add_probability("d", "True", 0.5)
        pi.add_probability("~d", "True", 0.5)
        pi.solve()
        with self.assertRaises(ImpossibleConditionError) as ctx:
            pi.query("d", "d & ~d")
        self.assertIn("zero probability", str(ctx.exception).lower())


class TestPiterInterfaceReset(unittest.TestCase):
    """Tests for reset and multi-block reuse."""

    def test_reset_clears_state(self):
        pi = PiterInterface()
        pi.add_constraint("~(~d & m)")
        pi.add_probability("m", "True", 0.0001)
        pi.add_probability("d", "True", 0.001)
        pi.solve()

        pi.reset()
        self.assertFalse(pi.is_solved)
        self.assertIsNone(pi.solution_vector)
        self.assertIsNone(pi.piter)

    def test_reuse_after_reset(self):
        pi = PiterInterface()
        pi.add_constraint("~(~d & m)")
        pi.add_probability("m", "True", 0.0001)
        pi.add_probability("d", "True", 0.001)
        pi.solve()

        pi.reset()
        pi.set_symbols(["a", "b"])
        pi.add_probability("a", "True", 0.3)
        pi.add_probability("b", "True", 0.4)
        pi.add_probability("a", "b", 0.5)
        total = pi.solve()
        self.assertAlmostEqual(total, 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
