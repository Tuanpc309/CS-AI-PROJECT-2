# Experiment results

Generated 2026-11-23 22:22:26 on Python 3.12.10 (Windows-11-10.0.26300-SP0). Runtime = median of 3 runs.


## baseline — step mode, auto encoding, first-variable branching, model reuse on

| puzzle | size | status | primary_vars | aux_vars | clauses | sat_calls | decisions | propagations | backtracks | steps | waves | time_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic-3x3-a | 3x3 | SOLVED | 9 | 0 | 40 | 44 | 0 | 193 | 0 | 8 | 8 | 2.13 |
| classic-3x3-b | 3x3 | SOLVED | 9 | 0 | 47 | 44 | 6 | 227 | 0 | 8 | 8 | 2.32 |
| classic-3x3-c | 3x3 | SOLVED | 9 | 0 | 68 | 43 | 5 | 239 | 0 | 8 | 8 | 2.78 |
| ext-3x3-a | 3x3 | SOLVED | 9 | 28 | 151 | 44 | 15 | 475 | 0 | 8 | 8 | 4.64 |
| classic-4x4-a | 4x4 | SOLVED | 16 | 0 | 105 | 129 | 35 | 1041 | 0 | 15 | 15 | 8.02 |
| classic-4x4-b | 4x4 | SOLVED | 16 | 0 | 341 | 122 | 107 | 1108 | 0 | 15 | 15 | 19.78 |
| classic-4x4-c | 4x4 | SOLVED | 16 | 0 | 82 | 131 | 192 | 1027 | 0 | 15 | 15 | 7.7 |
| ext-4x4-a | 4x4 | SOLVED | 16 | 0 | 88 | 135 | 0 | 925 | 0 | 15 | 15 | 7.59 |
| ext-4x4-b | 4x4 | SOLVED | 16 | 48 | 509 | 130 | 66 | 2063 | 0 | 15 | 15 | 26.66 |
| stress-5x5-a | 5x5 | SOLVED | 25 | 0 | 355 | 310 | 472 | 3409 | 21 | 24 | 24 | 27.45 |
| stress-ext-5x5-a | 5x5 | SOLVED | 25 | 53 | 397 | 298 | 765 | 8237 | 0 | 24 | 24 | 34.1 |
| special-inconsistent-3x3 | 3x3 | INCONSISTENT | 9 | 0 | 9 | 1 | 0 | 4 | 0 | 0 | 0 | 0.1 |
| special-multi-3x3 | 3x3 | STUCK | 9 | 0 | 10 | 24 | 0 | 68 | 0 | 2 | 2 | 0.6 |
| special-stuck-3x3 | 3x3 | STUCK | 9 | 0 | 113 | 8 | 29 | 36 | 0 | 0 | 0 | 0.85 |
| tutorial-3x3 | 3x3 | SOLVED | 9 | 13 | 78 | 44 | 2 | 302 | 0 | 8 | 8 | 3.06 |

## enc-direct — direct (combinatorial) cardinality encoding

| puzzle | size | status | primary_vars | aux_vars | clauses | sat_calls | decisions | propagations | backtracks | steps | waves | time_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic-3x3-a | 3x3 | SOLVED | 9 | 0 | 40 | 44 | 0 | 193 | 0 | 8 | 8 | 2.04 |
| classic-3x3-b | 3x3 | SOLVED | 9 | 0 | 47 | 44 | 6 | 227 | 0 | 8 | 8 | 2.24 |
| classic-3x3-c | 3x3 | SOLVED | 9 | 0 | 68 | 43 | 5 | 239 | 0 | 8 | 8 | 2.76 |
| ext-3x3-a | 3x3 | SOLVED | 9 | 24 | 150 | 44 | 15 | 458 | 0 | 8 | 8 | 4.66 |
| classic-4x4-a | 4x4 | SOLVED | 16 | 0 | 105 | 129 | 35 | 1041 | 0 | 15 | 15 | 7.91 |
| classic-4x4-b | 4x4 | SOLVED | 16 | 0 | 341 | 122 | 107 | 1108 | 0 | 15 | 15 | 19.1 |
| classic-4x4-c | 4x4 | SOLVED | 16 | 0 | 82 | 131 | 192 | 1027 | 0 | 15 | 15 | 7.46 |
| ext-4x4-a | 4x4 | SOLVED | 16 | 0 | 88 | 135 | 0 | 925 | 0 | 15 | 15 | 7.23 |
| ext-4x4-b | 4x4 | SOLVED | 16 | 48 | 509 | 130 | 66 | 2063 | 0 | 15 | 15 | 25.49 |
| stress-5x5-a | 5x5 | SOLVED | 25 | 0 | 355 | 310 | 472 | 3409 | 21 | 24 | 24 | 28.11 |
| stress-ext-5x5-a | 5x5 | SOLVED | 25 | 53 | 397 | 298 | 765 | 8237 | 0 | 24 | 24 | 34.58 |
| special-inconsistent-3x3 | 3x3 | INCONSISTENT | 9 | 0 | 9 | 1 | 0 | 4 | 0 | 0 | 0 | 0.1 |
| special-multi-3x3 | 3x3 | STUCK | 9 | 0 | 10 | 24 | 0 | 68 | 0 | 2 | 2 | 0.63 |
| special-stuck-3x3 | 3x3 | STUCK | 9 | 0 | 113 | 8 | 29 | 36 | 0 | 0 | 0 | 0.87 |
| tutorial-3x3 | 3x3 | SOLVED | 9 | 13 | 78 | 44 | 2 | 302 | 0 | 8 | 8 | 3.18 |

