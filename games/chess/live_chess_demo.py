"""
live_chess_demo.py — Live Loop Health Demonstration in Chess
=============================================================================

Plays chess games with TWO scenarios side-by-side:
  Scenario A: No Break (plays until 50-move rule or checkmate)
  Scenario B: CST-Lazy Break active (terminates when LH ≤ θ_H for 10 steps)

For each game, displays:
  - Move number, board position hash
  - LH value, S(t) (50-move indicator)
  - When Break fires, when 50-move would fire
  - Steps saved by early termination

Usage: python live_chess_demo.py
"""

from __future__ import annotations

import random
import sys
import os
from typing import List, Tuple, Optional
import numpy as np
import chess

sys.path.insert(0, os.path.dirname(__file__))
from chess_game   import ChessGame
from chess_engine import ChessLoopHealthEngine
from loop_health  import LHConfig

# ── Config ────────────────────────────────────────────────────────────────────
THETA_H        = 0.05      # Sterile/Productive boundary
THETA_RL       = 3.0       # Remedial loop trigger (accumulated RL)
WINDOW_SIZE    = 10        # Min consecutive sterile steps for Break
NUM_GAMES      = 5         # Games to demonstrate
SEED           = 42

# ── Policies ──────────────────────────────────────────────────────────────────
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

def _greedy_move(board, rng):
    mvs = list(board.legal_moves)
    if not mvs:
        return None
    caps = [(_PVAL.get(board.piece_type_at(m.to_square), 0) or 0, m)
            for m in mvs if board.is_capture(m)]
    return max(caps, key=lambda x: x[0])[1] if caps else rng.choice(mvs)

def _random_move(board, rng):
    mvs = list(board.legal_moves)
    return rng.choice(mvs) if mvs else None

# ── Game runner ───────────────────────────────────────────────────────────────

def play_game(policy_p1, policy_p2, rng, max_steps=200):
    """
    Play a game and track both scenarios.
    
    Returns:
      dict with keys:
        'moves_no_break': steps in scenario A (no Break)
        'moves_with_break': steps in scenario B (with Break)
        'break_triggered': boolean, did Break fire?
        'break_at_step': step number where Break fired (None if no break)
        'fifty_move_at_step': step number where 50-move would trigger (None if none)
        'history': list of tuples (step, lh, s_t, board_hash, break_status)
    """
    
    game = ChessGame(max_steps=max_steps)
    engine = ChessLoopHealthEngine(game, LHConfig())
    
    board = game.initial_state()
    history = [board.copy()]
    moves = []
    
    lh_values = []
    s_values = []
    
    # Track for Break criterion
    rl_accum = {0: 0.0, 1: 0.0}  # per player
    sterile_window = []
    break_fired = False
    break_step = None
    fifty_move_step = None
    
    policy = {0: policy_p1, 1: policy_p2}
    
    for step in range(max_steps):
        # Check if game is over
        if board.is_game_over():
            break
        
        # Choose move
        p = int(board.turn == chess.BLACK)
        move = policy[p](board, rng)
        if move is None:
            break
        
        # Record before transition
        lh_before = None
        s_before = None
        
        # Make move
        board.push(move)
        history.append(board.copy())
        moves.append(move)
        
        # Compute LH
        result = engine.analyse(history, moves)
        if result['metrics']:
            m = result['metrics'][-1]
            lh_val = m.lh
            s_val = m.stagnation  # 1.0 if stagnant, 0.0 otherwise
        else:
            lh_val = 0.5
            s_val = 0.0
        
        lh_values.append(lh_val)
        s_values.append(s_val)
        
        # Update RL (accumulated repetition count)
        is_exact_rep = len(result['exact_loops']) > 0
        if is_exact_rep:
            rl_accum[p] += 1.0
        else:
            rl_accum[p] = 0.0
        
        # Check Break criterion
        if lh_val <= THETA_H:
            sterile_window.append(step)
            if len(sterile_window) >= WINDOW_SIZE and max(rl_accum.values()) >= THETA_RL:
                if not break_fired:
                    break_fired = True
                    break_step = step
        else:
            sterile_window = []
        
        # Check 50-move rule
        if s_val > 0.5 and fifty_move_step is None:
            halfmove_clock = board.halfmove_clock
            if halfmove_clock >= 100:  # 50 full moves = 100 halfmoves
                fifty_move_step = step
        
        # Print progress
        if step % 20 == 0:
            print(f"  Step {step:3d}: LH={lh_val:.4f}, S={s_val}, "
                  f"RL_accum={rl_accum}, Break={break_fired}")
    
    return {
        'moves_no_break': len(moves),
        'moves_with_break': break_step + 1 if break_fired else len(moves),
        'break_triggered': break_fired,
        'break_at_step': break_step,
        'fifty_move_at_step': fifty_move_step,
        'lh_values': lh_values,
        's_values': s_values,
        'history': history,
    }

# ── Main demo ────────────────────────────────────────────────────────────────

def main():
    random.seed(SEED)
    rng = random.Random(SEED)
    
    print("=" * 80)
    print("  LIVE LOOP HEALTH DEMONSTRATION — CHESS")
    print("=" * 80)
    print(f"  θ_H (sterile/productive) = {THETA_H}")
    print(f"  θ_RL (remedial loop trigger) = {THETA_RL}")
    print(f"  Break window = {WINDOW_SIZE} consecutive sterile steps")
    print()
    
    matchups = [
        ("greedy", "random", _greedy_move, _random_move),
        ("random", "greedy", _random_move, _greedy_move),
    ]
    
    total_saved = 0
    total_games = 0
    
    for name_p1, name_p2, pol_p1, pol_p2 in matchups:
        print(f"\n{'─' * 80}")
        print(f"  Matchup: {name_p1.upper()} vs {name_p2.upper()}")
        print(f"{'─' * 80}\n")
        
        for game_num in range(NUM_GAMES):
            print(f"  Game {game_num + 1}/{NUM_GAMES}")
            result = play_game(pol_p1, pol_p2, rng)
            
            steps_saved = result['moves_no_break'] - result['moves_with_break']
            pct_saved = 100.0 * steps_saved / result['moves_no_break'] if result['moves_no_break'] > 0 else 0.0
            
            print(f"    ✓ No Break:    {result['moves_no_break']:3d} moves")
            print(f"    ✓ With Break:  {result['moves_with_break']:3d} moves  "
                  f"(saved {steps_saved:3d}, {pct_saved:5.1f}%)")
            
            if result['break_triggered']:
                print(f"    ⚡ Break fired at step {result['break_at_step']}")
            else:
                print(f"    ⚡ Break did NOT fire")
            
            if result['fifty_move_at_step'] is not None:
                print(f"    ◆ 50-move rule would trigger at step {result['fifty_move_at_step']}")
            else:
                print(f"    ◆ No 50-move rule reached")
            
            if result['break_triggered']:
                total_saved += steps_saved
                total_games += 1
            
            print()
    
    print(f"\n{'=' * 80}")
    print(f"  SUMMARY")
    print(f"{'=' * 80}")
    if total_games > 0:
        avg_saved = total_saved / total_games
        print(f"  Games with Break: {total_games}")
        print(f"  Average steps saved: {avg_saved:.1f}")
        print(f"  Total steps saved: {total_saved}")
    else:
        print(f"  No breaks triggered in this run.")
    print()

if __name__ == "__main__":
    main()
