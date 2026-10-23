import chess
import logging

from .chess_ai import evaluate_position
from .models import GameMatch, TrainingLessonProgress
from .training import LESSONS

logger = logging.getLogger(__name__)

PIECE_VALUES = {
	chess.PAWN: 1,
	chess.KNIGHT: 3,
	chess.BISHOP: 3,
	chess.ROOK: 5,
	chess.QUEEN: 9,
	chess.KING: 0,
}

PIECE_NAMES = {
	chess.PAWN: 'pawn',
	chess.KNIGHT: 'knight',
	chess.BISHOP: 'bishop',
	chess.ROOK: 'rook',
	chess.QUEEN: 'queen',
	chess.KING: 'king',
}

MIN_ALTERNATIVE_IMPROVEMENT = 100
TRAINING_FOCUS_THEMES = {
	'mating_threats': ('king safety', 'checkmate', 'mating attack', 'back-rank mate'),
	'missed_tactics': ('fork', 'double attack', 'calculation', 'rook tactics'),
	'piece_safety': ('piece safety', 'safe captures', 'rook tactics', 'board vision'),
	'calculation': ('calculation', 'board vision', 'piece safety'),
}
TRAINING_FOCUS_LABELS = {
	'mating_threats': 'King safety and mating threats',
	'missed_tactics': 'Spotting tactical opportunities',
	'piece_safety': 'Keeping pieces safe',
	'calculation': 'Comparing candidate moves',
}


def _captured_value(board, move):
	if board.is_en_passant(move):
		return PIECE_VALUES[chess.PAWN]
	piece = board.piece_at(move.to_square)
	return PIECE_VALUES[piece.piece_type] if piece else 0


def _best_immediate_capture_threat(board):
	best_threat = None
	for capture in board.legal_moves:
		if not board.is_capture(capture):
			continue

		victim_value = _captured_value(board, capture)
		attacker = board.piece_at(capture.from_square)
		next_board = board.copy(stack=False)
		next_board.push(capture)
		best_recapture = 0
		for recapture in next_board.legal_moves:
			if recapture.to_square != capture.to_square or not next_board.is_capture(recapture):
				continue
			best_recapture = max(best_recapture, _captured_value(next_board, recapture))

		net_gain = victim_value - best_recapture
		if net_gain >= 3 and (best_threat is None or net_gain > best_threat['net_gain']):
			best_threat = {
				'net_gain': net_gain,
				'piece': PIECE_NAMES[board.piece_at(capture.to_square).piece_type],
				'move': board.san(capture),
				'attacker_value': PIECE_VALUES[attacker.piece_type] if attacker else 0,
			}
	return best_threat


def _score_tactical_move(board, move):
	next_board = board.copy(stack=False)
	capture_value = _captured_value(board, move)
	promotion_value = (
		PIECE_VALUES[move.promotion] - PIECE_VALUES[chess.PAWN]
		if move.promotion
		else 0
	)
	next_board.push(move)
	if next_board.is_checkmate():
		return 100, board.san(move)
	threat = _best_immediate_capture_threat(next_board)
	threat_cost = threat['net_gain'] if threat else 0
	return capture_value + promotion_value - threat_cost, board.san(move)


def _immediate_checkmate(board):
	for move in board.legal_moves:
		next_board = board.copy(stack=False)
		next_board.push(move)
		if next_board.is_checkmate():
			return board.san(move)
	return None


def _positional_alternative(board, played_move):
	no_alternative = {
		'alternative': None,
		'alternative_from': None,
		'alternative_to': None,
		'alternative_fen': None,
		'alternative_explanation': None,
	}
	played_position = board.copy(stack=False)
	played_position.push(played_move)
	played_score = evaluate_position(played_position)
	best_move = None
	best_score = None

	for candidate in board.legal_moves:
		if candidate == played_move:
			continue
		position = board.copy(stack=False)
		position.push(candidate)
		score = evaluate_position(position)
		if best_score is None or (
			score > best_score if board.turn == chess.BLACK else score < best_score
		):
			best_move = candidate
			best_score = score

	if best_move is None or best_score is None:
		return no_alternative

	improvement = (
		best_score - played_score if board.turn == chess.BLACK
		else played_score - best_score
	)
	if improvement < MIN_ALTERNATIVE_IMPROVEMENT:
		return no_alternative

	position = board.copy(stack=False)
	alternative_san = board.san(best_move)
	position.push(best_move)
	return {
		'alternative': alternative_san,
		'alternative_from': chess.square_name(best_move.from_square),
		'alternative_to': chess.square_name(best_move.to_square),
		'alternative_fen': position.fen(),
		'alternative_explanation': (
			f'{alternative_san} scored about {improvement / 100:.1f} pawn(s) better '
			'in a quick positional scan. Compare the resulting position.'
		),
	}