## enc-seqcounter — Sinz sequential counter

| puzzle | size | status | primary_vars | aux_vars | clauses | sat_calls | decisions | propagations | backtracks | steps | waves | time_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic-3x3-a | 3x3 | SOLVED | 9 | 32 | 93 | 44 | 0 | 390 | 0 | 8 | 8 | 2.77 |
| classic-3x3-b | 3x3 | SOLVED | 9 | 44 | 112 | 44 | 26 | 765 | 0 | 8 | 8 | 3.83 |
| classic-3x3-c | 3x3 | SOLVED | 9 | 76 | 182 | 43 | 26 | 871 | 0 | 8 | 8 | 4.85 |
| ext-3x3-a | 3x3 | SOLVED | 9 | 65 | 207 | 44 | 45 | 1257 | 0 | 8 | 8 | 6.5 |
| classic-4x4-a | 4x4 | SOLVED | 16 | 112 | 272 | 129 | 50 | 4705 | 0 | 15 | 15 | 14.38 |
| classic-4x4-b | 4x4 | SOLVED | 16 | 270 | 600 | 122 | 128 | 9453 | 0 | 15 | 15 | 32.58 |
| classic-4x4-c | 4x4 | SOLVED | 16 | 101 | 244 | 131 | 490 | 4869 | 0 | 15 | 15 | 14.66 |
| ext-4x4-a | 4x4 | SOLVED | 16 | 106 | 260 | 135 | 3 | 3324 | 0 | 15 | 15 | 12.26 |
| ext-4x4-b | 4x4 | SOLVED | 16 | 279 | 702 | 130 | 226 | 11831 | 0 | 15 | 15 | 36.59 |
| stress-5x5-a | 5x5 | SOLVED | 25 | 354 | 797 | 310 | 1305 | 20444 | 21 | 24 | 24 | 53.23 |
| stress-ext-5x5-a | 5x5 | SOLVED | 25 | 316 | 811 | 298 | 765 | 20348 | 0 | 24 | 24 | 57.83 |
| special-inconsistent-3x3 | 3x3 | INCONSISTENT | 9 | 6 | 18 | 1 | 0 | 7 | 0 | 0 | 0 | 0.13 |
| special-multi-3x3 | 3x3 | STUCK | 9 | 10 | 26 | 24 | 28 | 234 | 0 | 2 | 2 | 0.96 |
| special-stuck-3x3 | 3x3 | STUCK | 9 | 56 | 119 | 8 | 29 | 484 | 0 | 0 | 0 | 0.84 |
| tutorial-3x3 | 3x3 | SOLVED | 9 | 35 | 112 | 44 | 2 | 842 | 0 | 8 | 8 | 4.36 |

## enc-totalizer — totalizer

