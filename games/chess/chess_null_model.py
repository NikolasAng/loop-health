"""
chess_null_model.py — Permutation null model for Stagnation Convergence
========================================================================

Question: Is r(S(t), [LH≤θ_H]) meaningful, or could any random
classification of steps yield a similar correlation?

Procedure
─────────
1. Play the same games as chess_experiment.py (same policies, seed=42).
2. Collect per-game lists of (S, LH⁻, LH_full) — keeping game boundaries.
3. Compute r_real  = r(S, [LH_full ≤ θ_H])   across all steps.
         r_real⁻ = r(S, [LH⁻    ≤ θ_H])   (circularity-free).
4. For N_PERM permutations:
     • Shuffle S labels WITHIN each game (preserves per-game stagnation rate).
     • Compute r_null and r_null_minus on the shuffled S.
5. p-value = fraction of null r_null ≥ r_real  (one-tailed).
   Effect size = (r_real - mean(r_null)) / std(r_null).

Interpretation
─────────────
  p < 0.01  AND  effect_size >> 1  →  LH classification is non-trivial.
  p > 0.05  OR   effect_size ≈ 0   →  LH is no better than random labelling.

Usage:  python chess_null_model.py
"""

from __future__ import annotations

import random
import sys
import os
import math
from typing import List, Tuple

import numpy as np
import chess

sys.path.insert(0, os.path.dirname(__file__))
from chess_game   import ChessGame
from chess_engine import ChessLoopHealthEngine
from loop_health  import LHConfig

# ── Config ────────────────────────────────────────────────────────────────────
N_PERM   = 500    # permutation runs per matchup
SEED     = 42
THETA_H  = 0.05

MATCHUPS = [
    ("random",    "random",    30),
    ("greedy",    "greedy",    30),
    ("greedy",    "random",    30),
    ("defensive", "greedy",    30),
    ("minimax2",  "minimax2",  20),
    ("minimax3",  "minimax2",  20),
    ("minimax3",  "random",    20),
]

# ── Minimal policies (same as chess_experiment.py) ────────────────────────────
_PVAL = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
         chess.ROOK:  500, chess.QUEEN:  900, chess.KING:  0}

def _order_moves(board):
    captures, quiets = [], []
    for mv in board.legal_moves:
        if board.is_capture(mv):
            v = _PVAL.get(board.piece_type_at(mv.to_square),   0) or 0
            a = _PVAL.get(board.piece_type_at(mv.from_square), 0) or 0
            captures.append((v - a, mv))
        else:
            quiets.append(mv)
    captures.sort(key=lambda x: -x[0])
    return [mv for _, mv in captures] + quiets

def _evaluate(board):
    if board.is_checkmate():
        return -20000 if board.turn == chess.WHITE else 20000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    score = 0
    for pt, v in _PVAL.items():
        score += len(board.pieces(pt, chess.WHITE)) * v
        score -= len(board.pieces(pt, chess.BLACK)) * v
    score += board.pseudo_legal_moves.count() * (1 if board.turn == chess.WHITE else -1)
    return score

def _minimax(board, depth, alpha, beta):
    if depth == 0 or board.is_game_over():
        return _evaluate(board)
    if board.turn == chess.WHITE:
        best = -10**7
        for mv in _order_moves(board):
            board.push(mv)
            best = max(best, _minimax(board, depth - 1, alpha, beta))
            board.pop()
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    else:
        best = 10**7
        for mv in _order_moves(board):
            board.push(mv)
            best = min(best, _minimax(board, depth - 1, alpha, beta))
            board.pop()
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best

def _best_move(board, depth, rng):
    moves = _order_moves(board)
    if not moves:
        return None
    best_val = -10**7 if board.turn == chess.WHITE else 10**7
    best_mvs = []
    alpha, beta = -10**7, 10**7
    for mv in moves:
        board.push(mv)
        val = _minimax(board, depth - 1, alpha, beta)
        board.pop()
        if board.turn == chess.WHITE:
            if val > best_val:
                best_val, best_mvs = val, [mv]
            elif val == best_val:
                best_mvs.append(mv)
            alpha = max(alpha, best_val)
        else:
            if val < best_val:
                best_val, best_mvs = val, [mv]
            elif val == best_val:
                best_mvs.append(mv)
            beta = min(beta, best_val)
    return rng.choice(best_mvs)

def _pol_random(board, rng):
    mvs = list(board.legal_moves)
    return rng.choice(mvs) if mvs else None

def _pol_greedy(board, rng):
    mvs = list(board.legal_moves)
    if not mvs:
        return None
    caps = [(_PVAL.get(board.piece_type_at(m.to_square), 0) or 0, m)
            for m in mvs if board.is_capture(m)]
    return max(caps, key=lambda x: x[0])[1] if caps else rng.choice(mvs)

def _pol_defensive(board, rng):
    mvs = list(board.legal_moves)
    if not mvs:
        return None
    opp  = not board.turn
    safe = [m for m in mvs if not board.is_attacked_by(opp, m.to_square)]
    return rng.choice(safe if safe else mvs)