def _review_move(board, move):
	actual_score, actual_san = _score_tactical_move(board, move)
	if actual_score == 100:
		return {
			'quality': 'checkmate',
			'explanation': 'You found checkmate.',
			'suggestion': None,
			'alternative': None,
			'alternative_from': None,
			'alternative_to': None,
			'alternative_fen': None,
			'alternative_explanation': None,
		}

	alternative = _positional_alternative(board, move)
	alternatives = []
	missed_mate = None

	for candidate in board.legal_moves:
		if candidate == move:
			continue
		next_board = board.copy(stack=False)
		next_board.push(candidate)
		if next_board.is_checkmate():
			missed_mate = board.san(candidate)
			break
		if _immediate_checkmate(next_board):
			continue
		score, san = _score_tactical_move(board, candidate)
		alternatives.append((score, san))

	if missed_mate:
		return {
			'quality': 'missed_win',
			'explanation': f'You had checkmate available with {missed_mate}.',
			'suggestion': missed_mate,
			**alternative,
		}

	best_alternative = max(alternatives, default=None, key=lambda item: item[0])
	if best_alternative and best_alternative[0] >= 3 and best_alternative[0] - actual_score >= 3:
		return {
			'quality': 'missed_tactic',
			'explanation': f'{best_alternative[1]} was a safer material-winning tactic.',
			'suggestion': best_alternative[1],
			**alternative,
		}

	board.push(move)
	mate_threat = _immediate_checkmate(board)
	threat = _best_immediate_capture_threat(board)
	board.pop()
	if mate_threat:
		safest_alternative = max(alternatives, default=None, key=lambda item: item[0])
		return {
			'quality': 'blunder',
			'explanation': f'This allowed the immediate checkmate {mate_threat}.',
			'suggestion': safest_alternative[1] if safest_alternative else None,
			**alternative,
		}
	if threat:
		quality = 'blunder' if threat['net_gain'] >= 5 else 'mistake'
		return {
			'quality': quality,
			'explanation': (
				f'This allowed {threat["move"]}, winning your {threat["piece"]} '
				f'({threat["net_gain"]} points of net material).'
			),
			'suggestion': actual_san,
			**alternative,
		}

	return {
		'quality': 'no_tactic',
		'explanation': 'No immediate checkmate or major material tactic was found.',
		'suggestion': None,
		**alternative,
	}


def _training_focus(player_moves):
	if not player_moves:
		return None

	mating_blunders = any(
		move['quality'] == 'blunder' and 'immediate checkmate' in move['explanation']
		for move in player_moves
	)
	missed_tactics = any(
		move['quality'] in {'missed_win', 'missed_tactic'}
		for move in player_moves
	)
	piece_safety_errors = any(
		move['quality'] in {'blunder', 'mistake'} and 'winning your ' in move['explanation']
		for move in player_moves
	)
	if mating_blunders:
		return 'mating_threats'
	if missed_tactics:
		return 'missed_tactics'
	if piece_safety_errors:
		return 'piece_safety'
	if any(move.get('alternative') for move in player_moves):
		return 'calculation'
	return None


def _training_lesson_recommendation(focus, player_id):
	progress_by_id = {
		progress.lesson_id: progress
		for progress in TrainingLessonProgress.objects.filter(player_id=player_id)
	}
	completed_ids = {
		lesson['id'] for lesson in LESSONS
		if progress_by_id.get(lesson['id']) and progress_by_id[lesson['id']].completed_at
	}
	next_lesson = next((lesson for lesson in LESSONS if lesson['id'] not in completed_ids), None)
	active_level = next_lesson['level'] if next_lesson else LESSONS[-1]['level']
	available_lessons = [
		lesson for lesson in LESSONS
		if lesson['level'] == active_level
		and (lesson['id'] in completed_ids or lesson is next_lesson)
	]
	theme_keywords = TRAINING_FOCUS_THEMES[focus]
	matching_lesson = next(
		(
			lesson for lesson in available_lessons
			if any(keyword in lesson['theme'].lower() for keyword in theme_keywords)
		),
		None,
	)
	future_lesson = next(
		(
			lesson for lesson in LESSONS
			if any(keyword in lesson['theme'].lower() for keyword in theme_keywords)
		),
		None,
	)

	if matching_lesson:
		return {
			'focus': focus,
			'focus_label': TRAINING_FOCUS_LABELS[focus],
			'lesson_id': matching_lesson['id'],
			'lesson_title': matching_lesson['title'],
			'lesson_theme': matching_lesson['theme'],
			'available_now': True,
			'message': f'Practice {TRAINING_FOCUS_LABELS[focus].lower()} with this lesson.',
		}
	if future_lesson and next_lesson:
		return {
			'focus': focus,
			'focus_label': TRAINING_FOCUS_LABELS[focus],
			'lesson_id': next_lesson['id'],
			'lesson_title': next_lesson['title'],
			'lesson_theme': next_lesson['theme'],
			'available_now': True,
			'message': (
				f'Start this available lesson; focused {future_lesson["theme"]} '
				'practice unlocks later in your course.'
			),
		}
	return {
		'focus': focus,
		'focus_label': TRAINING_FOCUS_LABELS[focus],
		'lesson_id': None,
		'lesson_title': None,
		'lesson_theme': None,
		'available_now': False,
		'message': 'Continue your course to unlock practice for this focus.',
	}