| puzzle | size | status | primary_vars | aux_vars | clauses | sat_calls | decisions | propagations | backtracks | steps | waves | time_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic-3x3-a | 3x3 | SOLVED | 9 | 23 | 106 | 44 | 0 | 342 | 0 | 8 | 8 | 2.87 |
| classic-3x3-b | 3x3 | SOLVED | 9 | 38 | 161 | 44 | 6 | 712 | 0 | 8 | 8 | 4.41 |
| classic-3x3-c | 3x3 | SOLVED | 9 | 54 | 218 | 43 | 5 | 744 | 0 | 8 | 8 | 5.38 |
| ext-3x3-a | 3x3 | SOLVED | 9 | 56 | 232 | 44 | 15 | 1085 | 0 | 8 | 8 | 7.08 |
| classic-4x4-a | 4x4 | SOLVED | 16 | 78 | 318 | 129 | 35 | 4381 | 0 | 15 | 15 | 17.77 |
| classic-4x4-b | 4x4 | SOLVED | 16 | 141 | 603 | 122 | 107 | 5997 | 0 | 15 | 15 | 28.33 |
| classic-4x4-c | 4x4 | SOLVED | 16 | 79 | 322 | 131 | 192 | 4263 | 0 | 15 | 15 | 17.39 |
| ext-4x4-a | 4x4 | SOLVED | 16 | 80 | 327 | 135 | 0 | 2894 | 0 | 15 | 15 | 13.91 |
| ext-4x4-b | 4x4 | SOLVED | 16 | 161 | 688 | 130 | 66 | 8304 | 0 | 15 | 15 | 37.36 |
| stress-5x5-a | 5x5 | SOLVED | 25 | 203 | 848 | 310 | 472 | 16033 | 21 | 24 | 24 | 56.34 |
| stress-ext-5x5-a | 5x5 | SOLVED | 25 | 191 | 793 | 298 | 765 | 15992 | 0 | 24 | 24 | 56.1 |
| special-inconsistent-3x3 | 3x3 | INCONSISTENT | 9 | 5 | 23 | 1 | 0 | 8 | 0 | 0 | 0 | 0.15 |
| special-multi-3x3 | 3x3 | STUCK | 9 | 5 | 24 | 24 | 0 | 185 | 0 | 2 | 2 | 0.87 |
| special-stuck-3x3 | 3x3 | STUCK | 9 | 24 | 107 | 8 | 29 | 228 | 0 | 0 | 0 | 0.74 |
| tutorial-3x3 | 3x3 | SOLVED | 9 | 30 | 123 | 44 | 2 | 900 | 0 | 8 | 8 | 4.87 |

## no-witness — always issue both entailment queries

| puzzle | size | status | primary_vars | aux_vars | clauses | sat_calls | decisions | propagations | backtracks | steps | waves | time_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic-3x3-a | 3x3 | SOLVED | 9 | 0 | 40 | 80 | 0 | 342 | 0 | 8 | 8 | 2.22 |
| classic-3x3-b | 3x3 | SOLVED | 9 | 0 | 47 | 80 | 15 | 411 | 0 | 8 | 8 | 2.46 |
| classic-3x3-c | 3x3 | SOLVED | 9 | 0 | 68 | 80 | 14 | 448 | 0 | 8 | 8 | 3.04 |
| ext-3x3-a | 3x3 | SOLVED | 9 | 28 | 151 | 80 | 32 | 855 | 0 | 8 | 8 | 5.08 |
| classic-4x4-a | 4x4 | SOLVED | 16 | 0 | 105 | 255 | 79 | 2088 | 0 | 15 | 15 | 9.08 |
| classic-4x4-b | 4x4 | SOLVED | 16 | 0 | 341 | 255 | 307 | 2372 | 0 | 15 | 15 | 21.56 |
| classic-4x4-c | 4x4 | SOLVED | 16 | 0 | 82 | 255 | 428 | 1951 | 0 | 15 | 15 | 8.93 |
| ext-4x4-a | 4x4 | SOLVED | 16 | 0 | 88 | 255 | 0 | 1715 | 0 | 15 | 15 | 8.25 |
| ext-4x4-b | 4x4 | SOLVED | 16 | 48 | 509 | 255 | 154 | 4343 | 0 | 15 | 15 | 29.02 |
| stress-5x5-a | 5x5 | SOLVED | 25 | 0 | 355 | 624 | 1091 | 7009 | 49 | 24 | 24 | 33.53 |
| stress-ext-5x5-a | 5x5 | SOLVED | 25 | 53 | 397 | 624 | 1861 | 19272 | 0 | 24 | 24 | 47.66 |
| special-inconsistent-3x3 | 3x3 | INCONSISTENT | 9 | 0 | 9 | 1 | 0 | 4 | 0 | 0 | 0 | 0.1 |
| special-multi-3x3 | 3x3 | STUCK | 9 | 0 | 10 | 45 | 0 | 128 | 0 | 2 | 2 | 0.74 |
| special-stuck-3x3 | 3x3 | STUCK | 9 | 0 | 113 | 17 | 60 | 77 | 0 | 0 | 0 | 1.02 |
| tutorial-3x3 | 3x3 | SOLVED | 9 | 13 | 78 | 80 | 5 | 564 | 0 | 8 | 8 | 3.61 |

## wave — reveal every forced card per round

