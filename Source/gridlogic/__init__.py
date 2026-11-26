"""gridlogic - a no-guess grid deduction game with a CNF/DPLL logic agent.

Package layout
--------------
board       Board geometry, cell ids, Status
regions     Clue regions (rows, columns, neighbours, lists + extensions)
clues       Structured clues: validation, semantic evaluator, formula, text
logic       Propositional formula AST used between clues and CNF
cnf         Variable pool (primary vs auxiliary variables) and CNF container
encoder     Formula -> CNF (direct / sequential counter / totalizer / XOR chain)
dpll        DPLL SAT solver (unit propagation, backtracking, statistics)
knowledge   KB_t construction, entailment queries, hint explanations
state       PublicState - the only data the Logic Agent may see
puzzle      Complete puzzle (hidden solution included) + JSON I/O
engine      Game Engine: referees verdicts and reveals cards
agent       Logic Agent: deduction loop, trace, hint
uniqueness  Uniqueness check over all clues, puzzle audit
generator   Random no-guess puzzle generator
"""

__version__ = "1.0.0"
