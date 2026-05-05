"""
loop_health.py — Loop Health Engine

Implements the core metrics from Sections 4–6 of the paper:

  SP(h_t, a_t)  — strategic productivity of a single transition
  LH(t)         — Loop Health of a repetitive cycle
  MP(C_k)       — marginal productivity across successive cycles
  PT(L)         — Productivity Transformer → Cycle / Spring / Tube

Also implements:
  - exact repetition detection   (Definition 1)
  - functional repetition detection  (Definition 2, tolerance ε)
  - candidate loop identification    (Definition 4)
  - repetition liability per player  (paper §5.2)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

import numpy as np

from game import GridPursuitGame, State
from features import FeatureExtractor

# ── Configuration ──────────────────────────────────────────────────────────

@dataclass
class LHConfig:
    """
    Weights w_i for the Loop Health formula (paper §5, unified 7-term form):

      LH(t) = w1·I + w2·T + w3·P + w4·E + w5·R + w6·A – w7·S

    and thresholds for classification.
    """
    w1: float = 0.15   # information gain
    w2: float = 0.25   # threat change  (distance closure)
    w3: float = 0.20   # progress
    w4: float = 0.15   # evaluation shift
    w5: float = 0.05   # irreversibility
    w6: float = 0.10   # asymmetry change
    w7: float = 0.10   # stagnation penalty

    theta_H:   float = 0.05   # LH threshold (productive vs sterile)
    theta_TD:  float = 0.03   # directional tension threshold (Spring vs Tube)
    epsilon:   float = 0.25   # functional equivalence tolerance
    r_cycles:  int   = 3      # consecutive sterile cycles before intervention
    theta_RL:  float = 3.0    # repetition liability threshold


# ── Per-transition metrics ─────────────────────────────────────────────────

@dataclass
class TransitionMetrics:
    """All SP components for a single transition (h_t, a_t, s_{t+1})."""
    info_gain:       float = 0.0   # I(t)
    threat_change:   float = 0.0   # T(t)  — positive: predator closing
    progress:        float = 0.0   # P(t)
    eval_shift:      float = 0.0   # E(t)
    irreversibility: float = 0.0   # R(t)
    asymmetry_change:float = 0.0   # A(t)
    stagnation:      float = 0.0   # S(t)

    # Derived
    sp:  float = 0.0   # strategic productivity
    lh:  float = 0.0   # Loop Health contribution

    # For Tube detection
    degrees_of_freedom: int   = 4
    td:                 float = 0.0   # directional tension


# ── Loop record ────────────────────────────────────────────────────────────

@dataclass
class LoopRecord:
    """One detected repetitive cycle in a game history."""
    start_step:    int
    end_step:      int
    loop_type:     str           # 'exact' or 'functional'
    topology:      str           # 'Cycle' / 'Spring' / 'Tube'
    avg_lh:        float
    avg_sp:        float
    marginal_prod: float         # MP(C_k) relative to previous cycle
    sustaining_player: int       # player who moved more in this loop
    metrics:       List[TransitionMetrics] = field(default_factory=list)


# ── Engine ─────────────────────────────────────────────────────────────────

class LoopHealthEngine:
    """
    Analyses a complete game history and returns:
      - per-transition SP and LH values
      - detected loop records with Cycle / Spring / Tube classification
      - repetition liability per player
      - aggregate statistics
    """

    def __init__(self, game: GridPursuitGame, config: Optional[LHConfig] = None):
        self.game     = game
        self.cfg      = config or LHConfig()
        self.features = FeatureExtractor(game)

    # ── Public interface ──────────────────────────────────────────────────

    def analyse(
        self,
        history: List[State],
        actions: List[str],
    ) -> Dict:
        """
        Main entry point.  Feed in the full list of states and actions from
        one game.  Returns a dict with all computed metrics.
        """
        assert len(actions) == len(history) - 1, \
            "len(actions) must equal len(history) - 1"

        phi_history: List[np.ndarray] = []
        metrics_list: List[TransitionMetrics] = []
        state_seen:  Dict[State, int] = {}        # exact repetition
        feature_seen: List[Tuple[int, np.ndarray]] = []  # functional

        exact_loops:      List[LoopRecord] = []
        functional_loops: List[LoopRecord] = []
        rl: Dict[int, float] = {0: 0.0, 1: 0.0}  # repetition liability

        prev_metrics: Optional[TransitionMetrics] = None

        for t, (state, action) in enumerate(zip(history[:-1], actions)):
            next_state = history[t + 1]

            phi_t = self.features.extract(state, history[:t])
            phi_history.append(phi_t)

            m = self._transition_metrics(
                state, action, next_state,
                history[:t], phi_history, t
            )
            m.sp  = self._sp(m)
            m.lh  = self._lh(m)
            m.td  = self._td(m, phi_history, t)
            metrics_list.append(m)

            # ── Exact repetition detection (Definition 1) ─────────────
            state_key = State(state.predator, state.prey, state.turn, 0)
            if state_key in state_seen:
                i = state_seen[state_key]
                loop_ms = metrics_list[i:t+1]
                rec = self._make_loop_record(
                    i, t, 'exact', loop_ms, prev_metrics
                )
                exact_loops.append(rec)
                rl = self._update_rl(rl, m, state, history[:t])
            else:
                state_seen[state_key] = t

            # ── Functional repetition detection (Definition 2) ────────
            phi_t_curr = self.features.extract(state, history[:t])
            for prev_t, phi_prev in feature_seen:
                d = self.features.functional_distance(phi_t_curr, phi_prev)
                if d <= self.cfg.epsilon:
                    loop_ms = metrics_list[prev_t:t+1]
                    rec = self._make_loop_record(
                        prev_t, t, 'functional', loop_ms, prev_metrics
                    )
                    functional_loops.append(rec)
                    rl = self._update_rl(rl, m, state, history[:t])
                    break
            feature_seen.append((t, phi_t_curr))

            prev_metrics = m

        all_loops = exact_loops + functional_loops
        return {
            "metrics":          metrics_list,
            "exact_loops":      exact_loops,
            "functional_loops": functional_loops,
            "all_loops":        all_loops,
            "repetition_liability": rl,
            "summary":          self._summary(metrics_list, all_loops, rl),
        }

    # ── Transition metrics ─────────────────────────────────────────────────

    def _transition_metrics(
        self,
        state:      State,
        action:     str,
        next_state: State,
        history:    List[State],
        phi_history: List[np.ndarray],
        t:          int,
    ) -> TransitionMetrics:
        g   = self.game
        cfg = self.cfg
        m   = TransitionMetrics()

        dist_before = g.manhattan_distance(state)
        dist_after  = g.manhattan_distance(next_state)

        # I(t) — information gain: change in move-option entropy
        pred_s_b = State(state.predator,      state.prey, 0, state.step)
        pred_s_a = State(next_state.predator, next_state.prey, 0, next_state.step)
        prey_s_b = State(state.predator,      state.prey, 1, state.step)
        prey_s_a = State(next_state.predator, next_state.prey, 1, next_state.step)

        ent_before = self._entropy_of_moves(g.legal_moves(pred_s_b)) + \
                     self._entropy_of_moves(g.legal_moves(prey_s_b))
        ent_after  = self._entropy_of_moves(g.legal_moves(pred_s_a)) + \
                     self._entropy_of_moves(g.legal_moves(prey_s_a))
        m.info_gain = abs(ent_after - ent_before) / (math.log2(4) * 2 + 1e-9)

        # T(t) — threat change: positive means predator getting closer
        m.threat_change = max(0.0, (dist_before - dist_after) / g.max_distance())

        # P(t) — progress (same as threat change in pure pursuit game)
        m.progress = m.threat_change

        # E(t) — evaluation shift (simple heuristic: normalised distance change)
        m.eval_shift = abs(dist_before - dist_after) / g.max_distance()

        # R(t) — irreversibility (0 in pure grid pursuit; extend for richer games)
        m.irreversibility = 0.0

        # A(t) — asymmetry change: change in mobility ratio
        mob_before = len(g.legal_moves(prey_s_b)) / (len(g.legal_moves(pred_s_b)) + 1)
        mob_after  = len(g.legal_moves(prey_s_a)) / (len(g.legal_moves(pred_s_a)) + 1)
        m.asymmetry_change = abs(mob_after - mob_before)

        # S(t) — stagnation: 1 if distance unchanged and no asymmetry change
        m.stagnation = 1.0 if (dist_before == dist_after
                               and m.asymmetry_change < 0.01) else 0.0

        # Degrees of freedom (prey legal moves — proxy for positional freedom)
        m.degrees_of_freedom = len(g.legal_moves(prey_s_a))

        return m

    # ── SP and LH formulas ────────────────────────────────────────────────

    def _sp(self, m: TransitionMetrics) -> float:
        """
        SP(h_t, a_t) = β1·IG + β2·Prog + β3·ΔThreat + β4·ΔOptions + β5·Irrev
        (paper §4, unified with LH weights for this single-game setting)
        """
        cfg = self.cfg
        return (cfg.w1 * m.info_gain
                + cfg.w3 * m.progress
                + cfg.w2 * m.threat_change
                + cfg.w6 * m.asymmetry_change
                + cfg.w5 * m.irreversibility)

    def _lh(self, m: TransitionMetrics) -> float:
        """
        LH(t) = w1·I + w2·T + w3·P + w4·E + w5·R + w6·A − w7·S
        (paper §5, unified 7-term formula)
        """
        cfg = self.cfg
        return (cfg.w1 * m.info_gain
                + cfg.w2 * m.threat_change
                + cfg.w3 * m.progress
                + cfg.w4 * m.eval_shift
                + cfg.w5 * m.irreversibility
                + cfg.w6 * m.asymmetry_change
                - cfg.w7 * m.stagnation)

    def _td(
        self,
        m:           TransitionMetrics,
        phi_history: List[np.ndarray],
        t:           int,
    ) -> float:
        """
        Directional tension TD: how consistently the feature vector is moving
        in the same direction over the last few steps.
        High TD → Tube topology.
        """
        window = 4
        if len(phi_history) < window + 1:
            return 0.0
        deltas = [phi_history[i+1] - phi_history[i]
                  for i in range(len(phi_history) - window - 1,
                                 len(phi_history) - 1)]
        if not deltas:
            return 0.0
        mean_delta = np.mean(deltas, axis=0)
        # Cosine similarity between successive deltas → high = consistent direction
        sims = []
        for d in deltas:
            n1 = np.linalg.norm(mean_delta) + 1e-9
            n2 = np.linalg.norm(d) + 1e-9
            sims.append(float(np.dot(mean_delta, d) / (n1 * n2)))
        return max(0.0, float(np.mean(sims)))

    # ── Topology classification ────────────────────────────────────────────

    def _classify(self, avg_lh: float, avg_td: float) -> str:
        """
        PT(L) → 'Cycle' / 'Spring' / 'Tube'  (paper §6, Productivity Transformer)
        """
        if avg_lh <= self.cfg.theta_H:
            return "Cycle"
        if avg_td > self.cfg.theta_TD:
            return "Tube"
        return "Spring"

    # ── Loop record builder ───────────────────────────────────────────────

    def _make_loop_record(
        self,
        start:        int,
        end:          int,
        loop_type:    str,
        loop_metrics: List[TransitionMetrics],
        prev_metrics: Optional[TransitionMetrics],
    ) -> LoopRecord:
        if not loop_metrics:
            return LoopRecord(start, end, loop_type, "Cycle",
                              0.0, 0.0, 0.0, 0)
        avg_lh = float(np.mean([m.lh for m in loop_metrics]))
        avg_sp = float(np.mean([m.sp for m in loop_metrics]))
        avg_td = float(np.mean([m.td for m in loop_metrics]))
        topology = self._classify(avg_lh, avg_td)

        # Marginal productivity MP(C_k)
        mp = avg_sp - (prev_metrics.sp if prev_metrics else avg_sp)

        # Which player moved most in this cycle
        steps_p0 = sum(1 for m in loop_metrics if True)  # simplified
        sustaining = 0

        return LoopRecord(
            start_step=start,
            end_step=end,
            loop_type=loop_type,
            topology=topology,
            avg_lh=avg_lh,
            avg_sp=avg_sp,
            marginal_prod=mp,
            sustaining_player=sustaining,
            metrics=loop_metrics,
        )

    # ── Repetition liability update ───────────────────────────────────────

    def _update_rl(
        self,
        rl:      Dict[int, float],
        m:       TransitionMetrics,
        state:   State,
        history: List[State],
    ) -> Dict[int, float]:
        """Update RL_n (paper §5.2)."""
        player = state.turn
        if m.sp <= self.cfg.theta_H:
            rl[player] = rl.get(player, 0.0) + 1.0
        else:
            rl[player] = max(0.0, rl.get(player, 0.0) - 0.5)
        return rl

    # ── Helper: entropy ───────────────────────────────────────────────────

    @staticmethod
    def _entropy_of_moves(moves: list) -> float:
        n = len(moves)
        if n <= 1:
            return 0.0
        p = 1.0 / n
        return -n * p * math.log2(p)

    # ── Summary statistics ────────────────────────────────────────────────

    def _summary(
        self,
        metrics:  List[TransitionMetrics],
        loops:    List[LoopRecord],
        rl:       Dict[int, float],
    ) -> Dict:
        if not metrics:
            return {}

        lh_vals = [m.lh for m in metrics]
        sp_vals = [m.sp for m in metrics]

        topologies = [l.topology for l in loops] if loops else []
        n_loops    = len(loops)

        return {
            "n_transitions":     len(metrics),
            "n_loops":           n_loops,
            "n_exact":           sum(1 for l in loops if l.loop_type == "exact"),
            "n_functional":      sum(1 for l in loops if l.loop_type == "functional"),
            "mean_lh":           float(np.mean(lh_vals)),
            "std_lh":            float(np.std(lh_vals)),
            "productive_pct":    float(np.mean([v > self.cfg.theta_H
                                                for v in lh_vals])) * 100,
            "sterile_pct":       float(np.mean([v <= self.cfg.theta_H
                                                for v in lh_vals])) * 100,
            "mean_sp":           float(np.mean(sp_vals)),
            "mean_stagnation":   float(np.mean([m.stagnation for m in metrics])),
            "cycle_pct":         topologies.count("Cycle") / max(n_loops,1) * 100,
            "spring_pct":        topologies.count("Spring") / max(n_loops,1) * 100,
            "tube_pct":          topologies.count("Tube") / max(n_loops,1) * 100,
            "repetition_liability": rl,
        }