| puzzle | size | status | primary_vars | aux_vars | clauses | sat_calls | decisions | propagations | backtracks | steps | waves | time_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic-3x3-a | 3x3 | SOLVED | 9 | 0 | 40 | 44 | 0 | 193 | 0 | 8 | 8 | 2.11 |
| classic-3x3-b | 3x3 | SOLVED | 9 | 0 | 47 | 26 | 8 | 136 | 0 | 5 | 5 | 2.0 |
| classic-3x3-c | 3x3 | SOLVED | 9 | 0 | 68 | 25 | 2 | 113 | 0 | 4 | 4 | 2.04 |
| ext-3x3-a | 3x3 | SOLVED | 9 | 28 | 151 | 32 | 9 | 410 | 0 | 6 | 6 | 4.65 |
| classic-4x4-a | 4x4 | SOLVED | 16 | 0 | 105 | 88 | 43 | 635 | 0 | 10 | 10 | 6.76 |
| classic-4x4-b | 4x4 | SOLVED | 16 | 0 | 341 | 53 | 37 | 433 | 0 | 6 | 6 | 12.88 |
| classic-4x4-c | 4x4 | SOLVED | 16 | 0 | 82 | 86 | 103 | 741 | 0 | 11 | 11 | 6.44 |
| ext-4x4-a | 4x4 | SOLVED | 16 | 0 | 88 | 132 | 0 | 880 | 0 | 14 | 14 | 6.95 |
| ext-4x4-b | 4x4 | SOLVED | 16 | 48 | 509 | 52 | 30 | 699 | 0 | 6 | 6 | 14.32 |
| stress-5x5-a | 5x5 | SOLVED | 25 | 0 | 355 | 207 | 241 | 1773 | 12 | 13 | 13 | 18.15 |
| stress-ext-5x5-a | 5x5 | SOLVED | 25 | 53 | 397 | 125 | 224 | 3167 | 0 | 10 | 10 | 23.37 |
| special-inconsistent-3x3 | 3x3 | INCONSISTENT | 9 | 0 | 9 | 1 | 0 | 4 | 0 | 0 | 0 | 0.1 |
| special-multi-3x3 | 3x3 | STUCK | 9 | 0 | 10 | 16 | 0 | 45 | 0 | 1 | 1 | 0.47 |
| special-stuck-3x3 | 3x3 | STUCK | 9 | 0 | 113 | 8 | 29 | 36 | 0 | 0 | 0 | 0.84 |
| tutorial-3x3 | 3x3 | SOLVED | 9 | 13 | 78 | 22 | 3 | 118 | 0 | 4 | 4 | 1.96 |

## wave-no-witness — wave mode without model reuse

| puzzle | size | status | primary_vars | aux_vars | clauses | sat_calls | decisions | propagations | backtracks | steps | waves | time_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic-3x3-a | 3x3 | SOLVED | 9 | 0 | 40 | 80 | 0 | 342 | 0 | 8 | 8 | 2.24 |
| classic-3x3-b | 3x3 | SOLVED | 9 | 0 | 47 | 53 | 19 | 290 | 0 | 5 | 5 | 2.1 |
| classic-3x3-c | 3x3 | SOLVED | 9 | 0 | 68 | 46 | 5 | 205 | 0 | 4 | 4 | 2.06 |
| ext-3x3-a | 3x3 | SOLVED | 9 | 28 | 151 | 58 | 20 | 750 | 0 | 6 | 6 | 4.74 |
| classic-4x4-a | 4x4 | SOLVED | 16 | 0 | 105 | 172 | 93 | 1251 | 0 | 10 | 10 | 7.37 |
| classic-4x4-b | 4x4 | SOLVED | 16 | 0 | 341 | 112 | 122 | 944 | 0 | 6 | 6 | 13.74 |
| classic-4x4-c | 4x4 | SOLVED | 16 | 0 | 82 | 165 | 232 | 1381 | 0 | 11 | 11 | 7.49 |
| ext-4x4-a | 4x4 | SOLVED | 16 | 0 | 88 | 250 | 0 | 1640 | 0 | 14 | 14 | 8.18 |
| ext-4x4-b | 4x4 | SOLVED | 16 | 48 | 509 | 102 | 74 | 1383 | 0 | 6 | 6 | 15.59 |
| stress-5x5-a | 5x5 | SOLVED | 25 | 0 | 355 | 403 | 526 | 3439 | 28 | 13 | 13 | 21.82 |
| stress-ext-5x5-a | 5x5 | SOLVED | 25 | 53 | 397 | 268 | 585 | 8056 | 0 | 10 | 10 | 28.54 |
| special-inconsistent-3x3 | 3x3 | INCONSISTENT | 9 | 0 | 9 | 1 | 0 | 4 | 0 | 0 | 0 | 0.1 |
| special-multi-3x3 | 3x3 | STUCK | 9 | 0 | 10 | 30 | 0 | 85 | 0 | 1 | 1 | 0.53 |
| special-stuck-3x3 | 3x3 | STUCK | 9 | 0 | 113 | 17 | 60 | 77 | 0 | 0 | 0 | 0.99 |
| tutorial-3x3 | 3x3 | SOLVED | 9 | 13 | 78 | 42 | 7 | 227 | 0 | 4 | 4 | 2.13 |

## occurrence — most-occurrences branching

| puzzle | size | status | primary_vars | aux_vars | clauses | sat_calls | decisions | propagations | backtracks | steps | waves | time_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic-3x3-a | 3x3 | SOLVED | 9 | 0 | 40 | 44 | 0 | 193 | 0 | 8 | 8 | 2.01 |
| classic-3x3-b | 3x3 | SOLVED | 9 | 0 | 47 | 44 | 6 | 227 | 0 | 8 | 8 | 2.24 |
| classic-3x3-c | 3x3 | SOLVED | 9 | 0 | 68 | 43 | 5 | 239 | 0 | 8 | 8 | 2.74 |
| ext-3x3-a | 3x3 | SOLVED | 9 | 28 | 151 | 44 | 15 | 475 | 0 | 8 | 8 | 4.85 |
| classic-4x4-a | 4x4 | SOLVED | 16 | 0 | 105 | 129 | 53 | 1023 | 0 | 15 | 15 | 7.97 |
| classic-4x4-b | 4x4 | SOLVED | 16 | 0 | 341 | 122 | 107 | 1108 | 0 | 15 | 15 | 19.1 |
| classic-4x4-c | 4x4 | SOLVED | 16 | 0 | 82 | 131 | 192 | 1027 | 0 | 15 | 15 | 7.74 |
| ext-4x4-a | 4x4 | SOLVED | 16 | 0 | 88 | 135 | 0 | 925 | 0 | 15 | 15 | 7.37 |
| ext-4x4-b | 4x4 | SOLVED | 16 | 48 | 509 | 130 | 66 | 2063 | 0 | 15 | 15 | 25.88 |
| stress-5x5-a | 5x5 | SOLVED | 25 | 0 | 355 | 312 | 478 | 3382 | 0 | 24 | 24 | 28.56 |
| stress-ext-5x5-a | 5x5 | SOLVED | 25 | 53 | 397 | 298 | 492 | 8572 | 12 | 24 | 24 | 34.63 |
| special-inconsistent-3x3 | 3x3 | INCONSISTENT | 9 | 0 | 9 | 1 | 0 | 4 | 0 | 0 | 0 | 0.1 |
| special-multi-3x3 | 3x3 | STUCK | 9 | 0 | 10 | 24 | 0 | 68 | 0 | 2 | 2 | 0.63 |
| special-stuck-3x3 | 3x3 | STUCK | 9 | 0 | 113 | 8 | 29 | 36 | 0 | 0 | 0 | 0.85 |
| tutorial-3x3 | 3x3 | SOLVED | 9 | 13 | 78 | 44 | 2 | 302 | 0 | 8 | 8 | 3.16 |

## pure-literal — pure-literal elimination on

| puzzle | size | status | primary_vars | aux_vars | clauses | sat_calls | decisions | propagations | backtracks | steps | waves | time_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic-3x3-a | 3x3 | SOLVED | 9 | 0 | 40 | 44 | 0 | 193 | 0 | 8 | 8 | 2.27 |
| classic-3x3-b | 3x3 | SOLVED | 9 | 0 | 47 | 44 | 6 | 227 | 0 | 8 | 8 | 2.49 |
| classic-3x3-c | 3x3 | SOLVED | 9 | 0 | 68 | 44 | 2 | 243 | 0 | 8 | 8 | 3.11 |
| ext-3x3-a | 3x3 | SOLVED | 9 | 28 | 151 | 44 | 15 | 475 | 0 | 8 | 8 | 6.41 |
| classic-4x4-a | 4x4 | SOLVED | 16 | 0 | 105 | 129 | 35 | 1018 | 0 | 15 | 15 | 10.15 |
| classic-4x4-b | 4x4 | SOLVED | 16 | 0 | 341 | 122 | 107 | 1108 | 0 | 15 | 15 | 30.53 |
| classic-4x4-c | 4x4 | SOLVED | 16 | 0 | 82 | 132 | 46 | 1034 | 0 | 15 | 15 | 9.84 |
| ext-4x4-a | 4x4 | SOLVED | 16 | 0 | 88 | 135 | 0 | 925 | 0 | 15 | 15 | 8.34 |
| ext-4x4-b | 4x4 | SOLVED | 16 | 48 | 509 | 130 | 66 | 2063 | 0 | 15 | 15 | 37.51 |
| stress-5x5-a | 5x5 | SOLVED | 25 | 0 | 355 | 312 | 79 | 3371 | 21 | 24 | 24 | 43.56 |
| stress-ext-5x5-a | 5x5 | SOLVED | 25 | 53 | 397 | 298 | 765 | 8237 | 0 | 24 | 24 | 98.79 |
| special-inconsistent-3x3 | 3x3 | INCONSISTENT | 9 | 0 | 9 | 1 | 0 | 4 | 0 | 0 | 0 | 0.1 |
| special-multi-3x3 | 3x3 | STUCK | 9 | 0 | 10 | 24 | 0 | 68 | 0 | 2 | 2 | 0.7 |
| special-stuck-3x3 | 3x3 | STUCK | 9 | 0 | 113 | 8 | 29 | 36 | 0 | 0 | 0 | 4.07 |
| tutorial-3x3 | 3x3 | SOLVED | 9 | 13 | 78 | 44 | 2 | 302 | 0 | 8 | 8 | 3.66 |

