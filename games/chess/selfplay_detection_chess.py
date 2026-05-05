"""
Self-Play Detection Experiment: Chess
======================================
Exploratory analysis of stagnation patterns in chess self-play.
Not for the paper—just to understand the framework better.

Generates N games, detects loops, analyzes:
- Stagnation distribution (where in games do loops occur?)
- Topology classification (Cycle/Spring/Tube %)
- Loop attractor zones (which positions recur most?)
- Policy comparison (which matchup has most stagnation?)
"""

import sys
sys.path.insert(0, 'g:\\ΕΡΓΑΣΙΕΣ\\code')

import random
import numpy as np
from collections import defaultdict
import chess
import time

from chess_game import ChessGame
from chess_engine import ChessLoopHealthEngine
from loop_health import LHConfig

random.seed(42)
np.random.seed(42)

# ── Policies (from chess_null_model.py) ────────────────────────────────
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
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is None:
            continue
        sign = +1.0 if piece.color == chess.WHITE else -1.0
        score += sign * _PVAL.get(piece.piece_type, 0)
    return score

def get_random_move(board):
    return random.choice(list(board.legal_moves))

def get_greedy_move(board):
    best_mv, best_score = None, -float('inf')
    for mv in _order_moves(board):
        board.push(mv)
        score = _evaluate(board)
        board.pop()
        if score > best_score:
            best_score = score
            best_mv = mv
    return best_mv or get_random_move(board)

def get_defensive_move(board):
    best_mv, best_score = None, float('inf')
    for mv in _order_moves(board):
        board.push(mv)
        score = -_evaluate(board)
        board.pop()
        if score < best_score:
            best_score = score
            best_mv = mv
    return best_mv or get_random_move(board)

POLICIES = {
    'random': get_random_move,
    'greedy': get_greedy_move,
    'defensive': get_defensive_move,
}

def run_selfplay_detection(policy1, policy2, num_games=10, max_steps=200, verbose=False):
    """
    Run self-play detection: simulate games and analyze stagnation patterns.
    Also captures board positions of detected loops.
    """
    results = {
        'games': [],
        'stagnation_dist': [],
        'topology_counts': {'Cycle': 0, 'Spring': 0, 'Tube': 0},
        'total_loops': 0,
        'loop_positions': defaultdict(list),
        'lh_values': [],
        'all_loops': [],
        'game_times': [],
    }
    
    game_engine = ChessGame()
    lh_engine = ChessLoopHealthEngine(game_engine, LHConfig(theta_H=0.05))
    
    for game_idx in range(num_games):
        game_start_time = time.time()
        board = chess.Board()
        history = [board.copy()]
        moves = []
        
        # Play game
        for step in range(max_steps):
            if board.is_game_over():
                break
            
            move = policy1(board) if board.turn else policy2(board)
            if move is None:
                break
            
            board.push(move)
            history.append(board.copy())
            moves.append(move)
        
        # Analyze loops
        if len(moves) > 0:
            analysis = lh_engine.analyse(history, moves)
            all_loops = analysis['all_loops']
            metrics = analysis['metrics']
            
            # Accumulate results
            for metric in metrics:
                results['lh_values'].append(metric.lh)
            
            for loop in all_loops:
                results['total_loops'] += 1
                results['all_loops'].append(loop)
                
                # Classify topology
                topology = loop.topology or 'Cycle'
                results['topology_counts'][topology] += 1
                
                # Capture board positions during the loop
                loop_start = loop.start_step
                loop_end = loop.end_step
                for step_in_range in range(loop_start, min(loop_end + 1, len(history))):
                    board_in_loop = history[step_in_range]
                    fen = board_in_loop.fen()
                    results['loop_positions'][fen].append({
                        'game': game_idx,
                        'step': step_in_range,
                        'topology': topology,
                        'lh': loop.avg_lh if hasattr(loop, 'avg_lh') else 0,
                    })
            
            # Record game
            game_phase = 'early' if len(moves) < 30 else ('mid' if len(moves) < 100 else 'late')
            game_elapsed = time.time() - game_start_time
            results['game_times'].append(game_elapsed)
            results['games'].append({
                'moves': len(moves),
                'loops': len(all_loops),
                'lh_mean': np.mean(results['lh_values']) if results['lh_values'] else 0,
                'lh_min': min(results['lh_values']) if results['lh_values'] else 0,
                'lh_max': max(results['lh_values']) if results['lh_values'] else 0,
                'phase': game_phase,
                'time': game_elapsed,
            })
            results['stagnation_dist'].append((game_phase, len(all_loops)))
        
        if verbose and (game_idx + 1) % max(1, num_games // 5) == 0:
            print(f"  [{game_idx + 1}/{num_games}] Loops detected: {len(all_loops)} | Elapsed: {game_elapsed:.2f}s")
    
    return results

def analyze_board_position(fen):
    """Extract basic position analysis from FEN."""
    board = chess.Board(fen)
    pieces = {
        'pawns': len(board.pieces(chess.PAWN, chess.WHITE)) + len(board.pieces(chess.PAWN, chess.BLACK)),
        'knights': len(board.pieces(chess.KNIGHT, chess.WHITE)) + len(board.pieces(chess.KNIGHT, chess.BLACK)),
        'bishops': len(board.pieces(chess.BISHOP, chess.WHITE)) + len(board.pieces(chess.BISHOP, chess.BLACK)),
        'rooks': len(board.pieces(chess.ROOK, chess.WHITE)) + len(board.pieces(chess.ROOK, chess.BLACK)),
        'queens': len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK)),
    }
    legal_moves = len(list(board.legal_moves))
    is_check = board.is_check()
    
    return {
        'pieces': pieces,
        'legal_moves': legal_moves,
        'check': is_check,
        'total_material': sum(pieces.values()),
    }

