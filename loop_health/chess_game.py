"""
chess_game.py — Chess wrapper for the LH framework

Uses python-chess as the board engine.

LH mapping
  R(t) = 1.0  on captures, pawn moves, castling, promotion
              (irreversible under chess rules — cannot undo)
  R(t) = 0.0  on quiet moves (piece repositioning)
  S(t) = 1.0  when no capture AND no pawn move AND material unchanged
              (= 50-move rule territory; halfmove clock is ticking)

Key theoretical validations:
  - 50-move rule  = primitive LH threshold: S(t)=1 for 50 consecutive steps
  - 3-fold repetition = exact state repetition with LH <= theta_H
  - CST-Lazy Break should subsume both rules when calibrated
"""

from __future__ import annotations
from typing import List, Tuple, Optional
import chess

# Standard piece values (centipawns / 100 → pawns)
PIECE_VALUE = {
    chess.PAWN:   1.0,
    chess.KNIGHT: 3.0,
    chess.BISHOP: 3.2,
    chess.ROOK:   5.0,
    chess.QUEEN:  9.0,
    chess.KING:   0.0,
}

MAX_MATERIAL = 2 * (8*1 + 2*3 + 2*3.2 + 2*5 + 1*9)  # both sides full army


class ChessGame:

    def __init__(self, max_steps: int = 200):
        self.max_steps = max_steps

    # ── State helpers ──────────────────────────────────────────────────────

    def initial_state(self) -> chess.Board:
        return chess.Board()

    def copy_state(self, board: chess.Board) -> chess.Board:
        return board.copy()

    def legal_moves(self, board: chess.Board) -> List[chess.Move]:
        return list(board.legal_moves)

    def apply_move(self, board: chess.Board, move: chess.Move) -> chess.Board:
        b = board.copy()
        b.push(move)
        return b

    def state_key(self, board: chess.Board) -> str:
        return board.fen().rsplit(' ', 2)[0]  # strip halfmove/fullmove for repetition

    # ── Irreversibility ────────────────────────────────────────────────────

    def is_irreversible(self, board: chess.Board, move: chess.Move) -> bool:
        return (
            board.is_capture(move)
            or board.piece_type_at(move.from_square) == chess.PAWN
            or board.is_castling(move)
            or move.promotion is not None
        )

    # ── Material evaluation ────────────────────────────────────────────────

    def material(self, board: chess.Board, color: chess.Color) -> float:
        total = 0.0
        for pt, val in PIECE_VALUE.items():
            total += len(board.pieces(pt, color)) * val
        return total

    def material_balance(self, board: chess.Board) -> float:
        """White material minus Black material, normalised to [-1, 1]."""
        w = self.material(board, chess.WHITE)
        b = self.material(board, chess.BLACK)
        return (w - b) / (MAX_MATERIAL / 2 + 1e-9)

    def total_material(self, board: chess.Board) -> float:
        return (self.material(board, chess.WHITE)
                + self.material(board, chess.BLACK))

    # ── King safety ────────────────────────────────────────────────────────

    def king_attackers(self, board: chess.Board, color: chess.Color) -> int:
        """Number of opponent pieces attacking squares adjacent to king."""
        ksq   = board.king(color)
        if ksq is None:
            return 0
        opp   = not color
        count = 0
        for sq in chess.SquareSet(chess.BB_KING_ATTACKS[ksq] | chess.BB_SQUARES[ksq]):
            count += len(board.attackers(opp, sq))
        return count

    # ── Mobility ──────────────────────────────────────────────────────────

    def mobility(self, board: chess.Board, color: chess.Color) -> int:
        b = board.copy()
        b.turn = color
        return b.legal_moves.count()

    # ── Pawn structure ─────────────────────────────────────────────────────

    def pawn_advancement(self, board: chess.Board, color: chess.Color) -> float:
        """Mean rank of pawns, normalised [0,1]. High = advanced."""
        pawns = board.pieces(chess.PAWN, color)
        if not pawns:
            return 0.0
        if color == chess.WHITE:
            ranks = [chess.square_rank(sq) for sq in pawns]
        else:
            ranks = [7 - chess.square_rank(sq) for sq in pawns]
        return sum(ranks) / (len(ranks) * 7)

    # ── Terminal check ─────────────────────────────────────────────────────

    def is_terminal(self, board: chess.Board, step: int) -> Tuple[bool, Optional[str]]:
        if board.is_checkmate():
            winner = "black" if board.turn == chess.WHITE else "white"
            return True, f"checkmate_{winner}_wins"
        if board.is_stalemate():
            return True, "stalemate_draw"
        if board.is_insufficient_material():
            return True, "insufficient_material_draw"
        if board.is_seventyfive_moves():
            return True, "75move_draw"
        if board.is_fivefold_repetition():
            return True, "fivefold_repetition_draw"
        if step >= self.max_steps:
            return True, "step_limit_draw"
        return False, None

    # ── Max distance (normalisation constant) ─────────────────────────────

    def max_distance(self) -> float:
        return 14.0  # max Manhattan distance on 8×8 board
