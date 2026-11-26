import itertools
import random
import time
import unittest

import helpers  # noqa: F401  (sets sys.path)

from gridlogic.dpll import DPLLSolver, SolverConfig, SolverTimeout


def brute_force(n, clauses, assumptions=()):
    for bits in itertools.product((False, True), repeat=n):
        val = {i + 1: b for i, b in enumerate(bits)}
        if any(val[abs(a)] != (a > 0) for a in assumptions):
            continue
        if all(any(val[abs(l)] == (l > 0) for l in c) for c in clauses):
            return True
    return False


def satisfies(model, clauses):
    return all(any(model[abs(l)] == (l > 0) for l in c) for c in clauses)


class DPLLTests(unittest.TestCase):
    CONFIGS = [
        SolverConfig(),
        SolverConfig(heuristic="occurrence"),
        SolverConfig(pure_literal=True),
        SolverConfig(phase=True, heuristic="occurrence", pure_literal=True),
    ]

    def test_random_formulas_against_brute_force(self):
        rng = random.Random(1)
        for trial in range(250):
            n = rng.randint(3, 9)
            m = rng.randint(1, 5 * n)
            clauses = [[rng.choice((-1, 1)) * rng.randint(1, n) for _ in range(rng.randint(1, 3))]
                       for _ in range(m)]
            assumptions = [rng.choice((-1, 1)) * rng.randint(1, n) for _ in range(rng.randint(0, 2))]
            expected = brute_force(n, clauses, assumptions)
            for cfg in self.CONFIGS:
                res = DPLLSolver(n, clauses, cfg).solve(assumptions)
                self.assertEqual(res.satisfiable, expected, (clauses, assumptions, cfg))
                if res.satisfiable:
                    self.assertEqual(len(res.model), n)  # complete assignment
                    self.assertTrue(satisfies(res.model, clauses))
                    self.assertTrue(all(res.model[abs(a)] == (a > 0) for a in assumptions))

    def test_spec_example(self):
        # KB = (A ∨ B) ∧ (¬A ∨ B): B is entailed, A is not
        solver = DPLLSolver(2, [[1, 2], [-1, 2]])
        self.assertTrue(solver.solve().satisfiable)
        self.assertFalse(solver.solve([-2]).satisfiable)   # KB ∧ ¬B UNSAT  -> B criminal
        self.assertTrue(solver.solve([1]).satisfiable)
        self.assertTrue(solver.solve([-1]).satisfiable)    # A unknown

    def test_conflict_and_empty_clause(self):
        self.assertFalse(DPLLSolver(1, [[1], [-1]]).solve().satisfiable)
        self.assertFalse(DPLLSolver(2, [[1, 2], []]).solve().satisfiable)
        self.assertFalse(DPLLSolver(2, [[1]]).solve([-1]).satisfiable)

    def test_free_variables_get_values(self):
        res = DPLLSolver(5, [[1, 2]]).solve()
        self.assertEqual(sorted(res.model), [1, 2, 3, 4, 5])

    def test_statistics(self):
        # pigeonhole PHP(3,2): UNSAT and needs branching + backtracking
        p = lambda i, j: 2 * i + j + 1  # noqa: E731  pigeon i in hole j
        clauses = [[p(i, 0), p(i, 1)] for i in range(3)]
        clauses += [[-p(i, j), -p(k, j)] for j in range(2) for i in range(3) for k in range(i + 1, 3)]
        res = DPLLSolver(6, clauses).solve()
        self.assertFalse(res.satisfiable)
        self.assertGreater(res.stats.decisions, 0)
        self.assertGreater(res.stats.backtracks, 0)
        self.assertGreater(res.stats.propagations, 0)
        self.assertGreater(res.stats.conflicts, 0)
        self.assertGreaterEqual(res.stats.time_ms, 0.0)
        # unit propagation alone decides this one
        res = DPLLSolver(3, [[1], [-1, 2], [-2, 3]]).solve()
        self.assertEqual(res.stats.decisions, 0)
        self.assertEqual(res.stats.propagations, 3)

    def test_solver_reuse_is_independent(self):
        solver = DPLLSolver(3, [[1, 2, 3], [-1, -2], [-2, -3], [-1, -3]])
        first = solver.solve([1]).model
        self.assertFalse(solver.solve([1, 2]).satisfiable)
        self.assertEqual(solver.solve([1]).model, first)

    def test_deadline(self):
        n = 14
        p = lambda i, j: (n - 1) * i + j + 1  # noqa: E731  PHP(n, n-1) is hard for plain DPLL
        clauses = [[p(i, j) for j in range(n - 1)] for i in range(n)]
        clauses += [[-p(i, j), -p(k, j)] for j in range(n - 1) for i in range(n) for k in range(i + 1, n)]
        with self.assertRaises(SolverTimeout):
            DPLLSolver(n * (n - 1), clauses).solve(deadline=time.perf_counter() + 0.05)


if __name__ == "__main__":
    unittest.main()
