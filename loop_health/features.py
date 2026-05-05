"""
features.py — Strategic Feature Map

Implements the strategic feature map  Φ: S × H → F  (Definition 2, paper §3)
and the pseudo-distance  d_F: F × F → ℝ≥0  used for functional repetition
detection (Definition 2, paper §4).

Feature vector components (dim = 10):
  [0]  Normalised Manhattan distance
  [1]  Predator legal-move count  (normalised)
  [2]  Prey    legal-move count  (normalised)
  [3]  Mobility ratio  prey / (pred + 1)   — strategic asymmetry proxy
  [4]  Predator row   (normalised)
  [5]  Predator col   (normalised)
  [6]  Prey    row   (normalised)
  [7]  Prey    col   (normalised)
  [8]  Distance trend  (+: predator closing, -: predator retreating)
  [9]  Relative bearing (angle predator→prey, normalised to [-1, 1])
"""

from __future__ import annotations
import math
from typing import List

import numpy as np

from .game import GridPursuitGame, State

FEATURE_DIM = 10


class FeatureExtractor:
    """
    Computes Φ(s_t, h_t) for any state in a GridPursuitGame.
    The history h_t is represented as the list of prior states.
    """

    def __init__(self, game: GridPursuitGame):
        self.game    = game
        self._maxd   = game.max_distance()
        self._max_mv = 4.0   # max legal moves on an open grid

    def extract(self, state: State, history: List[State]) -> np.ndarray:
        """Return the feature vector Φ(s_t, h_t) as a numpy array."""
        g = self.game

        dist = g.manhattan_distance(state)

        # Legal-move counts for each player (using helper states)
        pred_s = State(state.predator, state.prey, 0, state.step)
        prey_s = State(state.predator, state.prey, 1, state.step)
        pred_moves = len(g.legal_moves(pred_s))
        prey_moves  = len(g.legal_moves(prey_s))

        # Distance trend: positive means predator is closing
        if len(history) >= 1:
            prev_dist = g.manhattan_distance(history[-1])
            trend = (prev_dist - dist) / self._maxd
        else:
            trend = 0.0

        # Bearing from predator to prey (normalised angle)
        dr = state.prey[0] - state.predator[0]
        dc = state.prey[1] - state.predator[1]
        bearing = math.atan2(dr, dc) / math.pi   # ∈ [-1, 1]

        return np.array([
            dist          / self._maxd,          # [0] distance
            pred_moves    / self._max_mv,         # [1] predator mobility
            prey_moves    / self._max_mv,         # [2] prey mobility
            prey_moves    / (pred_moves + 1),     # [3] asymmetry
            state.predator[0] / (g.rows - 1),    # [4] pred row
            state.predator[1] / (g.cols - 1),    # [5] pred col
            state.prey[0]     / (g.rows - 1),    # [6] prey row
            state.prey[1]     / (g.cols - 1),    # [7] prey col
            trend,                                # [8] distance trend
            bearing,                              # [9] bearing
        ], dtype=float)

    @staticmethod
    def functional_distance(phi1: np.ndarray, phi2: np.ndarray) -> float:
        """
        d_F(Φ1, Φ2): Euclidean distance in feature space.
        Used in Definition 2 (functional repetition detection).
        """
        return float(np.linalg.norm(phi1 - phi2))