## seq-no-witness — sequential counter, both queries always (stress for DPLL)

| puzzle | size | status | primary_vars | aux_vars | clauses | sat_calls | decisions | propagations | backtracks | steps | waves | time_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic-3x3-a | 3x3 | SOLVED | 9 | 32 | 93 | 80 | 0 | 692 | 0 | 8 | 8 | 3.03 |
| classic-3x3-b | 3x3 | SOLVED | 9 | 44 | 112 | 80 | 47 | 1495 | 0 | 8 | 8 | 4.39 |
| classic-3x3-c | 3x3 | SOLVED | 9 | 76 | 182 | 80 | 65 | 1763 | 0 | 8 | 8 | 5.5 |
| ext-3x3-a | 3x3 | SOLVED | 9 | 65 | 207 | 80 | 108 | 2320 | 0 | 8 | 8 | 7.35 |
| classic-4x4-a | 4x4 | SOLVED | 16 | 112 | 272 | 255 | 109 | 10061 | 0 | 15 | 15 | 18.19 |
| classic-4x4-b | 4x4 | SOLVED | 16 | 270 | 600 | 255 | 374 | 22736 | 0 | 15 | 15 | 40.0 |
| classic-4x4-c | 4x4 | SOLVED | 16 | 101 | 244 | 255 | 1158 | 9527 | 0 | 15 | 15 | 19.39 |
| ext-4x4-a | 4x4 | SOLVED | 16 | 106 | 260 | 255 | 6 | 6127 | 0 | 15 | 15 | 14.36 |
| ext-4x4-b | 4x4 | SOLVED | 16 | 279 | 702 | 255 | 601 | 26344 | 0 | 15 | 15 | 47.33 |
| stress-5x5-a | 5x5 | SOLVED | 25 | 354 | 797 | 624 | 3142 | 45145 | 49 | 24 | 24 | 74.7 |
| stress-ext-5x5-a | 5x5 | SOLVED | 25 | 316 | 811 | 624 | 1861 | 48987 | 0 | 24 | 24 | 81.41 |
| special-inconsistent-3x3 | 3x3 | INCONSISTENT | 9 | 6 | 18 | 1 | 0 | 7 | 0 | 0 | 0 | 0.15 |
| special-multi-3x3 | 3x3 | STUCK | 9 | 10 | 26 | 45 | 54 | 446 | 0 | 2 | 2 | 1.18 |
| special-stuck-3x3 | 3x3 | STUCK | 9 | 56 | 119 | 17 | 60 | 1029 | 0 | 0 | 0 | 1.31 |
| tutorial-3x3 | 3x3 | SOLVED | 9 | 35 | 112 | 80 | 5 | 1612 | 0 | 8 | 8 | 5.03 |

## tot-occurrence — totalizer with most-occurrences branching