def _pol_minimax2(board, rng):
    return _best_move(board, 2, rng)

def _pol_minimax3(board, rng):
    return _best_move(board, 3, rng)

_POLICIES = {
    "random":    _pol_random,
    "greedy":    _pol_greedy,
    "defensive": _pol_defensive,
    "minimax2":  _pol_minimax2,
    "minimax3":  _pol_minimax3,
}

# ── Data collection ───────────────────────────────────────────────────────────

GameRecord = List[Tuple[float, float, float]]  # (S, lh_minus, lh_full) per step

def collect_games(pol0_name: str, pol1_name: str, n_games: int,
                  engine: ChessLoopHealthEngine, cfg: LHConfig,
                  rng: random.Random) -> List[GameRecord]:
    """Return one GameRecord per game (step-level (S, LH⁻, LH_full) tuples)."""
    pol0, pol1 = _POLICIES[pol0_name], _POLICIES[pol1_name]
    all_games: List[GameRecord] = []

    for _ in range(n_games):
        board  = chess.Board()
        boards = [board.copy()]
        moves: List[chess.Move] = []
        step = 0
        while not board.is_game_over() and step < 200:
            fn = pol0 if board.turn == chess.WHITE else pol1
            mv = fn(board, rng)
            if mv is None:
                break
            moves.append(mv)
            board.push(mv)
            boards.append(board.copy())
            step += 1

        if len(boards) < 2 or not moves:
            continue

        result  = engine.analyse(boards, moves)
        metrics = result["metrics"]
        game_rec: GameRecord = []
        for m in metrics:
            lh_minus = (cfg.w1 * m.info_gain
                        + cfg.w2 * m.threat_change
                        + cfg.w3 * m.progress
                        + cfg.w4 * m.eval_shift
                        + cfg.w5 * m.irreversibility
                        + cfg.w6 * m.asymmetry_change)
            lh_full  = lh_minus - cfg.w7 * m.stagnation
            game_rec.append((m.stagnation, lh_minus, lh_full))
        if game_rec:
            all_games.append(game_rec)

    return all_games

# ── Correlation ───────────────────────────────────────────────────────────────

def corr(x, y) -> float:
    x, y = np.array(x, dtype=float), np.array(y, dtype=float)
    if x.std() < 1e-10 or y.std() < 1e-10:
        return float('nan')
    return float(np.corrcoef(x, y)[0, 1])

def compute_r(games: List[GameRecord],
              s_override: List[List[float]] | None = None):
    """
    Compute r_full and r_minus across all steps.
    If s_override is provided, use those S values instead of the real ones.
    """
    s_vals, lh_full_ind, lh_minus_ind = [], [], []
    for gi, game in enumerate(games):
        for ti, (s, lm, lf) in enumerate(game):
            sv = s_override[gi][ti] if s_override is not None else s
            s_vals.append(sv)
            lh_full_ind.append(1.0 if lf <= THETA_H else 0.0)
            lh_minus_ind.append(1.0 if lm <= THETA_H else 0.0)
    return corr(s_vals, lh_full_ind), corr(s_vals, lh_minus_ind)

# ── Permutation test ──────────────────────────────────────────────────────────

def permutation_test(games: List[GameRecord],
                     r_real: float, r_real_minus: float,
                     n_perm: int, rng: random.Random):
    """
    Shuffle S within each game N_PERM times, collect null distribution.
    Returns (null_r_full list, null_r_minus list).
    """
    null_full, null_minus = [], []
    for _ in range(n_perm):
        s_shuffled = []
        for game in games:
            s_game = [step[0] for step in game]
            rng.shuffle(s_game)
            s_shuffled.append(s_game)
        rf, rm = compute_r(games, s_shuffled)
        if not math.isnan(rf):
            null_full.append(rf)
        if not math.isnan(rm):
            null_minus.append(rm)
    return null_full, null_minus

def summarise_null(r_real: float, null_dist: List[float], label: str):
    if not null_dist or math.isnan(r_real):
        return f"  {label}: r_real={r_real:+.4f}  [no null data]"
    arr = np.array(null_dist)
    mu, sd = float(arr.mean()), float(arr.std())
    p_val  = float(np.mean(arr >= r_real))   # fraction of nulls ≥ r_real
    effect = (r_real - mu) / sd if sd > 1e-10 else float('inf')
    sig    = "***" if p_val < 0.001 else ("**" if p_val < 0.01
              else ("*" if p_val < 0.05 else "ns"))
    return (f"  {label}:\n"
            f"    r_real   = {r_real:+.4f}\n"
            f"    null μ±σ = {mu:+.4f} ± {sd:.4f}  "
            f"[min={arr.min():+.4f}  max={arr.max():+.4f}]\n"
            f"    p-value  = {p_val:.4f}  {sig}\n"
            f"    effect   = {effect:+.2f}σ  "
            f"({'SIGNAL' if p_val < 0.05 else 'no signal'})")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    game_obj = ChessGame(max_steps=200)
    cfg      = LHConfig()
    engine   = ChessLoopHealthEngine(game_obj, cfg)
    rng_data = random.Random(SEED)    # for gameplay (same as chess_experiment)
    rng_perm = random.Random(SEED + 1)  # separate seed for permutations

    print("\n" + "=" * 72)
    print("  Chess — Null Model Permutation Test for Stagnation Convergence")
    print(f"  N_PERM={N_PERM}  seed={SEED}  theta_H={THETA_H}")
    print("  Null: shuffle S(t) labels WITHIN each game (preserves stagnation rate)")
    print("=" * 72)

    summary_rows = []

    for pol0, pol1, n_games in MATCHUPS:
        label = f"{pol0} vs {pol1}"
        print(f"\n{'─'*60}")
        print(f"  Matchup: {label}  ({n_games} games)")

        games = collect_games(pol0, pol1, n_games, engine, cfg, rng_data)
        total_steps = sum(len(g) for g in games)
        n_stag      = sum(s > 0.5 for g in games for s, _, _ in g)
        print(f"  Steps collected: {total_steps:,}  "
              f"(S=1: {n_stag:,}, {100*n_stag/max(total_steps,1):.1f}%)")

        r_real, r_real_minus = compute_r(games)
        print(f"\n  Real correlations:")
        print(f"    r(S, [LH_full ≤ θ_H])  = {r_real:+.4f}")
        print(f"    r(S, [LH⁻    ≤ θ_H])  = {r_real_minus:+.4f}  (circularity-free)")

        print(f"\n  Running {N_PERM} permutations ...", end=" ", flush=True)
        null_full, null_minus = permutation_test(
            games, r_real, r_real_minus, N_PERM, rng_perm)
        print("done")

        print()
        print(summarise_null(r_real, null_full,  "Full LH  [LH_full ≤ θ_H]"))
        print()
        print(summarise_null(r_real_minus, null_minus, "LH⁻ (circ-free) [LH⁻ ≤ θ_H]"))

        # Collect for summary table
        null_arr = np.array(null_full) if null_full else np.array([float('nan')])
        p_full   = float(np.mean(null_arr >= r_real)) if null_full else float('nan')
        eff_full = ((r_real - null_arr.mean()) / null_arr.std()
                    if null_full and null_arr.std() > 1e-10 else float('nan'))
        null_m   = np.array(null_minus) if null_minus else np.array([float('nan')])
        p_minus  = float(np.mean(null_m >= r_real_minus)) if null_minus else float('nan')
        eff_m    = ((r_real_minus - null_m.mean()) / null_m.std()
                    if null_minus and null_m.std() > 1e-10 else float('nan'))
        summary_rows.append((label, r_real, r_real_minus,
                              p_full, eff_full, p_minus, eff_m))

    # ── Summary table ─────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("  SUMMARY TABLE")
    print(f"  {'Matchup':<24} {'r_full':>7} {'p_full':>7} {'eff_full':>9} "
          f"{'r_minus':>8} {'p_minus':>8} {'eff_m':>7}")
    print("  " + "─" * 86)
    for (label, rf, rm, pf, ef, pm, em) in summary_rows:
        sig_f = "***" if pf < 0.001 else ("**" if pf < 0.01
                 else ("*" if pf < 0.05 else "ns "))
        sig_m = "***" if pm < 0.001 else ("**" if pm < 0.01
                 else ("*" if pm < 0.05 else "ns "))
        pf_s  = f"{pf:.4f}" if not math.isnan(pf) else "  nan"
        pm_s  = f"{pm:.4f}" if not math.isnan(pm) else "  nan"
        ef_s  = f"{ef:+.2f}σ" if not math.isnan(ef) else "  nan"
        em_s  = f"{em:+.2f}σ" if not math.isnan(em) else "  nan"
        print(f"  {label:<24} {rf:+7.4f} {pf_s:>7} {sig_f} {ef_s:>8}  "
              f"{rm:+8.4f} {pm_s:>8} {sig_m} {em_s:>7}")
    print("  " + "─" * 86)
    print("  Significance: *** p<0.001  ** p<0.01  * p<0.05  ns p≥0.05")
    print("=" * 90)

    # ── Verdict ───────────────────────────────────────────────────────────────
    n_sig   = sum(1 for *_, pf, ef, pm, em in summary_rows if pf < 0.05)
    n_total = len(summary_rows)
    print(f"\n  VERDICT: {n_sig}/{n_total} matchups show significant full-LH signal (p<0.05).")
    if n_sig == n_total:
        print("  LH classification is NON-TRIVIAL across all matchups.")
        print("  Random shuffling cannot reproduce the observed correlations.")
    elif n_sig > n_total // 2:
        print("  LH classification shows signal in most matchups.")
        print("  The null model is rejected for the majority of conditions.")
    else:
        print("  WARNING: LH signal is not robust — null model not consistently rejected.")


if __name__ == "__main__":
    main()
