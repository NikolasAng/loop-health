"""
chess_engine.py — Loop Health Engine for Chess

LH component mapping:
  I(t)   = change in legal-move entropy (branching factor shift)
  Thr(t) = increase in king-attacker count for the side to move
  P(t)   = material gain for the moving side (captures)
  E(t)   = |material_balance_after - material_balance_before|
  R(t)   = 1 if capture / pawn move / castling / promotion, else 0
  A(t)   = change in mobility ratio (white_mobility / black_mobility)
  S(t)   = 1 if no capture AND no pawn move AND material unchanged
             (= 50-move clock territory)

Key theoretical claim validated here:
  S(t) = 1 for N consecutive steps  ≡  50-move rule clock ticking
  LH(t) <= theta_H for N steps      →  CST-Lazy Break subsumes the 50-move rule
"""

from __future__ import annotations
import math
from typing import List, Dict, Optional

import numpy as np
import chess

from .chess_game import ChessGame
from .loop_health import LHConfig, TransitionMetrics, LoopRecord


class ChessLoopHealthEngine:

    def __init__(self, game: ChessGame, config: Optional[LHConfig] = None):
        self.game = game
        self.cfg  = config or LHConfig()

    # ── Public ────────────────────────────────────────────────────────────

    def analyse(self, history: List[chess.Board], moves: List[chess.Move]) -> Dict:
        assert len(moves) == len(history) - 1

        phi_history:      List[np.ndarray]        = []
        metrics_list:     List[TransitionMetrics] = []
        state_seen:       Dict[str, int]          = {}
        feature_seen:     List[tuple]             = []
        exact_loops:      List[LoopRecord]        = []
        functional_loops: List[LoopRecord]        = []
        rl:   Dict[int, float] = {0: 0.0, 1: 0.0}
        prev: Optional[TransitionMetrics] = None

        for t, (board, move) in enumerate(zip(history[:-1], moves)):
            nxt = history[t + 1]
            phi = self._extract(board)
            phi_history.append(phi)

            m = self._transition_metrics(board, move, nxt)
            m.sp = self._sp(m)
            m.lh = self._lh(m)
            m.td = self._td(phi_history, t)
            metrics_list.append(m)

            # Exact repetition: FEN without move counters
            key = self.game.state_key(board)
            if key in state_seen:
                i = state_seen[key]
                rec = self._make_loop(i, t, "exact", metrics_list[i:t+1], prev)
                exact_loops.append(rec)
                rl = self._update_rl(rl, m, board)
            else:
                state_seen[key] = t

            # Functional repetition
            phi_c = self._extract(board)
            for pt, pp in feature_seen:
                if float(np.linalg.norm(phi_c - pp)) <= self.cfg.epsilon:
                    rec = self._make_loop(pt, t, "functional", metrics_list[pt:t+1], prev)
                    functional_loops.append(rec)
                    rl = self._update_rl(rl, m, board)
                    break
            feature_seen.append((t, phi_c))
            prev = m

        all_loops = exact_loops + functional_loops
        return {
            "metrics":              metrics_list,
            "exact_loops":          exact_loops,
            "functional_loops":     functional_loops,
            "all_loops":            all_loops,
            "repetition_liability": rl,
            "summary":              self._summary(metrics_list, all_loops, rl),
        }

    # ── Feature extraction ────────────────────────────────────────────────

    def _extract(self, board: chess.Board) -> np.ndarray:
        g = self.game
        mat_w   = g.material(board, chess.WHITE) / 39.0
        mat_b   = g.material(board, chess.BLACK) / 39.0
        mat_diff = g.material_balance(board)
        mob_w   = g.mobility(board, chess.WHITE) / 40.0
        mob_b   = g.mobility(board, chess.BLACK) / 40.0
        mob_r   = mob_w / (mob_b + 1e-9)
        ka_w    = g.king_attackers(board, chess.WHITE) / 8.0
        ka_b    = g.king_attackers(board, chess.BLACK) / 8.0
        pa_w    = g.pawn_advancement(board, chess.WHITE)
        pa_b    = g.pawn_advancement(board, chess.BLACK)
        endgame = 1.0 if g.total_material(board) < 15.0 else 0.0
        hm_norm = board.halfmove_clock / 100.0   # 50-move rule clock
        turn    = float(board.turn)               # WHITE=True=1.0

        return np.array([
            mat_w, mat_b, mat_diff,      # [0-2] material
            mob_w, mob_b, mob_r,         # [3-5] mobility
            ka_w,  ka_b,                 # [6-7] king safety
            pa_w,  pa_b,                 # [8-9] pawn structure
            endgame,                     # [10]  game phase
            hm_norm,                     # [11]  50-move clock (sterility proxy)
            turn,                        # [12]  side to move
        ], dtype=float)

    # ── Transition metrics ────────────────────────────────────────────────

    def _transition_metrics(
        self, board: chess.Board, move: chess.Move, nxt: chess.Board
    ) -> TransitionMetrics:
        g = self.game
        m = TransitionMetrics()

        # R(t): irreversibility
        m.irreversibility = 1.0 if g.is_irreversible(board, move) else 0.0

        # Material before/after
        mat_b_w = g.material(board, chess.WHITE)
        mat_b_b = g.material(board, chess.BLACK)
        mat_a_w = g.material(nxt, chess.WHITE)
        mat_a_b = g.material(nxt, chess.BLACK)
        total_before = mat_b_w + mat_b_b
        total_after  = mat_a_w + mat_a_b

        # P(t): material gain for the side that just moved
        if board.turn == chess.WHITE:
            gain = (mat_a_w - mat_b_w) - (mat_a_b - mat_b_b)
        else:
            gain = (mat_a_b - mat_b_b) - (mat_a_w - mat_b_w)
        m.progress = max(0.0, gain / 9.0)  # normalise by queen value

        # E(t): evaluation shift (material balance change)
        bal_b = g.material_balance(board)
        bal_a = g.material_balance(nxt)
        m.eval_shift = abs(bal_a - bal_b)

        # Thr(t): increase in attacks on the opponent's king
        if board.turn == chess.WHITE:
            ka_b = g.king_attackers(board, chess.BLACK)
            ka_a = g.king_attackers(nxt,   chess.BLACK)
        else:
            ka_b = g.king_attackers(board, chess.WHITE)
            ka_a = g.king_attackers(nxt,   chess.WHITE)
        m.threat_change = max(0.0, (ka_a - ka_b) / 8.0)

        # I(t): change in legal-move entropy
        ent_b = self._ent(len(list(board.legal_moves)))
        ent_a = self._ent(len(list(nxt.legal_moves)))
        m.info_gain = abs(ent_a - ent_b) / (math.log2(40) + 1e-9)

        # A(t): mobility ratio change
        mob_w_b = g.mobility(board, chess.WHITE)
        mob_b_b = g.mobility(board, chess.BLACK)
        mob_w_a = g.mobility(nxt,   chess.WHITE)
        mob_b_a = g.mobility(nxt,   chess.BLACK)
        ratio_b = mob_w_b / (mob_b_b + 1)
        ratio_a = mob_w_a / (mob_b_a + 1)
        m.asymmetry_change = abs(ratio_a - ratio_b) / 5.0

        # S(t): stagnation — no capture, no pawn move, no material change
        no_capture = not board.is_capture(move)
        no_pawn    = board.piece_type_at(move.from_square) != chess.PAWN
        no_mat     = abs(total_after - total_before) < 0.01
        m.stagnation = 1.0 if (no_capture and no_pawn and no_mat) else 0.0

        m.degrees_of_freedom = len(list(nxt.legal_moves))
        return m

    # ── SP / LH / TD ─────────────────────────────────────────────────────

    def _sp(self, m: TransitionMetrics) -> float:
        c = self.cfg
        return (c.w1*m.info_gain + c.w3*m.progress + c.w2*m.threat_change
                + c.w6*m.asymmetry_change + c.w5*m.irreversibility)

    def _lh(self, m: TransitionMetrics) -> float:
        c = self.cfg
        return (c.w1*m.info_gain + c.w2*m.threat_change + c.w3*m.progress
                + c.w4*m.eval_shift + c.w5*m.irreversibility
                + c.w6*m.asymmetry_change - c.w7*m.stagnation)

    def _td(self, phi_history: List[np.ndarray], t: int) -> float:
        window = 4
        if len(phi_history) < window + 1:
            return 0.0
        deltas = [phi_history[i+1] - phi_history[i]
                  for i in range(len(phi_history)-window-1, len(phi_history)-1)]
        if not deltas:
            return 0.0
        mean_d = np.mean(deltas, axis=0)
        sims = [float(np.dot(mean_d, d) / (np.linalg.norm(mean_d)*np.linalg.norm(d)+1e-9))
                for d in deltas]
        return max(0.0, float(np.mean(sims)))

    def _classify(self, avg_lh: float, avg_td: float) -> str:
        if avg_lh <= self.cfg.theta_H: return "Cycle"
        if avg_td > self.cfg.theta_TD: return "Tube"
        return "Spring"

    def _make_loop(self, start, end, ltype, loop_ms, prev):
        if not loop_ms:
            return LoopRecord(start, end, ltype, "Cycle", 0.0, 0.0, 0.0, 0)
        avg_lh = float(np.mean([m.lh for m in loop_ms]))
        avg_sp = float(np.mean([m.sp for m in loop_ms]))
        avg_td = float(np.mean([m.td for m in loop_ms]))
        topo   = self._classify(avg_lh, avg_td)
        mp     = avg_sp - (prev.sp if prev else avg_sp)
        return LoopRecord(start, end, ltype, topo, avg_lh, avg_sp, mp, 0, loop_ms)

    def _update_rl(self, rl, m, board):
        p = 0 if board.turn == chess.WHITE else 1
        if m.sp <= self.cfg.theta_H:
            rl[p] = rl.get(p, 0.0) + 1.0
        else:
            rl[p] = max(0.0, rl.get(p, 0.0) - 0.5)
        return rl

    @staticmethod
    def _ent(n: int) -> float:
        if n <= 1: return 0.0
        p = 1.0 / n
        return -n * p * math.log2(p)

    def _summary(self, metrics, loops, rl) -> Dict:
        if not metrics: return {}
        lh_v  = [m.lh for m in metrics]
        sp_v  = [m.sp for m in metrics]
        irr_v = [m.irreversibility for m in metrics]
        stag_v = [m.stagnation for m in metrics]
        tops  = [l.topology for l in loops]
        n_lp  = max(len(loops), 1)

        # Correlation: stagnation (50-move proxy) vs LH <= theta_H
        stag_arr  = np.array(stag_v)
        lh_arr    = np.array(lh_v)
        sterile   = (lh_arr <= self.cfg.theta_H).astype(float)
        corr      = float(np.corrcoef(stag_arr, sterile)[0, 1]) if len(stag_v) > 1 else 0.0

        # Circularity-free: same but using LH⁻ (without -w7·S term)
        lh_minus_v = [m.info_gain * self.cfg.w1
                      + m.threat_change   * self.cfg.w2
                      + m.progress        * self.cfg.w3
                      + m.eval_shift      * self.cfg.w4
                      + m.irreversibility * self.cfg.w5
                      + m.asymmetry_change* self.cfg.w6
                      for m in metrics]
        lh_minus_arr = np.array(lh_minus_v)
        sterile_minus = (lh_minus_arr <= self.cfg.theta_H).astype(float)
        corr_minus = (float(np.corrcoef(stag_arr, sterile_minus)[0, 1])
                      if len(stag_v) > 1 else 0.0)

        return {
            "n_transitions":          len(metrics),
            "n_loops":                len(loops),
            "mean_lh":                float(np.mean(lh_v)),
            "std_lh":                 float(np.std(lh_v)),
            "mean_sp":                float(np.mean(sp_v)),
            "productive_pct":         float(np.mean([v > self.cfg.theta_H for v in lh_v])) * 100,
            "sterile_pct":            float(np.mean([v <= self.cfg.theta_H for v in lh_v])) * 100,
            "irrev_pct":              float(np.mean([v > 0 for v in irr_v])) * 100,
            "mean_stagnation":        float(np.mean(stag_v)),
            "stagnation_lh_corr":       corr,
            "stagnation_lh_minus_corr": corr_minus,
            "cycle_pct":              tops.count("Cycle")  / n_lp * 100,
            "spring_pct":             tops.count("Spring") / n_lp * 100,
            "tube_pct":               tops.count("Tube")   / n_lp * 100,
            "repetition_liability":   rl,
        }
