"""
game.py — Grid Pursuit Game

Implements the formal model G = (N, S, s0, A, L, T, p, Z, o)
from Section 3 of the paper.

Players:
  0 = Predator  (wins by catching Prey)
  1 = Prey      (wins by surviving max_steps turns)

Board: rows x cols grid, no obstacles.
Moves: N / S / E / W (cardinal directions only).
Terminal:
  - Predator and Prey occupy the same cell  -> predator_wins
  - step count >= max_steps                 -> draw
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict

# ── Action definitions ─────────────────────────────────────────────────────
DIRECTIONS: Dict[str, Tuple[int, int]] = {
    "N": (-1,  0),
    "S": ( 1,  0),
    "E": ( 0,  1),
    "W": ( 0, -1),
}
ALL_ACTIONS: List[str] = list(DIRECTIONS.keys())


# ── State ──────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class State:
    """
    A single game state s ∈ S.
    Frozen + hashable so it can be stored in sets/dicts for repetition tracking.
    """
    predator: Tuple[int, int]   # (row, col)
    prey:     Tuple[int, int]   # (row, col)
    turn:     int               # 0 = predator, 1 = prey
    step:     int               # total half-moves played


# ── Game ───────────────────────────────────────────────────────────────────
class GridPursuitGame:
    """
    Deterministic two-player pursuit-evasion game on a grid.

    Corresponds directly to the formal tuple G = (N, S, s0, A, L, T, p, Z, o).
    """

    def __init__(self, rows: int = 6, cols: int = 6, max_steps: int = 120):
        self.rows      = rows
        self.cols      = cols
        self.max_steps = max_steps
        self.N         = (0, 1)   # player set

    # ── G components ──────────────────────────────────────────────────────

    def initial_state(
        self,
        predator_start: Tuple[int, int] = (0, 0),
        prey_start:     Tuple[int, int] = (5, 5),
    ) -> State:
        """s0 ∈ S: initial state."""
        return State(predator=predator_start, prey=prey_start, turn=0, step=0)

    def legal_moves(self, state: State) -> List[str]:
        """L(s) ⊆ A: legal actions for the active player."""
        pos = state.predator if state.turn == 0 else state.prey
        return [
            name
            for name, (dr, dc) in DIRECTIONS.items()
            if self._in_bounds(pos[0] + dr, pos[1] + dc)
        ]

    def transition(self, state: State, action: str) -> State:
        """T(s, a) → s': deterministic successor state."""
        dr, dc = DIRECTIONS[action]
        if state.turn == 0:
            new_pred = (state.predator[0] + dr, state.predator[1] + dc)
            return State(predator=new_pred, prey=state.prey,
                         turn=1, step=state.step + 1)
        else:
            new_prey = (state.prey[0] + dr, state.prey[1] + dc)
            return State(predator=state.predator, prey=new_prey,
                         turn=0, step=state.step + 1)

    def active_player(self, state: State) -> int:
        """p(s) ∈ N: which player acts at state s."""
        return state.turn

    def is_terminal(self, state: State) -> bool:
        """s ∈ Z: whether state is terminal."""
        return state.predator == state.prey or state.step >= self.max_steps

    def outcome(self, state: State) -> Optional[str]:
        """o(s): outcome at a terminal state; None if non-terminal."""
        if not self.is_terminal(state):
            return None
        if state.predator == state.prey:
            return "predator_wins"
        return "draw"

    # ── Utility ───────────────────────────────────────────────────────────

    def manhattan_distance(self, state: State) -> int:
        """Manhattan distance between Predator and Prey."""
        return (abs(state.predator[0] - state.prey[0])
                + abs(state.predator[1] - state.prey[1]))

    def max_distance(self) -> int:
        """Maximum possible Manhattan distance on this board."""
        return (self.rows - 1) + (self.cols - 1)

    def _in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols
