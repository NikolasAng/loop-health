# Loop Health Framework Architecture

## Overview

The Loop Health framework is organized into core modules, domain implementations, and demonstration scripts.

```
loop-health/
├── loop_health/                 # Core framework
│   ├── loop_health.py          # Main LH metrics
│   ├── chess_engine.py         # Chess-specific engine
│   ├── chess_game.py           # Chess domain wrapper
│   ├── features.py             # Feature extractors
│   └── game.py                 # Base game abstraction
├── games/
│   └── chess/                  # Chess domain
│       ├── chess_null_model.py           # Permutation testing
│       ├── live_chess_demo.py            # Real-time demo
│       └── selfplay_detection_chess.py   # Self-play analysis
├── examples/
│   └── basic_usage.py          # Usage examples
├── docs/
│   └── ARCHITECTURE.md         # This file
├── tests/                      # Unit tests (future)
└── [config files]              # setup.py, requirements.txt, etc.
```

## Core Modules

### loop_health.py

**Purpose**: Implement the core Loop Health algorithm.

**Key Classes**:
- `LHConfig`: Configuration for weights and thresholds
- `TransitionMetrics`: Per-step metrics (I, Thr, P, E, R, A, S, LH)
- `LoopRecord`: Detected loop with topology classification
- `GameLoopHealthEngine`: Base engine class

**Key Methods**:
- `compute_lh(metrics) -> float`: Compute LH for a step
- `detect_exact_loops(history) -> List[LoopRecord]`: Hash-based loop detection
- `classify_topology(loop) -> str`: Classify as Cycle/Spring/Tube

**Inputs**: Game history, list of moves
**Outputs**: Detected loops, LH values, topology classifications

### chess_engine.py

**Purpose**: Chess-specific implementation of Loop Health.

**Key Classes**:
- `ChessLoopHealthEngine`: Extends GameLoopHealthEngine for chess
- Implements chess-specific feature extraction
- Handles board state analysis

**Key Methods**:
- `analyse(history, moves) -> Dict`: Main analysis entry point
- Returns: all_loops, exact_loops, functional_loops, metrics, topology_counts, lh_values, lh_mean

**Dependency Chain**:
```
ChessGame (domain wrapper)
    ↓
ChessLoopHealthEngine (chess-specific analysis)
    ↓
FeatureExtractor (domain-agnostic features)
    ↓
LH computation (core algorithm)
```

### chess_game.py

**Purpose**: Chess domain wrapper and policy implementations.

**Key Classes**:
- `ChessGame`: Wrapper around python-chess
- Policy functions: `get_random_move()`, `get_greedy_move()`, `get_defensive_move()`, `get_minimax_move()`

**Dependency**: python-chess library

### features.py

**Purpose**: Extract structural features from game states.

**Key Classes**:
- `FeatureExtractor`: Compute I, Thr, P, E, R, A, S per step
- Domain-agnostic design (works for any game with defined state properties)

**Features**:
- I: Information gain (new knowledge)
- Thr: Threat change (distance to key objectives)
- P: Progress (material/positional advancement)
- E: Evaluation shift (strategic score change)
- R: Irreversibility (commitment to current strategy)
- A: Asymmetry (difference between player positions)
- S: Stagnation indicator (explicit repetition detection)

### game.py

**Purpose**: Base game abstraction.

**Key Classes**:
- `State`: Abstract state representation
- `Game`: Base game class with state transitions, terminal conditions, etc.

**Design**: Template method pattern allows subclassing for new domains

## Domain Implementations

### games/chess/

**Purpose**: Chess-specific demonstrations and analysis.

#### chess_null_model.py
- Implements permutation null-model testing
- Runs 500 permutations per matchup
- Outputs correlation statistics (r, p-value, effect size)
- Validates that LH⁻ (circularity-free) correlates with stagnation indicator
- **Usage**: `python chess_null_model.py`

#### live_chess_demo.py
- Real-time demonstration of CST-Lazy loop-breaking
- Plays chess games with artificial stagnation patterns
- Detects and breaks loops in real-time
- Shows which moves are recovered via intervention
- **Usage**: `python live_chess_demo.py`

#### selfplay_detection_chess.py
- Analyzes self-play across multiple policy matchups
- Detects board position attractors (positions that cause loops)
- Generates statistics on attractor characteristics
- **Usage**: `python selfplay_detection_chess.py`

## Data Flow

### Single Game Analysis

```
ChessGame (history + moves)
    ↓
ChessLoopHealthEngine.analyse()
    ├─ detect_exact_loops(history)
    │   └─ Hash-based state matching
    ├─ For each loop:
    │   ├─ Extract features (FeatureExtractor)
    │   ├─ Compute LH values
    │   └─ Classify topology
    └─ Return: analysis dict with all_loops, metrics, topologies
```

### Batch Analysis (e.g., null model)

```
For each of N games:
    ├─ Play game (policies)
    ├─ Analyze (ChessLoopHealthEngine)
    ├─ Extract LH values and S values
    └─ Store results

Permutation test:
    ├─ Shuffle S values (break correspondence)
    ├─ Recompute correlation r(LH, S_shuffled)
    ├─ Repeat 500 times
    └─ Output: actual r, p-value, effect size
```

## Key Algorithms

### 1. Exact Loop Detection (Definition 1)

```
For each state s_t in history:
    If hash(s_t) == hash(s_u) for some u < t:
        Record loop [u, t]
```

**Complexity**: O(n) with hash table
**Output**: Exact repetitions of identical board states

### 2. Loop Health Computation (Definition 5)

```
For each step t:
    I(t) = information_gain
    Thr(t) = threat_density
    P(t) = progress
    E(t) = evaluation_shift
    R(t) = irreversibility
    A(t) = asymmetry
    S(t) = stagnation_indicator
    
    LH(t) = 0.15·I + 0.25·Thr + 0.20·P + 0.15·E + 0.05·R + 0.10·A - 0.10·S
```

**LH⁻ (Circularity-Free)**:
```
LH⁻(t) = 0.15·I + 0.25·Thr + 0.20·P + 0.15·E + 0.05·R + 0.10·A
        (same formula but without S term)
```

### 3. Topology Classification (Productivity Transformer, Definition 7)

```
For a detected loop [u, t]:
    avg_lh = mean(LH[u:t])
    
    if avg_lh ≤ θ_H (0.05):
        topology = "Cycle"      # Sterile
    else:
        td = directional_tension(loop)
        if td ≤ θ_TD (0.03):
            topology = "Spring"  # Intermediate
        else:
            topology = "Tube"    # Productive
```

## Configuration

### LHConfig Defaults

```python
w1 = 0.15   # Information gain weight
w2 = 0.25   # Throughput (threat) weight
w3 = 0.20   # Progress weight
w4 = 0.15   # Evaluation shift weight
w5 = 0.05   # Irreversibility weight
w6 = 0.10   # Asymmetry weight
w7 = 0.10   # Stagnation weight

theta_H = 0.05      # Sterile threshold
theta_TD = 0.03     # Directional tension threshold
theta_RL = 3.0      # Accumulation trigger (CST-Lazy)
epsilon = 0.25      # Functional equivalence tolerance
r_cycles = 3        # Consecutive cycle intervention window
```

## Performance

### Timing

- **Per-game analysis**: ~0.5s (random vs random), ~0.08s (greedy vs greedy)
- **Batch (50 games)**: ~10–18s total
- **Serial execution**: Optimal (multiprocessing overhead exceeds benefits for this workload)

### Memory

- **Per game**: ~5–10 MB (board history + metrics)
- **Batch buffer**: O(n_moves) for feature storage

## Testing Strategy

### Unit Tests (Planned)

- Feature extraction validation
- LH computation against known positions
- Loop detection correctness
- Topology classification boundary cases

### Integration Tests

- End-to-end analysis workflow
- Null model permutation testing
- Cross-policy comparison consistency

### Validation

- Chess: 7 matchups, 500 permutations each, statistical significance (p<0.0001)
- Sokoban: 50 puzzles, 300 permutations, effect size validation
- Stagnation Grid: Stratification consistency (Δr = 0.000)

## Extension Points

### Adding a New Domain

1. Subclass `Game` in `game.py`
2. Implement required methods (state transition, terminal check, etc.)
3. Create domain-specific `DomainLoopHealthEngine`
4. Implement feature extractor for domain-specific metrics
5. Create `domains/{domain}/` directory with demos

### Tuning LHConfig

- Adjust weights `w1–w7` based on domain characteristics
- Modify thresholds `theta_H`, `theta_TD` for sensitivity
- Calibrate epsilon for functional equivalence tolerance

### Performance Optimization

- Cythonize critical loops (feature extraction, hash matching)
- Batch GPU acceleration for large policy sets
- Approximate null model via sampling (reduce permutations)

## References

- **Paper**: "Adaptive Loop-Breaking Protocol for Deterministic Self-Play"
  - Full formal definitions
  - Experimental methodology
  - Statistical validation
  
- **Games**: Chess (python-chess), Sokoban (custom implementation)

- **Algorithms**:
  - Permutation testing: standard statistical methodology
  - Loop detection: hash-based exact matching
  - Topology classification: weighted productivity measure

---

**Last Updated**: May 2025
**Version**: 1.0.0
**Status**: Production-ready for Chess domain, extensible to other games