| puzzle | size | status | primary_vars | aux_vars | clauses | sat_calls | decisions | propagations | backtracks | steps | waves | time_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic-3x3-a | 3x3 | SOLVED | 9 | 23 | 106 | 80 | 0 | 600 | 0 | 8 | 8 | 3.22 |
| classic-3x3-b | 3x3 | SOLVED | 9 | 38 | 161 | 80 | 15 | 1349 | 0 | 8 | 8 | 5.07 |
| classic-3x3-c | 3x3 | SOLVED | 9 | 54 | 218 | 80 | 21 | 1472 | 0 | 8 | 8 | 6.1 |
| ext-3x3-a | 3x3 | SOLVED | 9 | 56 | 232 | 80 | 23 | 1981 | 0 | 8 | 8 | 7.85 |
| classic-4x4-a | 4x4 | SOLVED | 16 | 78 | 318 | 255 | 79 | 9149 | 0 | 15 | 15 | 22.14 |
| classic-4x4-b | 4x4 | SOLVED | 16 | 141 | 603 | 255 | 227 | 13501 | 0 | 15 | 15 | 36.48 |
| classic-4x4-c | 4x4 | SOLVED | 16 | 79 | 322 | 255 | 277 | 8595 | 0 | 15 | 15 | 22.22 |
| ext-4x4-a | 4x4 | SOLVED | 16 | 80 | 327 | 255 | 0 | 5305 | 0 | 15 | 15 | 16.67 |
| ext-4x4-b | 4x4 | SOLVED | 16 | 161 | 688 | 255 | 227 | 17279 | 18 | 15 | 15 | 45.03 |
| stress-5x5-a | 5x5 | SOLVED | 25 | 203 | 848 | 624 | 932 | 34097 | 0 | 24 | 24 | 74.24 |
| stress-ext-5x5-a | 5x5 | SOLVED | 25 | 191 | 793 | 624 | 1186 | 38072 | 52 | 24 | 24 | 79.49 |
| special-inconsistent-3x3 | 3x3 | INCONSISTENT | 9 | 5 | 23 | 1 | 0 | 8 | 0 | 0 | 0 | 0.15 |
| special-multi-3x3 | 3x3 | STUCK | 9 | 5 | 24 | 45 | 0 | 350 | 0 | 2 | 2 | 1.1 |
| special-stuck-3x3 | 3x3 | STUCK | 9 | 24 | 107 | 17 | 42 | 503 | 0 | 0 | 0 | 1.08 |
| tutorial-3x3 | 3x3 | SOLVED | 9 | 30 | 123 | 80 | 5 | 1652 | 0 | 8 | 8 | 5.78 |

## Uniqueness check (complete clue set + initial face-up cards)

| puzzle | size | status | primary_vars | aux_vars | clauses | sat_calls | decisions | propagations | backtracks | time_ms | wave_count |
|---|---|---|---|---|---|---|---|---|---|---|---|
| classic-3x3-a | 3x3 | UNIQUE | 9 | 0 | 32 | 2 | 0 | 18 | 0 | 0.2 | 8 |
| classic-3x3-b | 3x3 | UNIQUE | 9 | 0 | 39 | 2 | 0 | 18 | 0 | 0.21 | 5 |
| classic-3x3-c | 3x3 | UNIQUE | 9 | 0 | 60 | 2 | 0 | 18 | 0 | 0.27 | 4 |
| ext-3x3-a | 3x3 | UNIQUE | 9 | 28 | 143 | 2 | 0 | 70 | 0 | 0.58 | 6 |
| classic-4x4-a | 4x4 | UNIQUE | 16 | 0 | 90 | 2 | 0 | 32 | 0 | 0.43 | 10 |
| classic-4x4-b | 4x4 | UNIQUE | 16 | 0 | 326 | 2 | 0 | 32 | 0 | 1.22 | 6 |
| classic-4x4-c | 4x4 | UNIQUE | 16 | 0 | 67 | 2 | 0 | 32 | 0 | 0.34 | 11 |
| ext-4x4-a | 4x4 | UNIQUE | 16 | 0 | 73 | 2 | 0 | 32 | 0 | 0.41 | 14 |
| ext-4x4-b | 4x4 | UNIQUE | 16 | 48 | 494 | 2 | 0 | 124 | 0 | 1.87 | 6 |
| stress-5x5-a | 5x5 | UNIQUE | 25 | 0 | 331 | 2 | 2 | 56 | 3 | 1.54 | 13 |
| stress-ext-5x5-a | 5x5 | UNIQUE | 25 | 53 | 373 | 2 | 0 | 138 | 0 | 1.3 | 10 |
| special-inconsistent-3x3 | 3x3 | NO_SOLUTION | 9 | 5 | 44 | 1 | 0 | 5 | 0 | 0.19 | 0 |
| special-multi-3x3 | 3x3 | MULTIPLE | 9 | 13 | 62 | 2 | 9 | 35 | 0 | 0.34 | 1 |
| special-stuck-3x3 | 3x3 | UNIQUE | 9 | 13 | 178 | 2 | 0 | 40 | 0 | 0.78 | 0 |
| tutorial-3x3 | 3x3 | UNIQUE | 9 | 13 | 70 | 2 | 0 | 38 | 0 | 0.35 | 4 |

## Scaling study (generated puzzles, fixed seeds)

