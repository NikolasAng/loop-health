"""
Loop Health Framework
=====================

A domain-validated framework for detecting stagnation in deterministic sequential games
through per-step causal productivity analysis.

Core modules:
- loop_health: Main Loop Health metrics and formulas
- chess_engine: Chess-specific implementation
- chess_game: Chess domain wrapper
- features: Feature extractors
- game: Base game abstraction

Usage example:
    from loop_health import ChessLoopHealthEngine, LHConfig
    from games.chess import ChessGame
    
    engine = ChessLoopHealthEngine(ChessGame(), LHConfig())
    analysis = engine.analyse(history, moves)
"""

__version__ = "1.0.0"
__author__ = "Nikolaos Angelosoulis"
__all__ = [
    "loop_health",
    "chess_engine",
    "chess_game",
    "features",
    "game",
]