def _training_recommendation(player_moves, player_id):
	focus = _training_focus(player_moves)
	return _training_lesson_recommendation(focus, player_id) if focus else None


def _reviewed_player_moves(match, player_id, stored_moves):
	board = chess.Board()
	player_moves = []
	for stored_move in stored_moves:
		if board.is_game_over():
			raise ValueError('Match contains moves after the game ended.')
		move = board.parse_san(stored_move.notation)
		if (
			chess.square_name(move.from_square) != stored_move.from_square
			or chess.square_name(move.to_square) != stored_move.to_square
		):
			raise ValueError('Match move coordinates do not match the notation.')
		mover_is_white = board.turn == chess.WHITE
		if (
			mover_is_white and match.white_player_id == player_id
		) or (
			not mover_is_white and match.black_player_id == player_id
		):
			player_moves.append(_review_move(board, move))
		board.push(move)
	return player_moves


def training_trend(matches, player_id):
	focus_counts = {}
	matches_reviewed = 0
	for match in matches:
		stored_moves = list(match.moves.all())
		if not stored_moves:
			continue
		try:
			player_moves = _reviewed_player_moves(match, player_id, stored_moves)
		except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError) as error:
			logger.warning(
				'Training trend skipped invalid match history (match_id=%s, error=%s).',
				match.id,
				type(error).__name__,
			)
			continue
		matches_reviewed += 1
		focus = _training_focus(player_moves)
		if focus:
			focus_counts[focus] = focus_counts.get(focus, 0) + 1

	if not focus_counts:
		return {
			'matches_reviewed': matches_reviewed,
			'focus': None,
			'focus_label': None,
			'matches_with_focus': 0,
			'recommendation': None,
			'message': (
				f'No recurring tactical focus found in your last {matches_reviewed} '
				'matches.' if matches_reviewed else 'Finish a match to start tracking game trends.'
			),
		}

	focus = max(
		focus_counts,
		key=lambda item: (focus_counts[item], -list(TRAINING_FOCUS_LABELS).index(item)),
	)
	return {
		'matches_reviewed': matches_reviewed,
		'focus': focus,
		'focus_label': TRAINING_FOCUS_LABELS[focus],
		'matches_with_focus': focus_counts[focus],
		'recommendation': _training_lesson_recommendation(focus, player_id),
		'message': (
			f'This focus appeared in {focus_counts[focus]} of your '
			f'last {matches_reviewed} reviewed matches.'
		),
	}


def review_match(match, reviewed_player_id=None):
	board = chess.Board()
	review_moves = []
	for stored_move in match.moves.all():
		if board.is_game_over():
			raise ValueError('Match contains moves after the game ended.')
		move = board.parse_san(stored_move.notation)
		if (
			chess.square_name(move.from_square) != stored_move.from_square
			or chess.square_name(move.to_square) != stored_move.to_square
		):
			raise ValueError('Match move coordinates do not match the notation.')

		mover_is_white = board.turn == chess.WHITE
		analysis = _review_move(board, move)
		board.push(move)
		review_moves.append({
			'move_number': stored_move.move_number,
			'ply': len(review_moves) + 1,
			'notation': stored_move.notation,
			'from': stored_move.from_square,
			'to': stored_move.to_square,
			'fen': board.fen(),
			'player': match.white_player.username if mover_is_white else (
				match.black_player.username if match.black_player else (
					'Arena AI' if match.mode == 'ai' else 'Black'
				)
			),
			'color': 'white' if mover_is_white else 'black',
			'player_id': 'white' if mover_is_white else 'black',
			**analysis,
		})

	reviewed_moves = [
		move for move in review_moves
		if reviewed_player_id is None
		or (
			move['player_id'] == 'white' and match.white_player_id == reviewed_player_id
		)
		or (
			move['player_id'] == 'black' and match.black_player_id == reviewed_player_id
		)
	]
	for move in review_moves:
		move.pop('player_id')
	return {
		'match': {
			'id': str(match.id),
			'mode': match.mode,
			'ai_difficulty': match.ai_difficulty,
			'status': match.status,
			'result': match.result,
			'white_player': match.white_player.username,
			'black_player': match.black_player.username if match.black_player else None,
			'fen': board.fen(),
		},
		'scope': (
			'Quick scan for checkmates, captures, and material threats. Exploratory '
			'alternatives use a lightweight one-ply positional score, not a full '
			'chess-engine evaluation.'
		),
		'moves': review_moves,
		'summary': {
			'plies_reviewed': len(review_moves),
			'blunders': sum(move['quality'] == 'blunder' for move in reviewed_moves),
			'mistakes': sum(move['quality'] == 'mistake' for move in reviewed_moves),
			'missed_tactics': sum(move['quality'] in {'missed_win', 'missed_tactic'} for move in reviewed_moves),
		},
		'training_recommendation': (
			_training_recommendation(reviewed_moves, reviewed_player_id)
			if reviewed_player_id is not None else None
		),
	}