def analyze_results(results, policy_name):
    """Pretty-print analysis."""
    print(f"\n{'='*60}")
    print(f"Self-Play Detection: {policy_name}")
    print(f"{'='*60}")
    
    total_games = len(results['games'])
    total_steps = sum(g['moves'] for g in results['games'])
    total_loops = results['total_loops']
    
    print(f"\nGameplay Summary:")
    print(f"  Games: {total_games}")
    print(f"  Total moves: {total_steps}")
    print(f"  Total loops detected: {total_loops}")
    if total_games > 0:
        print(f"  Average moves/game: {total_steps / total_games:.1f}")
        print(f"  Average loops/game: {total_loops / total_games:.2f}")
    
    # Timing
    if results['game_times']:
        total_time = sum(results['game_times'])
        avg_time = np.mean(results['game_times'])
        print(f"\nPerformance:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Avg time/game: {avg_time:.3f}s")
        print(f"  Min/Max: {min(results['game_times']):.3f}s / {max(results['game_times']):.3f}s")
    
    # LH distribution
    all_lh = results['lh_values']
    if all_lh:
        print(f"\nLoop Health Distribution (all steps):")
        print(f"  Mean: {np.mean(all_lh):.4f}")
        print(f"  Std:  {np.std(all_lh):.4f}")
        print(f"  Min:  {np.min(all_lh):.4f}")
        print(f"  Max:  {np.max(all_lh):.4f}")
        sterile_pct = 100*sum(1 for x in all_lh if x <= 0.05)/len(all_lh)
        print(f"  Sterile (LH <= 0.05): {sterile_pct:.1f}%")
    
    # Topology
    total_topo = sum(results['topology_counts'].values())
    print(f"\nTopology Distribution (loops only):")
    if total_topo > 0:
        for topo, count in sorted(results['topology_counts'].items()):
            pct = 100 * count / total_topo
            print(f"  {topo:8s}: {count:4d} ({pct:5.1f}%)")
    
    # Game phase analysis
    phase_loops = defaultdict(int)
    phase_count = defaultdict(int)
    for phase, loop_cnt in results['stagnation_dist']:
        phase_loops[phase] += loop_cnt
        phase_count[phase] += 1
    
    print(f"\nStagnation by Game Phase:")
    for phase in ['early', 'mid', 'late']:
        if phase in phase_count:
            avg_loops = phase_loops[phase] / phase_count[phase]
            print(f"  {phase:8s}: {avg_loops:.2f} avg loops/game")

