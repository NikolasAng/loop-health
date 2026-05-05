#!/usr/bin/env python3
"""
Loop Health Chess Server
Real-time LH computation backend for the HTML demo
"""
import sys
sys.path.insert(0, '../../')

from flask import Flask, request, jsonify
from flask_cors import CORS
import chess
from loop_health.chess_engine import ChessLoopHealthEngine
from loop_health.loop_health import LHConfig

app = Flask(__name__)
CORS(app)

# Initialize engine
engine = ChessLoopHealthEngine()
config = LHConfig()

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'ok', 'service': 'chess-lh-server'})

@app.route('/compute-lh', methods=['POST'])
def compute_lh():
    """
    Compute LH metrics for a game
    
    Request body:
    {
        "moves": ["e2e4", "e7e5", ...],  # OR
        "pgn": "1. e4 e5 2. Nf3 Nc6 ...",  # Optional PGN
        "current_move": 5  # Optional: only compute up to this move
    }
    
    Returns:
    {
        "success": true,
        "game_length": 10,
        "moves": [
            {
                "move_num": 1,
                "san": "e4",
                "lh": 0.234,
                "lh_circ": 0.345,
                "topology": "cycle",
                "in_loop": false,
                "repetitions": 1
            },
            ...
        ],
        "summary": {
            "avg_lh": 0.15,
            "min_lh": -0.5,
            "max_lh": 0.6,
            "loops_detected": 2,
            "stagnant_moves": 3
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        moves = data.get('moves', [])
        if not moves:
            return jsonify({'success': False, 'error': 'No moves provided'}), 400
        
        current_move = data.get('current_move', len(moves))
        
        # Reconstruct game
        game = chess.Board()
        history = [game.copy()]
        move_list = []
        lh_values = []
        
        for i, move_uci in enumerate(moves[:current_move]):
            try:
                move = chess.Move.from_uci(move_uci)
                if move not in game.legal_moves:
                    return jsonify({
                        'success': False, 
                        'error': f'Illegal move at position {i}: {move_uci}'
                    }), 400
                
                game.push(move)
                history.append(game.copy())
                move_list.append(move)
                
            except ValueError as e:
                return jsonify({
                    'success': False, 
                    'error': f'Invalid move format at position {i}: {move_uci}'
                }), 400
        
        # Analyze with ChessLoopHealthEngine
        analysis = engine.analyse(history, move_list)
        
        # Build response with per-move metrics
        moves_response = []
        position_counts = {}
        
        for idx, board in enumerate(history):
            fen = board.fen()
            rep_count = list(history[:idx+1]).count(board) + sum(1 for h in history[idx+1:] if h.fen() == fen)
            position_counts[fen] = rep_count
            
            if idx > 0:
                # Get LH for this move
                lh_data = {
                    'move_num': (idx + 1) // 2,
                    'move_color': 'W' if idx % 2 == 1 else 'B',
                    'san': move_list[idx-1].uci() if idx <= len(move_list) else '?',
                    'repetitions': rep_count,
                    'position_fen': fen[:40] + '...' if len(fen) > 40 else fen
                }
                
                # Check if move is part of a detected loop
                in_loop = False
                loop_type = 'none'
                
                for loop_record in analysis.get('exact_loops', []):
                    if loop_record.start_step <= idx <= loop_record.end_step:
                        in_loop = True
                        loop_type = loop_record.topology
                        break
                
                lh_data['in_loop'] = in_loop
                lh_data['loop_type'] = loop_type
                
                moves_response.append(lh_data)
        
        # Summary
        summary = {
            'total_moves': len(move_list),
            'total_positions': len(set(h.fen() for h in history)),
            'max_repetition': max(position_counts.values()) if position_counts else 1,
            'loops_detected': len(analysis.get('exact_loops', [])),
            'functional_loops': len(analysis.get('functional_loops', [])),
            'all_loops': len(analysis.get('all_loops', []))
        }
        
        return jsonify({
            'success': True,
            'game_length': len(move_list),
            'moves': moves_response,
            'summary': summary,
            'analysis': {
                'exact_loops': len(analysis.get('exact_loops', [])),
                'functional_loops': len(analysis.get('functional_loops', [])),
                'repetition_liability': float(analysis.get('metrics', {}).get('repetition_liability', 0))
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get-lh-single', methods=['POST'])
def get_lh_single():
    """
    Get LH metrics for a single position
    
    Request body:
    {
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "moves_in_position": ["e2e4", "e7e5", ...]
    }
    """
    try:
        data = request.get_json()
        fen = data.get('fen')
        
        if not fen:
            return jsonify({'success': False, 'error': 'No FEN provided'}), 400
        
        board = chess.Board(fen)
        
        return jsonify({
            'success': True,
            'fen': fen,
            'material_balance': calculate_material(board),
            'legal_moves': len(list(board.legal_moves)),
            'in_check': board.is_check(),
            'checkmated': board.is_checkmate(),
            'stalemate': board.is_stalemate()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def calculate_material(board):
    """Calculate material balance"""
    values = {'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9}
    white_mat = sum(values.get(piece.symbol().lower(), 0) 
                   for piece in board.piece_map().values() if piece.color)
    black_mat = sum(values.get(piece.symbol().lower(), 0) 
                   for piece in board.piece_map().values() if not piece.color)
    return {'white': white_mat, 'black': black_mat, 'diff': white_mat - black_mat}

if __name__ == '__main__':
    print("Starting Chess Loop Health Server on http://localhost:5000")
    print("Endpoints:")
    print("  GET  /health")
    print("  POST /compute-lh (body: {moves: [...], current_move: N})")
    print("  POST /get-lh-single (body: {fen: '...'})")
    app.run(debug=True, port=5000, host='localhost')
