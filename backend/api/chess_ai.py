import chess


PIECE_VALUES = {
	chess.PAWN: 100,
	chess.KNIGHT: 320,
	chess.BISHOP: 330,
	chess.ROOK: 500,
	chess.QUEEN: 900,
	chess.KING: 0,
}

SEARCH_DEPTHS = {
	'beginner': 1,
	'intermediate': 2,
	'advanced': 3,
}
MAX_SEARCH_NODES = 6000


def _evaluate(board):
	score = 0
	for square, piece in board.piece_map().items():
		value = PIECE_VALUES[piece.piece_type]
		file_index = chess.square_file(square)
		rank_index = chess.square_rank(square)
		center_bonus = int((7 - abs(3.5 - file_index) - abs(3.5 - rank_index)) * 4)
		if piece.piece_type in {chess.KNIGHT, chess.BISHOP, chess.QUEEN}:
			value += center_bonus
		if piece.piece_type == chess.PAWN:
			value += (rank_index if piece.color == chess.WHITE else 7 - rank_index) * 7
			value += center_bonus * 3
		score += value if piece.color == chess.BLACK else -value
	return score


def evaluate_position(board):
	if board.is_checkmate():
		return 100000 if board.turn == chess.WHITE else -100000
	if board.is_game_over(claim_draw=True):
		return 0
	return _evaluate(board)


def _move_order_score(board, move):
	score = 0
	if board.is_capture(move):
		captured = board.piece_at(move.to_square)
		if captured is None and board.is_en_passant(move):
			captured_value = PIECE_VALUES[chess.PAWN]
		else:
			captured_value = PIECE_VALUES[captured.piece_type] if captured else 0
		moving_value = PIECE_VALUES[board.piece_at(move.from_square).piece_type]
		score += 10 * captured_value - moving_value
	if move.promotion:
		score += PIECE_VALUES[move.promotion]
	return score


def _ordered_moves(board):
	return sorted(
		board.legal_moves,
		key=lambda move: _move_order_score(board, move),
		reverse=True,
	)


def _search(board, depth, alpha, beta, ply, state):
	state['nodes'] += 1
	if board.is_checkmate():
		return -100000 + ply if board.turn == chess.BLACK else 100000 - ply
	if board.is_game_over(claim_draw=True):
		return 0
	if depth == 0 or state['nodes'] >= MAX_SEARCH_NODES:
		return _evaluate(board)

	maximizing = board.turn == chess.BLACK
	best_score = -float('inf') if maximizing else float('inf')
	for move in _ordered_moves(board):
		board.push(move)
		score = _search(board, depth - 1, alpha, beta, ply + 1, state)
		board.pop()
		if maximizing:
			best_score = max(best_score, score)
			alpha = max(alpha, best_score)
		else:
			best_score = min(best_score, score)
			beta = min(beta, best_score)
		if beta <= alpha or state['nodes'] >= MAX_SEARCH_NODES:
			break
	return best_score


def choose_ai_move(board, difficulty):
	try:
		depth = SEARCH_DEPTHS[difficulty]
	except KeyError as error:
		raise ValueError('Unsupported AI difficulty.') from error

	legal_moves = _ordered_moves(board)
	if not legal_moves:
		return None

	best_move = None
	best_score = -float('inf')
	state = {'nodes': 0}
	for move in legal_moves:
		board.push(move)
		score = _search(board, depth - 1, -float('inf'), float('inf'), 1, state)
		board.pop()
		if score > best_score:
			best_score = score
			best_move = move
		if state['nodes'] >= MAX_SEARCH_NODES:
			break
	return best_move