| experiment | puzzle | size | status | primary_vars | aux_vars | clauses | sat_calls | decisions | propagations | backtracks | steps | waves | time_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | scale-3x3-s11 | 3x3 | SOLVED | 9 | 0 | 49 | 40 | 7 | 248 | 0 | 8 | 8 | 2.89 |
| seq-no-witness | scale-3x3-s11 | 3x3 | SOLVED | 9 | 21 | 72 | 80 | 64 | 868 | 0 | 8 | 8 | 3.63 |
| baseline | scale-3x3-s12 | 3x3 | SOLVED | 9 | 16 | 86 | 44 | 0 | 437 | 0 | 8 | 8 | 4.32 |
| seq-no-witness | scale-3x3-s12 | 3x3 | SOLVED | 9 | 42 | 126 | 80 | 33 | 1344 | 0 | 8 | 8 | 5.15 |
| baseline | scale-4x4-s11 | 4x4 | SOLVED | 16 | 17 | 158 | 123 | 127 | 1185 | 44 | 15 | 15 | 8.57 |
| seq-no-witness | scale-4x4-s11 | 4x4 | SOLVED | 16 | 112 | 310 | 255 | 339 | 11601 | 44 | 15 | 15 | 23.86 |
| baseline | scale-4x4-s12 | 4x4 | SOLVED | 16 | 24 | 214 | 132 | 81 | 1265 | 0 | 15 | 15 | 9.22 |
| seq-no-witness | scale-4x4-s12 | 4x4 | SOLVED | 16 | 148 | 384 | 255 | 772 | 7659 | 0 | 15 | 15 | 19.89 |
| baseline | scale-5x5-s11 | 5x5 | SOLVED | 25 | 11 | 178 | 292 | 786 | 5434 | 120 | 24 | 24 | 24.16 |
| seq-no-witness | scale-5x5-s11 | 5x5 | SOLVED | 25 | 125 | 355 | 624 | 1867 | 21217 | 126 | 24 | 24 | 45.17 |
| baseline | scale-5x5-s12 | 5x5 | SOLVED | 25 | 285 | 858 | 299 | 196 | 13767 | 0 | 24 | 24 | 56.41 |
| seq-no-witness | scale-5x5-s12 | 5x5 | SOLVED | 25 | 474 | 1144 | 624 | 787 | 75938 | 0 | 24 | 24 | 121.78 |
| baseline | scale-6x6-s11 | 6x6 | SOLVED | 36 | 131 | 1045 | 577 | 16252 | 70027 | 28609 | 35 | 35 | 217.72 |
| seq-no-witness | scale-6x6-s11 | 6x6 | SOLVED | 36 | 524 | 1472 | 1295 | 33109 | 418622 | 55811 | 35 | 35 | 602.53 |
| baseline | scale-6x6-s12 | 6x6 | SOLVED | 36 | 32 | 738 | 598 | 3678 | 19923 | 2990 | 35 | 35 | 154.6 |
| seq-no-witness | scale-6x6-s12 | 6x6 | SOLVED | 36 | 498 | 1206 | 1295 | 10945 | 293063 | 2991 | 35 | 35 | 426.82 |
| baseline | scale-7x7-s11 | 7x7 | SOLVED | 49 | 147 | 2135 | 1058 | 90429 | 738790 | 166170 | 48 | 48 | 2515.93 |
| seq-no-witness | scale-7x7-s11 | 7x7 | SOLVED | 49 | 1195 | 2939 | 2400 | 103789 | 4285523 | 166499 | 48 | 48 | 5585.05 |
| baseline | scale-7x7-s12 | 7x7 | SOLVED | 49 | 146 | 2158 | 992 | 14071 | 58458 | 14416 | 48 | 48 | 489.56 |
| seq-no-witness | scale-7x7-s12 | 7x7 | SOLVED | 49 | 1202 | 2942 | 2400 | 53890 | 1237184 | 14487 | 48 | 48 | 1686.08 |
| baseline | scale-8x8-s11 | 8x8 | SOLVED | 64 | 45 | 2064 | 1842 | 21725 | 75453 | 170 | 63 | 63 | 423.36 |
| seq-no-witness | scale-8x8-s11 | 8x8 | SOLVED | 64 | 1186 | 2735 | 4095 | 157548 | 1098039 | 512 | 63 | 63 | 1757.53 |
| baseline | scale-8x8-s12 | 8x8 | SOLVED | 64 | 243 | 2774 | 1829 | 10688 | 100467 | 28 | 63 | 63 | 551.86 |
| seq-no-witness | scale-8x8-s12 | 8x8 | SOLVED | 64 | 1475 | 3860 | 4095 | 55168 | 1682421 | 45 | 63 | 63 | 2249.32 |
| seq-no-witness@1.40s | scale-7x7-s11 | 7x7 | TIMEOUT | 49 | 334 | 850 | 880 | 10888 | 326953 | 11752 | 10 | 10 | 1397.67 |
