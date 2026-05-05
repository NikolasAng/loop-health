"""
Basic Usage Examples for Loop Health Framework
"""

import chess
import sys
sys.path.insert(0, '..')

from loop_health import ChessLoopHealthEngine, LHConfig
from loop_health import ChessGame

def example_basic_analysis():
    """Example: Analyze a simple chess game for stagnation"""
    print("=" * 60)
    print("Example 1: Basic Chess Game Analysis")
    print("=" * 60)
    
    game = ChessGame()
    engine = ChessLoopHealthEngine(game, LHConfig())
    
    # Simulate some moves
    board = chess.Board()
    history = [board.copy()]
    moves = []
    
    # Play a few moves (just as example)
    move_list = ['e2e4', 'c7c5', 'g1f3', 'd7d6', 'f1c4']
    for move_uci in move_list:
        move = chess.Move.from_uci(move_uci)
        if move in board.legal_moves:
            board.push(move)
            history.append(board.copy())
            moves.append(move)
    
    # Analyze for loops
    if len(moves) > 0:
        analysis = engine.analyse(history, moves)
        print(f"\nMoves played: {len(moves)}")
        print(f"Loops detected: {len(analysis['all_loops'])}")
        print(f"Loop types: {analysis.get('topology_counts', {})}")
        if analysis.get('lh_values'):
            import numpy as np
            print(f"Mean LH: {np.mean(analysis['lh_values']):.4f}")


def example_with_policies():
    """Example: Compare stagnation across different policies"""
    print("\n" + "=" * 60)
    print("Example 2: Policy Comparison")
    print("=" * 60)
    
    print("\nFor full policy comparison, see games/chess/selfplay_detection_chess.py")
    print("Run: python games/chess/selfplay_detection_chess.py")


def example_null_model():
    """Example: Permutation null model testing"""
    print("\n" + "=" * 60)
    print("Example 3: Null Model Testing")
    print("=" * 60)
    
    print("\nFor null model permutation testing, see games/chess/chess_null_model.py")
    print("Run: python games/chess/chess_null_model.py")


if __name__ == "__main__":
    example_basic_analysis()
    example_with_policies()
    example_null_model()
    
    print("\n" + "=" * 60)
    print("For more examples, see:")
    print("  - games/chess/live_chess_demo.py (real-time detection)")
    print("  - games/chess/selfplay_detection_chess.py (attractor analysis)")
    print("  - games/chess/chess_null_model.py (statistical validation)")
    print("=" * 60)