def analyze_stagnation_attractors(results, top_k=10):
    """Analyze board positions that are biggest stagnation attractors."""
    print(f"\n{'='*80}")
    print(f"Top {top_k} Stagnation Attractor Positions")
    print(f"{'='*80}")
    
    # Rank positions by recurrence count
    position_recurrence = {}
    for fen, occurrences in results['loop_positions'].items():
        position_recurrence[fen] = {
            'count': len(occurrences),
            'topologies': [occ['topology'] for occ in occurrences],
            'games': set(occ['game'] for occ in occurrences),
            'avg_lh': np.mean([occ.get('lh', 0) for occ in occurrences]),
        }
    
    # Sort by recurrence count
    top_positions = sorted(position_recurrence.items(), key=lambda x: x[1]['count'], reverse=True)[:top_k]
    
    for rank, (fen, data) in enumerate(top_positions, 1):
        print(f"\n{rank}. Position recurred {data['count']} times (in {len(data['games'])} games)")
        print(f"   FEN: {fen[:80]}...")
        
        # Topology breakdown
        topo_counts = defaultdict(int)
        for topo in data['topologies']:
            topo_counts[topo] += 1
        
        topo_str = ', '.join(f"{t}:{c}" for t, c in sorted(topo_counts.items()))
        print(f"   Topology: {topo_str}")
        print(f"   Avg LH: {data['avg_lh']:.4f}")
        
        # Position analysis
        analysis = analyze_board_position(fen)
        board = chess.Board(fen)
        print(f"   Board State:")
        print(f"     - Material: {analysis['pieces']['pawns']}P {analysis['pieces']['knights']}N {analysis['pieces']['bishops']}B {analysis['pieces']['rooks']}R {analysis['pieces']['queens']}Q (total {analysis['total_material']})")
        print(f"     - Legal moves: {analysis['legal_moves']}")
        print(f"     - In check: {'Yes' if analysis['check'] else 'No'}")
        print(f"     - To move: {'White' if board.turn else 'Black'}")
        
        # Show board
        print(f"\n     Board visualization:")
        for line in str(board).split('\n'):
            print(f"     {line}")

# ─────────────────────────────────────────
# Main
# ─────────────────────────────────────────

if __name__ == '__main__':
    print("Self-Play Detection Experiment: Chess")
    print("=====================================\n")
    
    # Test different policy matchups
    matchups = [
        ('random vs random', POLICIES['random'], POLICIES['random'], 20),
        ('greedy vs greedy', POLICIES['greedy'], POLICIES['greedy'], 15),
        ('greedy vs random', POLICIES['greedy'], POLICIES['random'], 15),
    ]
    
    all_results = {}
    
    for name, policy1, policy2, num_games in matchups:
        print(f"Running: {name} ({num_games} games)...")
        results = run_selfplay_detection(policy1, policy2, num_games=num_games, verbose=True)
        all_results[name] = results
        analyze_results(results, name)
        analyze_stagnation_attractors(results, top_k=5)
    
    # Cross-matchup comparison
    print(f"\n{'='*60}")
    print(f"Cross-Matchup Comparison")
    print(f"{'='*60}")
    
    for name, results in all_results.items():
        all_lh = results['lh_values']
        if all_lh:
            games = len(results['games'])
            loops_per_game = results['total_loops'] / games if games > 0 else 0
            print(f"{name:20s} | Mean LH: {np.mean(all_lh):.4f} | Loops/game: {loops_per_game:.2f}")
    
    print("\nDone!")
