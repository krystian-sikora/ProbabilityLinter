import sympy
import numpy as np
from sympy.parsing.sympy_parser import parse_expr
from piter import Piter

# Tolerance for floating-point validation
_TOLERANCE = 1e-9


class PiterInterfaceError(Exception):
    """Base exception for PiterInterface errors that the linter should surface."""
    pass


class SymbolError(PiterInterfaceError):
    """Raised when a SymPy expression cannot be parsed."""
    pass


class ProbabilityValueError(PiterInterfaceError):
    """Raised when a probability value is outside [0, 1]."""
    pass


class InconsistentSystemError(PiterInterfaceError):
    """Raised when the linear system is contradictory (e.g., P(d)=0.1 and P(d)=0.2)."""
    pass


class UnderdeterminedSystemError(PiterInterfaceError):
    """Raised when the system has fewer equations than unknowns and no unique solution."""
    pass


class InvalidSolutionError(PiterInterfaceError):
    """Raised when the solved vector contains negative probabilities or does not sum to 1."""
    pass


class ImpossibleConditionError(PiterInterfaceError):
    """Raised when querying a conditional probability where the condition has probability 0."""
    pass


class PiterInterface:
    """
    High-level interface for the Markdown Linter to interact with the Piter engine.
    Handles string parsing, symbol management, and solving the linear system.

    Usage:
        pi = PiterInterface()
        pi.set_symbols(['m', 'd'])          # optional; symbols are auto-created too
        pi.add_constraint('m >> d')
        pi.add_probability('m', 'True', 0.0001)
        pi.add_probability('d', 'True', 0.001)
        pi.solve()
        result = pi.query('m', 'd')
    """

    def __init__(self):
        self.symbols_map = {}
        self.piter = None
        self.solution_vector = None
        self.is_solved = False
        self._finalized_symbols = None  # set of symbols known when piter was finalized

    def reset(self):
        """
        Reset the interface for a new probability block.
        Clears symbols, the Piter engine, and any cached solution.
        """
        self.symbols_map = {}
        self.piter = None
        self.solution_vector = None
        self.is_solved = False
        self._finalized_symbols = None

    def set_symbols(self, symbol_names: list[str]):
        """
        Pre-register a list of symbol name strings.
        This is optional — symbols referenced in expressions are created on demand.
        Example: ['m', 'd']
        """
        for name in symbol_names:
            if name not in self.symbols_map:
                self.symbols_map[name] = sympy.symbols(name)

        if self.piter is None:
            self.piter = Piter(set(self.symbols_map.values()))
        else:
            # Merge new symbols into existing Piter instance
            for sym in self.symbols_map.values():
                # Piter auto-discovers symbols via addP/addConstraint, so
                # we just need to make sure the engine exists.
                pass

    def _ensure_piter(self):
        """Lazy-initialize the Piter engine if it doesn't exist yet."""
        if self.piter is None:
            self.piter = Piter(set())

    def _parse_logic(self, expr_str: str):
        """Parse a logical string using the current symbol map.
        Unknown symbols are created on the fly (mirroring Piter's behaviour)."""
        self._ensure_piter()

        try:
            expr = parse_expr(expr_str, local_dict=self.symbols_map)
        except Exception as e:
            raise SymbolError(f"Failed to parse logic expression '{expr_str}': {e}")

        # Auto-register any newly discovered symbols so future calls see them
        for arg in sympy.preorder_traversal(expr):
            if isinstance(arg, sympy.core.symbol.Symbol):
                if str(arg) not in self.symbols_map:
                    self.symbols_map[str(arg)] = arg

        return expr

    def add_constraint(self, constraint_str: str):
        """
        Add a logical constraint string.
        Example: "m >> d"
        """
        expr = self._parse_logic(constraint_str)
        self.piter.addConstraint(expr)

    def add_probability(self, target_str: str, condition_str: str, value: float):
        """
        Add a probability definition.
        P(target | condition) = value
        Pass condition_str=None or "True" for unconditional probability.
        """
        if not (0.0 <= float(value) <= 1.0):
            raise ProbabilityValueError(
                f"Probability value must be in [0, 1], got {value}"
            )

        target = self._parse_logic(target_str)

        if condition_str and condition_str.lower() != "true":
            condition = self._parse_logic(condition_str)
        else:
            condition = sympy.true

        self.piter.addP(target, condition, float(value))

    def solve(self):
        """
        Finalize the Piter engine, build the matrix, and solve the linear system.
        Returns the sum of probabilities (should be close to 1.0).

        Raises:
            InconsistentSystemError: if the equations are contradictory.
            UnderdeterminedSystemError: if there is no unique solution.
            InvalidSolutionError: if the resulting probabilities are negative or don't sum to 1.
        """
        if self.is_solved:
            return float(np.sum(self.solution_vector))

        self.piter.finalize()
        self._finalized_symbols = set(self.symbols_map.values())

        ab = self.piter.getNumpy()
        A = ab[:, :-1]
        b = ab[:, -1]

        rank_a = np.linalg.matrix_rank(A)
        rank_ab = np.linalg.matrix_rank(ab)
        n_unknowns = A.shape[1]

        if rank_a < rank_ab:
            raise InconsistentSystemError(
                "The probability system is contradictory (no solution satisfies all equations)."
            )

        if rank_a == n_unknowns:
            # Full column rank → unique solution (square or overdetermined but consistent)
            if A.shape[0] == n_unknowns:
                # Square system
                self.solution_vector = np.linalg.solve(A, b)
            else:
                # Overdetermined but consistent
                self.solution_vector, residuals, _, _ = np.linalg.lstsq(A, b, rcond=None)
                if residuals.size > 0 and residuals[0] > _TOLERANCE:
                    raise InconsistentSystemError(
                        "Overdetermined system is inconsistent (residual too large)."
                    )
        else:
            # Under-determined — try maximum-entropy solution via Piter
            try:
                self.solution_vector = self.piter.getOptimalSolution(
                    epochs=2000, stop=0.00001
                )
            except Exception as e:
                raise UnderdeterminedSystemError(
                    f"The probability system is underdetermined and the optimizer failed: {e}"
                )

        # Validate the solution vector
        if np.any(self.solution_vector < -_TOLERANCE):
            raise InvalidSolutionError(
                "Solved probability system yields negative base probabilities."
            )

        total = float(np.sum(self.solution_vector))
        if abs(total - 1.0) > _TOLERANCE:
            raise InvalidSolutionError(
                f"Base probabilities sum to {total}, expected 1.0."
            )

        self.is_solved = True
        return total

    def query(self, target_str: str, condition_str: str = "True") -> float:
        """
        Calculate a posteriori probability based on the solved system.
        Query: P(target | condition)

        Raises:
            ImpossibleConditionError: if the condition has zero probability.
        """
        if not self.is_solved:
            self.solve()

        target = self._parse_logic(target_str)

        if condition_str and condition_str.lower() != "true":
            condition = self._parse_logic(condition_str)
        else:
            condition = sympy.true

        # Piter's getNumDem rejects symbols that were not present at finalize().
        # Ensure we fail with a clear message instead of a raw PiterException.
        known_symbols = self._finalized_symbols or set()
        for expr, name in ((target, "target"), (condition, "condition")):
            extra = {str(s) for s in sympy.preorder_traversal(expr) if isinstance(s, sympy.core.symbol.Symbol)} - {str(s) for s in known_symbols}
            if extra:
                raise SymbolError(
                    f"Query {name} introduces unknown symbol(s) {extra!r}. "
                    f"They must be declared in a <symbol> or used in a <prob> / <constraint> before finalizing."
                )

        num_mask, dem_mask = self.piter.getNumDem(target, condition)

        probability_numerator = np.sum(num_mask * self.solution_vector)
        probability_denominator = np.sum(dem_mask * self.solution_vector)

        if probability_denominator <= _TOLERANCE:
            raise ImpossibleConditionError(
                f"Condition '{condition_str}' has zero probability; P(... | condition) is undefined."
            )

        return float(probability_numerator / probability_denominator)
