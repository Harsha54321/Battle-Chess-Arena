import json
import hashlib
import io
import re
import secrets
from datetime import timedelta
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import chess
from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import TestCase, TransactionTestCase, override_settings

from .chess_ai import choose_ai_move
from .models import DailyChallengeProgress, DailyChallengeSettings, FriendConnection, GameMatch, GameMove, MatchMessage, Notification, PlayerProfile, PlayerSession, TrainingLessonProgress
from .review import _review_move, _training_recommendation
from .training import LESSONS, lesson_position
from .views import _board_result, _board_termination
from config.asgi import application


class AdminApiTests(TestCase):
	def setUp(self):
		self.staff_user = get_user_model().objects.create_user(
			username='arena-admin',
			password='SecureAdminPassword!42',
			is_staff=True,
		)
		self.player = PlayerProfile.objects.create(username='AdminManagedPlayer')

	def admin_token(self):
		response = self.client.post(
			'/api/admin/login/',
			data=json.dumps({'username': 'arena-admin', 'password': 'SecureAdminPassword!42'}),
			content_type='application/json',
		)
		self.assertEqual(response.status_code, 200)
		return response.json()['token']

	def test_admin_login_requires_staff_and_credentials(self):
		invalid_password = self.client.post(
			'/api/admin/login/',
			data=json.dumps({'username': 'arena-admin', 'password': 'wrong'}),
			content_type='application/json',
		)
		self.assertEqual(invalid_password.status_code, 401)

		get_user_model().objects.create_user(username='regular-user', password='RegularPassword!42')
		regular_login = self.client.post(
			'/api/admin/login/',
			data=json.dumps({'username': 'regular-user', 'password': 'RegularPassword!42'}),
			content_type='application/json',
		)
		self.assertEqual(regular_login.status_code, 403)

	def test_admin_dashboard_and_player_suspension_require_staff_token(self):
		self.assertEqual(self.client.get('/api/admin/overview/').status_code, 401)
		self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {self.admin_token()}'

		overview = self.client.get('/api/admin/overview/')
		self.assertEqual(overview.status_code, 200)
		self.assertEqual(overview.json()['overview']['players_total'], 1)

		player_list = self.client.get('/api/admin/players/?q=AdminManaged')
		self.assertEqual(player_list.status_code, 200)
		self.assertEqual(player_list.json()['pagination']['total'], 1)
		self.assertEqual(player_list.json()['players'][0]['username'], self.player.username)

		suspend = self.client.post(
			f'/api/admin/players/{self.player.id}/suspension/',
			data=json.dumps({'suspended': True}),
			content_type='application/json',
		)
		self.assertEqual(suspend.status_code, 200)
		self.assertTrue(suspend.json()['player']['is_suspended'])
		self.assertFalse(PlayerProfile.objects.get(id=self.player.id).sessions.exists())

		bad_update = self.client.post(
			f'/api/admin/players/{self.player.id}/suspension/',
			data=json.dumps({'suspended': 'false'}),
			content_type='application/json',
		)
		self.assertEqual(bad_update.status_code, 400)

	def test_admin_token_is_rejected_when_staff_access_is_removed(self):
		self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {self.admin_token()}'
		self.staff_user.is_staff = False
		self.staff_user.save(update_fields=['is_staff'])
		self.assertEqual(self.client.get('/api/admin/overview/').status_code, 401)

	def test_admin_can_update_daily_challenge_and_apply_it_to_today(self):
		self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {self.admin_token()}'
		today = timezone.localdate()
		progress = DailyChallengeProgress.objects.create(
			player=self.player,
			date=today,
			progress=3,
			target=3,
			reward_coins=500,
		)
		response = self.client.post(
			'/api/admin/challenges/',
			data=json.dumps({'target': 5, 'reward_coins': 800}),
			content_type='application/json',
		)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), {'target': 5, 'reward_coins': 800})
		progress.refresh_from_db()
		self.assertEqual((progress.progress, progress.target, progress.reward_coins), (3, 5, 800))

		progress.progress = 5
		progress.save(update_fields=['progress'])
		lowered_target = self.client.post(
			'/api/admin/challenges/',
			data=json.dumps({'target': 2, 'reward_coins': 0}),
			content_type='application/json',
		)
		self.assertEqual(lowered_target.status_code, 200)
		progress.refresh_from_db()
		self.assertEqual((progress.progress, progress.target, progress.reward_coins), (2, 2, 0))

	def test_daily_challenge_admin_endpoint_requires_auth_and_valid_settings(self):
		self.assertEqual(self.client.get('/api/admin/challenges/').status_code, 401)
		self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {self.admin_token()}'
		settings = self.client.get('/api/admin/challenges/')
		self.assertEqual(settings.status_code, 200)
		self.assertEqual(settings.json(), {'target': 3, 'reward_coins': 500})

		for payload in (
			{'target': True, 'reward_coins': 500},
			{'target': 21, 'reward_coins': 500},
			{'target': 3, 'reward_coins': -1},
			{'target': 3, 'reward_coins': 100_001},
		):
			with self.subTest(payload=payload):
				response = self.client.post(
					'/api/admin/challenges/',
					data=json.dumps(payload),
					content_type='application/json',
				)
				self.assertEqual(response.status_code, 400)


class GameApiTests(TestCase):
	def authenticate_as(self, player):
		token = secrets.token_urlsafe(32)
		PlayerSession.objects.create(
			player=player,
			token_hash=hashlib.sha256(token.encode('utf-8')).hexdigest(),
			expires_at=timezone.now() + timedelta(days=30),
		)
		self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
		return token

	def create_player(self, username='TestPlayer'):
		response = self.client.post(
			'/api/players/guest/',
			data=json.dumps({'username': username, 'avatar': 'knight'}),
			content_type='application/json',
		)
		self.assertEqual(response.status_code, 201)
		self.client.defaults['HTTP_AUTHORIZATION'] = f"Bearer {response.json()['session_token']}"
		return response.json()['player']

	def test_guest_player_and_detail(self):
		player = self.create_player()
		response = self.client.get(f"/api/players/{player['id']}/")
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['player']['username'], 'TestPlayer')

	def test_profile_summary_uses_recorded_match_and_training_data(self):
		player = PlayerProfile.objects.create(username='ProfileSummaryPlayer')
		opponent = PlayerProfile.objects.create(username='ProfileSummaryOpponent')
		unrelated = PlayerProfile.objects.create(username='ProfileSummaryUnrelated')
		GameMatch.objects.create(
			white_player=player,
			black_player=opponent,
			status=GameMatch.Status.COMPLETED,
			result='white_wins',
		)
		GameMatch.objects.create(
			white_player=opponent,
			black_player=player,
			status=GameMatch.Status.ABANDONED,
			result='white_wins',
		)
		GameMatch.objects.create(
			white_player=player,
			black_player=opponent,
			status=GameMatch.Status.COMPLETED,
			result='draw',
		)
		GameMatch.objects.create(
			white_player=player,
			black_player=opponent,
			status=GameMatch.Status.ACTIVE,
			result='',
		)
		GameMatch.objects.create(
			white_player=unrelated,
			black_player=opponent,
			status=GameMatch.Status.COMPLETED,
			result='white_wins',
		)
		TrainingLessonProgress.objects.create(
			player=player,
			lesson_id=LESSONS[0]['id'],
			completed_at=timezone.now(),
		)
		TrainingLessonProgress.objects.create(
			player=player,
			lesson_id=LESSONS[1]['id'],
		)

		self.authenticate_as(player)
		response = self.client.get(f'/api/players/{player.id}/profile-summary/')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['stats'], {
			'matches_played': 3,
			'wins': 1,
			'losses': 1,
			'draws': 1,
			'win_rate_percent': 33,
		})
		self.assertEqual(response.json()['training'], {
			'lessons_completed': 1,
			'lessons_total': len(LESSONS),
		})
		self.assertEqual(
			[item['id'] for item in response.json()['achievements']],
			['first-victory', 'first-lesson'],
		)

	def test_profile_summary_is_private_and_empty_records_are_honest(self):
		player = PlayerProfile.objects.create(username='EmptyProfileSummary')
		other = PlayerProfile.objects.create(username='OtherProfileSummary')
		self.assertEqual(
			self.client.get(f'/api/players/{player.id}/profile-summary/').status_code,
			401,
		)

		self.authenticate_as(other)
		self.assertEqual(
			self.client.get(f'/api/players/{player.id}/profile-summary/').status_code,
			403,
		)
		response = self.client.get(f'/api/players/{other.id}/profile-summary/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['stats']['matches_played'], 0)
		self.assertIsNone(response.json()['stats']['win_rate_percent'])
		self.assertEqual(response.json()['achievements'], [])

	def test_match_move_and_surrender(self):
		player = self.create_player()
		response = self.client.post(
			'/api/matches/',
			data=json.dumps({'player_id': player['id'], 'mode': 'ai'}),
			content_type='application/json',
		)
		self.assertEqual(response.status_code, 201)
		match = response.json()['match']
		self.assertEqual(match['mode'], GameMatch.Mode.AI)
		self.assertEqual(match['ai_difficulty'], GameMatch.AIDifficulty.BEGINNER)
		move_response = self.client.post(
			f"/api/matches/{match['id']}/moves/",
			data=json.dumps({
				'move_number': 1,
				'from': 'e2',
				'to': 'e4',
				'notation': 'forged notation',
				'fen': 'forged-fen',
			}),
			content_type='application/json',
		)
		self.assertEqual(move_response.status_code, 201)
		self.assertEqual(move_response.json()['move']['notation'], 'e4')
		self.assertNotEqual(move_response.json()['match']['fen'], 'forged-fen')
		self.assertEqual(len(move_response.json()['match']['moves']), 2)
		self.assertEqual(GameMove.objects.filter(match_id=match['id']).count(), 2)
		ai_reply = move_response.json()['match']['moves'][1]
		self.assertEqual(ai_reply['move_number'], 2)
		self.assertTrue(chess.Move.from_uci(ai_reply['from'] + ai_reply['to']) in chess.Board(move_response.json()['match']['moves'][0]['fen']).legal_moves)
		surrender_response = self.client.post(
			f"/api/matches/{match['id']}/surrender/",
			data=json.dumps({'player_id': player['id']}),
			content_type='application/json',
		)
		self.assertEqual(surrender_response.status_code, 200)
		self.assertEqual(surrender_response.json()['match']['status'], GameMatch.Status.ABANDONED)
		repeated_surrender = self.client.post(
			f"/api/matches/{match['id']}/surrender/",
			data=json.dumps({'player_id': player['id']}),
			content_type='application/json',
		)
		self.assertEqual(repeated_surrender.status_code, 409)

	def test_training_curriculum_hides_answers_and_unlocks_lessons_in_order(self):
		player = self.create_player('TrainingStudent')
		self.assertEqual(len({lesson['level'] for lesson in LESSONS}), 5)
		self.assertEqual(len(LESSONS), 50)
		self.assertEqual(len({lesson['id'] for lesson in LESSONS}), 50)
		for level in range(1, 6):
			self.assertEqual(sum(lesson['level'] == level for lesson in LESSONS), 10)
		exercise_positions = set()
		for lesson in LESSONS:
			board = lesson_position(lesson)
			solution = chess.Move.from_uci(lesson['solution'])
			self.assertIn(solution, board.legal_moves)
			exercise_positions.add((board.board_fen(), board.turn, board.castling_rights, solution.uci()))
			self.assertEqual(len(lesson['hints']), 3)
			self.assertTrue(lesson['steps'])
			if re.search(r'\bmate\b', lesson['explanation'].lower()):
				board.push(solution)
				self.assertTrue(board.is_checkmate(), lesson['id'])
		self.assertEqual(len(exercise_positions), len(LESSONS))

		training_response = self.client.get(f"/api/players/{player['id']}/training/")
		self.assertEqual(training_response.status_code, 200)
		training = training_response.json()
		self.assertEqual(training['progress']['lessons_total'], 50)
		self.assertTrue(training['lessons'][0]['unlocked'])
		self.assertFalse(training['lessons'][1]['unlocked'])
		self.assertFalse(training['lessons'][2]['unlocked'])
		self.assertEqual(training['game_trend']['matches_reviewed'], 0)
		self.assertIsNone(training['game_trend']['focus'])
		self.assertNotIn(LESSONS[0]['solution'], json.dumps(training))

		incorrect_attempt = self.client.post(
			f"/api/players/{player['id']}/training/attempt/",
			data=json.dumps({'lesson_id': LESSONS[0]['id'], 'from': 'h5', 'to': 'h6'}),
			content_type='application/json',
		)
		self.assertEqual(incorrect_attempt.status_code, 200)
		self.assertFalse(incorrect_attempt.json()['correct'])
		self.assertEqual(incorrect_attempt.json()['progress']['attempts'], 1)

		correct_attempt = self.client.post(
			f"/api/players/{player['id']}/training/attempt/",
			data=json.dumps({'lesson_id': LESSONS[0]['id'], 'from': 'h5', 'to': 'f7'}),
			content_type='application/json',
		)
		self.assertEqual(correct_attempt.status_code, 200)
		self.assertTrue(correct_attempt.json()['correct'])
		self.assertTrue(TrainingLessonProgress.objects.get(
			player_id=player['id'], lesson_id=LESSONS[0]['id']
		).completed_at)

		updated_training = self.client.get(f"/api/players/{player['id']}/training/").json()
		self.assertTrue(updated_training['lessons'][1]['unlocked'])
		self.assertFalse(updated_training['lessons'][2]['unlocked'])
		self.assertEqual(updated_training['progress']['lessons_completed'], 1)
		self.assertEqual(updated_training['progress']['current_level'], 1)
		self.assertEqual(updated_training['progress']['training_xp'], 100)

		for lesson in LESSONS[1:10]:
			with self.subTest(lesson=lesson['id']):
				solution = chess.Move.from_uci(lesson['solution'])
				attempt = {
					'lesson_id': lesson['id'],
					'from': chess.square_name(solution.from_square),
					'to': chess.square_name(solution.to_square),
				}
				if solution.promotion:
					attempt['promotion'] = chess.piece_symbol(solution.promotion)
				response = self.client.post(
					f"/api/players/{player['id']}/training/attempt/",
					data=json.dumps(attempt),
					content_type='application/json',
				)
				self.assertEqual(response.status_code, 200)
				self.assertTrue(response.json()['correct'])
		level_two_training = self.client.get(f"/api/players/{player['id']}/training/").json()
		self.assertEqual(level_two_training['progress']['current_level'], 2)
		self.assertEqual(level_two_training['progress']['lessons_completed'], 10)
		self.assertEqual(level_two_training['progress']['training_xp'], 1000)
		self.assertTrue(level_two_training['lessons'][10]['unlocked'])
		self.assertFalse(level_two_training['lessons'][11]['unlocked'])

	def test_training_attempt_requires_previous_lesson_and_session_owner(self):
		player = self.create_player('TrainingGate')
		self.assertEqual(self.client.post(
			f"/api/players/{player['id']}/training/attempt/",
			data=json.dumps({'lesson_id': LESSONS[1]['id'], 'from': 'a1', 'to': 'a8'}),
			content_type='application/json',
		).status_code, 409)
		self.assertEqual(self.client.post(
			f"/api/players/{player['id']}/training/attempt/",
			data=json.dumps({'lesson_id': LESSONS[2]['id'], 'from': 'g5', 'to': 'f7'}),
			content_type='application/json',
		).status_code, 409)
		first_lesson = self.client.post(
			f"/api/players/{player['id']}/training/attempt/",
			data=json.dumps({'lesson_id': LESSONS[0]['id'], 'from': 'h5', 'to': 'f7'}),
			content_type='application/json',
		)
		self.assertEqual(first_lesson.status_code, 200)
		second_lesson = self.client.post(
			f"/api/players/{player['id']}/training/attempt/",
			data=json.dumps({'lesson_id': LESSONS[1]['id'], 'from': 'a1', 'to': 'a8'}),
			content_type='application/json',
		)
		self.assertEqual(second_lesson.status_code, 200)
		other_player = PlayerProfile.objects.create(username='TrainingOther')
		self.assertEqual(self.client.get(f'/api/players/{other_player.id}/training/').status_code, 403)

	def test_ai_match_uses_requested_difficulty_and_rejects_unknown_levels(self):
		player = self.create_player('DifficultyPlayer')
		match_response = self.client.post(
			'/api/matches/',
			data=json.dumps({
				'player_id': player['id'],
				'mode': GameMatch.Mode.AI,
				'difficulty': GameMatch.AIDifficulty.ADVANCED,
			}),
			content_type='application/json',
		)
		self.assertEqual(match_response.status_code, 201)
		self.assertEqual(match_response.json()['match']['ai_difficulty'], GameMatch.AIDifficulty.ADVANCED)

		invalid_response = self.client.post(
			'/api/matches/',
			data=json.dumps({
				'player_id': player['id'],
				'mode': GameMatch.Mode.AI,
				'difficulty': 'unbeatable',
			}),
			content_type='application/json',
		)
		self.assertEqual(invalid_response.status_code, 400)

	def test_ai_selector_returns_legal_moves_at_each_difficulty(self):
		for difficulty in GameMatch.AIDifficulty.values:
			with self.subTest(difficulty=difficulty):
				board = chess.Board()
				board.push_san('e4')
				move = choose_ai_move(board, difficulty)
				self.assertIn(move, board.legal_moves)

	def test_ai_selector_rejects_unknown_difficulty(self):
		with self.assertRaises(ValueError):
			choose_ai_move(chess.Board(), 'unbeatable')

	def test_match_review_requires_participation_and_finished_game(self):
		player_data = self.create_player('ReviewOwner')
		player = PlayerProfile.objects.get(id=player_data['id'])
		opponent = PlayerProfile.objects.create(username='ReviewOpponent')
		outsider = PlayerProfile.objects.create(username='ReviewOutsider')
		match = GameMatch.objects.create(
			white_player=player,
			black_player=opponent,
			status=GameMatch.Status.ACTIVE,
		)

		active_review = self.client.get(f'/api/matches/{match.id}/review/')
		self.assertEqual(active_review.status_code, 409)

		GameMatch.objects.filter(id=match.id).update(status=GameMatch.Status.COMPLETED)
		self.authenticate_as(outsider)
		private_review = self.client.get(f'/api/matches/{match.id}/review/')
		self.assertEqual(private_review.status_code, 403)

		self.client.defaults.pop('HTTP_AUTHORIZATION', None)
		unauthenticated_review = self.client.get(f'/api/matches/{match.id}/review/')
		self.assertEqual(unauthenticated_review.status_code, 401)

	def test_match_review_replays_finished_game_and_returns_annotations(self):
		player_data = self.create_player('ReviewWhite')
		player = PlayerProfile.objects.get(id=player_data['id'])
		opponent = PlayerProfile.objects.create(username='ReviewBlack')
		match = GameMatch.objects.create(
			white_player=player,
			black_player=opponent,
			status=GameMatch.Status.COMPLETED,
			result='black_win',
		)
		board = chess.Board()
		for move_number, notation in enumerate(('f3', 'e5', 'g4', 'Qh4#'), start=1):
			move = board.parse_san(notation)
			board.push(move)
			GameMove.objects.create(
				match=match,
				move_number=move_number,
				notation=notation,
				from_square=chess.square_name(move.from_square),
				to_square=chess.square_name(move.to_square),
				fen_after=board.fen(),
			)

		response = self.client.get(f'/api/matches/{match.id}/review/')

		self.assertEqual(response.status_code, 200)
		review = response.json()['review']
		self.assertEqual(review['match']['result'], 'black_win')
		self.assertEqual(review['summary']['plies_reviewed'], 4)
		self.assertEqual([move['notation'] for move in review['moves']], ['f3', 'e5', 'g4', 'Qh4#'])
		self.assertEqual(review['moves'][2]['quality'], 'blunder')
		self.assertIn('immediate checkmate Qh4#', review['moves'][2]['explanation'])
		self.assertEqual(review['moves'][3]['quality'], 'checkmate')
		self.assertEqual(review['summary']['blunders'], 1)
		self.assertEqual(review['summary']['mistakes'], 0)
		self.assertEqual(review['moves'][-1]['color'], 'black')
		self.assertEqual(review['moves'][-1]['player'], opponent.username)
		self.assertIn('not a full chess-engine evaluation', review['scope'])
		self.assertTrue(all('quality' in move and 'explanation' in move for move in review['moves']))
		self.assertTrue(chess.Board(review['moves'][-1]['fen']).is_checkmate())
		self.assertEqual(review['training_recommendation']['focus'], 'mating_threats')
		self.assertEqual(review['training_recommendation']['lesson_id'], 'mate-fundamentals')
		self.assertTrue(review['training_recommendation']['available_now'])

		self.authenticate_as(opponent)
		opponent_review = self.client.get(f'/api/matches/{match.id}/review/').json()['review']
		self.assertEqual(opponent_review['summary']['blunders'], 0)
		self.assertIsNone(opponent_review['training_recommendation'])

	def test_ai_match_review_identifies_the_ai_and_difficulty(self):
		player_data = self.create_player('ReviewAIPlayer')
		player = PlayerProfile.objects.get(id=player_data['id'])
		match = GameMatch.objects.create(
			white_player=player,
			mode=GameMatch.Mode.AI,
			ai_difficulty=GameMatch.AIDifficulty.INTERMEDIATE,
			status=GameMatch.Status.COMPLETED,
			result='black_wins',
		)
		board = chess.Board()
		for move_number, notation in enumerate(('f3', 'e5', 'g4', 'Qh4#'), start=1):
			move = board.parse_san(notation)
			board.push(move)
			GameMove.objects.create(
				match=match,
				move_number=move_number,
				notation=notation,
				from_square=chess.square_name(move.from_square),
				to_square=chess.square_name(move.to_square),
				fen_after=board.fen(),
			)

		response = self.client.get(f'/api/matches/{match.id}/review/')

		self.assertEqual(response.status_code, 200)
		review = response.json()['review']
		self.assertEqual(review['match']['mode'], GameMatch.Mode.AI)
		self.assertEqual(review['match']['ai_difficulty'], GameMatch.AIDifficulty.INTERMEDIATE)
		self.assertEqual(review['moves'][-1]['player'], 'Arena AI')

	def test_match_review_offers_a_playable_positional_alternative(self):
		board = chess.Board('3qk3/5N2/8/8/8/8/8/3RK3 w - - 0 1')
		played_move = board.parse_san('Kf1')

		analysis = _review_move(board, played_move)

		self.assertEqual((analysis['alternative_from'], analysis['alternative_to']), ('f7', 'd8'))
		alternative_board = board.copy()
		alternative_board.push_san(analysis['alternative'])
		self.assertEqual(alternative_board.piece_at(chess.D8).piece_type, chess.KNIGHT)
		self.assertEqual(alternative_board.fen(), analysis['alternative_fen'])
		self.assertIn('quick positional scan', analysis['alternative_explanation'])

	def test_missed_tactic_recommends_an_unlocked_matching_training_lesson(self):
		player = PlayerProfile.objects.create(username='ForkTrainingRecommendation')
		for lesson in LESSONS:
			if lesson['level'] == 1:
				TrainingLessonProgress.objects.create(
					player=player,
					lesson_id=lesson['id'],
					completed_at=timezone.now(),
				)
		recommendation = _training_recommendation(
			[{'quality': 'missed_tactic', 'explanation': 'Missed a fork.'}],
			player.id,
		)
		self.assertEqual(recommendation['focus'], 'missed_tactics')
		self.assertEqual(recommendation['lesson_id'], 'knight-fork')
		self.assertTrue(recommendation['available_now'])

	def test_training_game_trend_aggregates_recent_player_matches(self):
		player_data = self.create_player('GameTrendStudent')
		player = PlayerProfile.objects.get(id=player_data['id'])
		opponents = [
			PlayerProfile.objects.create(username=f'GameTrendOpponent{index}')
			for index in range(2)
		]
		for index, opponent in enumerate(opponents):
			match = GameMatch.objects.create(
				white_player=player,
				black_player=opponent,
				status=GameMatch.Status.COMPLETED,
				result='black_wins',
			)
			board = chess.Board()
			for move_number, notation in enumerate(('f3', 'e5', 'g4', 'Qh4#'), start=1):
				move = board.parse_san(notation)
				board.push(move)
				GameMove.objects.create(
					match=match,
					move_number=move_number,
					notation=notation,
					from_square=chess.square_name(move.from_square),
					to_square=chess.square_name(move.to_square),
					fen_after=board.fen(),
				)
		GameMatch.objects.create(white_player=player, status=GameMatch.Status.ACTIVE)

		response = self.client.get(f'/api/players/{player.id}/training/')

		self.assertEqual(response.status_code, 200)
		trend = response.json()['game_trend']
		self.assertEqual(trend['matches_reviewed'], 2)
		self.assertEqual(trend['focus'], 'mating_threats')
		self.assertEqual(trend['matches_with_focus'], 2)
		self.assertEqual(trend['recommendation']['lesson_id'], 'mate-fundamentals')
		self.assertTrue(trend['recommendation']['available_now'])

	def test_match_review_rejects_a_finished_match_without_moves(self):
		player_data = self.create_player('ReviewEmpty')
		player = PlayerProfile.objects.get(id=player_data['id'])
		match = GameMatch.objects.create(white_player=player, status=GameMatch.Status.COMPLETED)

		response = self.client.get(f'/api/matches/{match.id}/review/')

		self.assertEqual(response.status_code, 409)
		self.assertIn('no recorded moves', response.json()['error'])

	def test_quick_match_pairs_waiting_players_and_assigns_both_colors(self):
		first_player = self.create_player('QueueFirst')
		first_match = self.client.post(
			'/api/matches/',
			data=json.dumps({'mode': 'quick_match'}),
			content_type='application/json',
		)
		self.assertEqual(first_match.status_code, 201)
		self.assertEqual(first_match.json()['match']['status'], GameMatch.Status.WAITING)
		self.assertIsNone(first_match.json()['match']['black_player'])
		retried = self.client.post(
			'/api/matches/',
			data=json.dumps({'mode': 'quick_match'}),
			content_type='application/json',
		)
		self.assertEqual(retried.status_code, 200)
		self.assertEqual(retried.json()['match']['id'], first_match.json()['match']['id'])
		self.assertEqual(GameMatch.objects.filter(
			white_player_id=first_player['id'],
			mode=GameMatch.Mode.QUICK_MATCH,
			status=GameMatch.Status.WAITING,
		).count(), 1)

		second_player_response = self.client.post(
			'/api/players/guest/',
			data=json.dumps({'username': 'QueueSecond'}),
			content_type='application/json',
		)
		self.assertEqual(second_player_response.status_code, 201)
		second_player = second_player_response.json()['player']
		self.client.defaults['HTTP_AUTHORIZATION'] = f"Bearer {second_player_response.json()['session_token']}"
		paired = self.client.post(
			'/api/matches/',
			data=json.dumps({'mode': 'quick_match'}),
			content_type='application/json',
		)
		self.assertEqual(paired.status_code, 200)
		match = paired.json()['match']
		self.assertEqual(match['status'], GameMatch.Status.ACTIVE)
		self.assertEqual(
			{match['white_player']['id'], match['black_player']['id']},
			{first_player['id'], second_player['id']},
		)
		cancel_after_pairing = self.client.post(
			'/api/matches/cancel-queue/',
			data=json.dumps({'match_id': match['id']}),
			content_type='application/json',
		)
		self.assertEqual(cancel_after_pairing.status_code, 200)
		self.assertEqual(cancel_after_pairing.json()['status'], 'already_matched')
		self.assertEqual(cancel_after_pairing.json()['match']['status'], GameMatch.Status.ACTIVE)

	def test_waiting_player_can_cancel_queue_and_cannot_be_matched(self):
		self.create_player('QueueCancel')
		waiting = self.client.post(
			'/api/matches/',
			data=json.dumps({'mode': 'quick_match'}),
			content_type='application/json',
		).json()['match']
		cancelled = self.client.post(
			'/api/matches/cancel-queue/',
			data=json.dumps({'match_id': waiting['id']}),
			content_type='application/json',
		)
		self.assertEqual(cancelled.status_code, 200)
		self.assertEqual(cancelled.json()['status'], 'cancelled')
		self.assertEqual(
			GameMatch.objects.get(id=waiting['id']).status,
			GameMatch.Status.ABANDONED,
		)

		opponent = PlayerProfile.objects.create(username='QueueOpponent')
		self.authenticate_as(opponent)
		new_queue = self.client.post(
			'/api/matches/',
			data=json.dumps({'mode': 'quick_match'}),
			content_type='application/json',
		)
		self.assertEqual(new_queue.status_code, 201)
		self.assertNotEqual(new_queue.json()['match']['id'], waiting['id'])

	def test_stale_queue_expires_and_is_not_matched(self):
		self.create_player('QueueStale')
		stale_match = GameMatch.objects.create(
			white_player=PlayerProfile.objects.get(username='QueueStale'),
			mode=GameMatch.Mode.QUICK_MATCH,
			status=GameMatch.Status.WAITING,
		)
		GameMatch.objects.filter(id=stale_match.id).update(
			updated_at=timezone.now() - timedelta(minutes=6),
		)
		opponent = PlayerProfile.objects.create(username='FreshQueuePlayer')
		self.authenticate_as(opponent)
		response = self.client.post(
			'/api/matches/',
			data=json.dumps({'mode': 'quick_match'}),
			content_type='application/json',
		)
		self.assertEqual(response.status_code, 201)
		self.assertNotEqual(response.json()['match']['id'], str(stale_match.id))
		stale_match.refresh_from_db()
		self.assertEqual(stale_match.status, GameMatch.Status.ABANDONED)

	def test_illegal_move_and_unfinished_result_are_rejected(self):
		player = self.create_player()
		match = self.client.post(
			'/api/matches/',
			data=json.dumps({'mode': 'ai'}),
			content_type='application/json',
		).json()['match']
		move = self.client.post(
			f"/api/matches/{match['id']}/moves/",
			data=json.dumps({'from': 'e2', 'to': 'e5', 'fen': 'forged-fen'}),
			content_type='application/json',
		)
		self.assertEqual(move.status_code, 409)
		self.assertEqual(GameMatch.objects.get(id=match['id']).moves.count(), 0)
		completion = self.client.post(
			f"/api/matches/{match['id']}/complete/",
			data=json.dumps({'result': 'white_wins'}),
			content_type='application/json',
		)
		self.assertEqual(completion.status_code, 409)
		self.assertEqual(GameMatch.objects.get(id=match['id']).status, GameMatch.Status.ACTIVE)

	def test_match_rejects_moves_from_the_wrong_player_turn(self):
		white = PlayerProfile.objects.create(username='TurnWhite')
		black = PlayerProfile.objects.create(username='TurnBlack')
		match = GameMatch.objects.create(white_player=white, black_player=black)
		self.authenticate_as(white)
		first_move = self.client.post(
			f'/api/matches/{match.id}/moves/',
			data=json.dumps({'from': 'e2', 'to': 'e4'}),
			content_type='application/json',
		)
		self.assertEqual(first_move.status_code, 201)
		wrong_turn = self.client.post(
			f'/api/matches/{match.id}/moves/',
			data=json.dumps({'from': 'e7', 'to': 'e5'}),
			content_type='application/json',
		)
		self.assertEqual(wrong_turn.status_code, 403)
		self.assertEqual(GameMatch.objects.get(id=match.id).moves.count(), 1)

	def test_match_accepts_castling_and_en_passant_using_chess_rules(self):
		en_passant_white = PlayerProfile.objects.create(username='EnPassantWhite')
		en_passant_black = PlayerProfile.objects.create(username='EnPassantBlack')
		en_passant_match = GameMatch.objects.create(
			white_player=en_passant_white,
			black_player=en_passant_black,
		)
		en_passant_moves = (
			(en_passant_white, 'e2', 'e4'),
			(en_passant_black, 'a7', 'a6'),
			(en_passant_white, 'e4', 'e5'),
			(en_passant_black, 'd7', 'd5'),
			(en_passant_white, 'e5', 'd6'),
		)
		for move_number, (player, from_square, to_square) in enumerate(en_passant_moves, start=1):
			self.authenticate_as(player)
			response = self.client.post(
				f'/api/matches/{en_passant_match.id}/moves/',
				data=json.dumps({
					'move_number': move_number,
					'from': from_square,
					'to': to_square,
				}),
				content_type='application/json',
			)
			self.assertEqual(response.status_code, 201)
		self.assertEqual(response.json()['move']['notation'], 'exd6')
		en_passant_board = chess.Board(response.json()['match']['fen'])
		self.assertEqual(en_passant_board.piece_at(chess.parse_square('d6')), chess.Piece(chess.PAWN, chess.WHITE))
		self.assertIsNone(en_passant_board.piece_at(chess.parse_square('d5')))

		castle_white = PlayerProfile.objects.create(username='CastleWhite')
		castle_black = PlayerProfile.objects.create(username='CastleBlack')
		castle_match = GameMatch.objects.create(
			white_player=castle_white,
			black_player=castle_black,
		)
		castle_moves = (
			(castle_white, 'e2', 'e4'),
			(castle_black, 'e7', 'e5'),
			(castle_white, 'g1', 'f3'),
			(castle_black, 'b8', 'c6'),
			(castle_white, 'f1', 'c4'),
			(castle_black, 'g8', 'f6'),
			(castle_white, 'e1', 'g1'),
		)
		for move_number, (player, from_square, to_square) in enumerate(castle_moves, start=1):
			self.authenticate_as(player)
			response = self.client.post(
				f'/api/matches/{castle_match.id}/moves/',
				data=json.dumps({
					'move_number': move_number,
					'from': from_square,
					'to': to_square,
				}),
				content_type='application/json',
			)
			self.assertEqual(response.status_code, 201)
		self.assertEqual(response.json()['move']['notation'], 'O-O')
		castle_board = chess.Board(response.json()['match']['fen'])
		self.assertEqual(castle_board.piece_at(chess.parse_square('g1')), chess.Piece(chess.KING, chess.WHITE))
		self.assertEqual(castle_board.piece_at(chess.parse_square('f1')), chess.Piece(chess.ROOK, chess.WHITE))

	def test_match_chat_is_persisted_and_private_to_participants(self):
		white = PlayerProfile.objects.create(username='ChatWhite')
		black = PlayerProfile.objects.create(username='ChatBlack')
		outside = PlayerProfile.objects.create(username='ChatOutside')
		match = GameMatch.objects.create(
			white_player=white,
			black_player=black,
			status=GameMatch.Status.ACTIVE,
		)
		url = f'/api/matches/{match.id}/messages/'
		self.authenticate_as(white)
		sent = self.client.post(
			url,
			data=json.dumps({'message': 'Good luck!'}),
			content_type='application/json',
		)
		self.assertEqual(sent.status_code, 201)
		self.assertEqual(sent.json()['message']['username'], white.username)
		self.assertEqual(MatchMessage.objects.get(match=match).message, 'Good luck!')
		self.assertEqual(self.client.get(url).json()['messages'][0]['message'], 'Good luck!')
		waiting_match = GameMatch.objects.create(
			white_player=white,
			mode=GameMatch.Mode.MULTIPLAYER,
			status=GameMatch.Status.WAITING,
		)
		self.assertEqual(self.client.post(
			f'/api/matches/{waiting_match.id}/messages/',
			data=json.dumps({'message': 'Before you join'}),
			content_type='application/json',
		).status_code, 409)

		self.assertEqual(self.client.post(
			url,
			data=json.dumps({'message': ' ' * 3}),
			content_type='application/json',
		).status_code, 400)
		self.authenticate_as(outside)
		self.assertEqual(self.client.get(url).status_code, 403)
		self.assertEqual(self.client.post(
			url,
			data=json.dumps({'message': 'Private message'}),
			content_type='application/json',
		).status_code, 403)

	def test_checkmate_is_derived_and_completed_by_server(self):
		white = PlayerProfile.objects.create(username='WhitePlayer')
		black = PlayerProfile.objects.create(username='BlackPlayer')
		DailyChallengeSettings.objects.create(target=4, reward_coins=750)
		match = GameMatch.objects.create(
			white_player=white,
			black_player=black,
			mode=GameMatch.Mode.QUICK_MATCH,
		)
		moves = [
			(white, 'f2', 'f3'),
			(black, 'e7', 'e5'),
			(white, 'g2', 'g4'),
			(black, 'd8', 'h4'),
		]
		for move_number, (player, from_square, to_square) in enumerate(moves, start=1):
			self.authenticate_as(player)
			response = self.client.post(
				f'/api/matches/{match.id}/moves/',
				data=json.dumps({
					'move_number': move_number,
					'from': from_square,
					'to': to_square,
					'result': 'white_wins',
				}),
				content_type='application/json',
			)
			self.assertEqual(response.status_code, 201)
		match.refresh_from_db()
		self.assertEqual(match.status, GameMatch.Status.COMPLETED)
		self.assertEqual(match.result, 'black_wins')
		challenge = self.client.get(f'/api/players/{black.id}/daily-challenge/').json()['challenge']
		self.assertEqual((challenge['progress'], challenge['target'], challenge['reward_coins']), (1, 4, 750))
		self.authenticate_as(white)
		personal_plan = self.client.get(f'/api/players/{white.id}/training/').json()
		self.assertEqual(personal_plan['progress']['lessons_completed'], 0)
		self.assertTrue(personal_plan['lessons'][0]['unlocked'])
		final_move = self.client.get(f'/api/matches/{match.id}/').json()['match']
		self.assertEqual(final_move['termination'], 'checkmate')
		self.assertFalse(final_move['can_claim_draw'])
		rejected_after_mate = self.client.post(
			f'/api/matches/{match.id}/moves/',
			data=json.dumps({'from': 'e2', 'to': 'e4'}),
			content_type='application/json',
		)
		self.assertEqual(rejected_after_mate.status_code, 409)

	def test_claim_draw_after_threefold_repetition_and_lock_the_finished_game(self):
		white = PlayerProfile.objects.create(username='DrawClaimWhite')
		black = PlayerProfile.objects.create(username='DrawClaimBlack')
		match = GameMatch.objects.create(
			white_player=white,
			black_player=black,
			mode=GameMatch.Mode.QUICK_MATCH,
		)
		knight_cycle = (
			(white, 'g1', 'f3', 'Nf3'),
			(black, 'g8', 'f6', 'Nf6'),
			(white, 'f3', 'g1', 'Ng1'),
			(black, 'f6', 'g8', 'Ng8'),
		)
		for move_number in range(1, 9):
			player, from_square, to_square, _ = knight_cycle[(move_number - 1) % 4]
			self.authenticate_as(player)
			response = self.client.post(
				f'/api/matches/{match.id}/moves/',
				data=json.dumps({
					'move_number': move_number,
					'from': from_square,
					'to': to_square,
				}),
				content_type='application/json',
			)
			self.assertEqual(response.status_code, 201)

		current_match = self.client.get(f'/api/matches/{match.id}/').json()['match']
		self.assertTrue(current_match['can_claim_draw'])
		claimed = self.client.post(f'/api/matches/{match.id}/claim-draw/')

		self.assertEqual(claimed.status_code, 200)
		self.assertEqual(claimed.json()['match']['status'], GameMatch.Status.COMPLETED)
		self.assertEqual(claimed.json()['match']['result'], 'draw')
		self.assertEqual(claimed.json()['match']['termination'], 'threefold_repetition')
		reloaded_match = self.client.get(f'/api/matches/{match.id}/').json()['match']
		self.assertEqual(reloaded_match['termination'], 'threefold_repetition')
		rejected_after_draw = self.client.post(
			f'/api/matches/{match.id}/moves/',
			data=json.dumps({'from': 'e2', 'to': 'e4'}),
			content_type='application/json',
		)
		self.assertEqual(rejected_after_draw.status_code, 409)

	def test_draw_claim_is_rejected_until_a_chess_draw_can_be_claimed(self):
		player = self.create_player('NoDrawClaim')
		match = GameMatch.objects.create(
			white_player=PlayerProfile.objects.get(id=player['id']),
			mode=GameMatch.Mode.QUICK_MATCH,
		)

		response = self.client.post(f'/api/matches/{match.id}/claim-draw/')

		self.assertEqual(response.status_code, 409)
		self.assertEqual(GameMatch.objects.get(id=match.id).status, GameMatch.Status.ACTIVE)

	def test_automatic_draw_rules_end_stalemate_insufficient_and_seventyfive_move_games(self):
		positions = (
			(chess.Board('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1'), 'stalemate'),
			(chess.Board('7k/8/6K1/8/8/8/8/8 b - - 0 1'), 'insufficient_material'),
			(chess.Board('7k/8/6K1/8/8/8/8/6Q1 w - - 150 76'), 'seventyfive_moves'),
		)
		for board, termination in positions:
			with self.subTest(termination=termination):
				self.assertEqual(_board_termination(board), termination)
				self.assertEqual(_board_result(board), 'draw')

	def test_duplicate_username_is_rejected(self):
		self.create_player()
		response = self.client.post(
			'/api/players/guest/',
			data=json.dumps({'username': 'TestPlayer'}),
			content_type='application/json',
		)
		self.assertEqual(response.status_code, 409)

	def test_leaderboard_is_sorted_by_rating(self):
		first = PlayerProfile.objects.create(username='LowerRated', rating=1200)
		second = PlayerProfile.objects.create(username='HigherRated', rating=2100)
		response = self.client.get('/api/leaderboard/?limit=2')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['players'][0]['name'], second.username)
		self.assertEqual(response.json()['players'][1]['name'], first.username)

	def test_daily_challenge_is_created_for_player(self):
		player = PlayerProfile.objects.create(username='ChallengePlayer')
		self.authenticate_as(player)
		response = self.client.get(f'/api/players/{player.id}/daily-challenge/')
		self.assertEqual(response.status_code, 200)
		challenge = response.json()['challenge']
		self.assertEqual(challenge['progress'], 0)
		self.assertEqual(challenge['target'], 3)
		self.assertEqual(challenge['reward_coins'], 500)

	def test_daily_challenge_uses_admin_configured_target_and_reward(self):
		player = PlayerProfile.objects.create(username='ConfiguredChallengePlayer')
		DailyChallengeSettings.objects.create(target=4, reward_coins=750)
		self.authenticate_as(player)
		response = self.client.get(f'/api/players/{player.id}/daily-challenge/')
		self.assertEqual(response.status_code, 200)
		challenge = response.json()['challenge']
		self.assertEqual((challenge['target'], challenge['reward_coins']), (4, 750))
		record = DailyChallengeProgress.objects.get(player=player, date=timezone.localdate())
		record.progress = 4
		record.save(update_fields=['progress'])
		claimed = self.client.post(f'/api/players/{player.id}/daily-challenge/claim/')
		self.assertEqual(claimed.status_code, 200)
		player.refresh_from_db()
		self.assertEqual(player.coins, 1_250)

	def test_unfinished_match_cannot_be_completed_to_award_progress(self):
		player = PlayerProfile.objects.create(username='Winner')
		self.authenticate_as(player)
		match = GameMatch.objects.create(white_player=player, mode=GameMatch.Mode.QUICK_MATCH)
		payload = json.dumps({'player_id': str(player.id), 'result': 'white_wins'})
		first = self.client.post(f'/api/matches/{match.id}/complete/', data=payload, content_type='application/json')
		second = self.client.post(f'/api/matches/{match.id}/complete/', data=payload, content_type='application/json')
		self.assertEqual(first.status_code, 409)
		self.assertEqual(second.status_code, 409)
		challenge = self.client.get(f'/api/players/{player.id}/daily-challenge/').json()['challenge']
		self.assertEqual(challenge['progress'], 0)

	def test_daily_challenge_claim_requires_completion_and_awards_once(self):
		player = PlayerProfile.objects.create(username='Claimer', coins=500)
		self.authenticate_as(player)
		challenge_url = f'/api/players/{player.id}/daily-challenge/claim/'
		blocked = self.client.post(challenge_url)
		self.assertEqual(blocked.status_code, 409)
		challenge = player.daily_challenges.get(date=timezone.localdate())
		challenge.progress = 3
		challenge.save(update_fields=['progress'])
		first = self.client.post(challenge_url)
		second = self.client.post(challenge_url)
		self.assertEqual(first.status_code, 200)
		self.assertEqual(second.status_code, 200)
		player.refresh_from_db()
		challenge.refresh_from_db()
		self.assertEqual(player.coins, 1000)
		self.assertTrue(challenge.claimed)

	def test_notifications_friend_search_and_chat(self):
		sender = PlayerProfile.objects.create(username='Sender')
		receiver = PlayerProfile.objects.create(username='Receiver')
		self.authenticate_as(sender)
		search = self.client.get('/api/players/search/?q=Rece')
		self.assertEqual(search.json()['players'][0]['username'], 'Receiver')
		request = self.client.post('/api/friends/', data=json.dumps({'player_id': str(sender.id), 'friend_id': str(receiver.id)}), content_type='application/json')
		self.assertEqual(request.status_code, 201)
		self.authenticate_as(receiver)
		notifications = self.client.get(f'/api/players/{receiver.id}/notifications/')
		self.assertEqual(notifications.json()['notifications'][0]['message'], 'Sender sent you a friend request.')
		connection_id = notifications.json()['notifications'][0]['connection_id']
		accepted = self.client.post(f'/api/friends/{connection_id}/respond/', data=json.dumps({'player_id': str(receiver.id), 'action': 'accept'}), content_type='application/json')
		self.assertEqual(accepted.status_code, 200)
		self.authenticate_as(sender)
		self.assertEqual(len(self.client.get(f'/api/players/{sender.id}/friends/').json()['friends']), 1)
		self.assertEqual(self.client.get(f'/api/players/{sender.id}/notifications/').json()['notifications'][0]['type'], 'friend_request_accepted')
		message = self.client.post(f'/api/players/{sender.id}/friends/{receiver.id}/messages/', data=json.dumps({'message': 'Ready for a match?'}), content_type='application/json')
		self.assertEqual(message.status_code, 201)
		self.assertEqual(self.client.get(f'/api/players/{sender.id}/friends/{receiver.id}/messages/').json()['messages'][0]['message'], 'Ready for a match?')

	def test_notifications_can_be_marked_read_only_by_their_owner(self):
		owner = PlayerProfile.objects.create(username='NotificationOwner')
		other = PlayerProfile.objects.create(username='NotificationOther')
		first = Notification.objects.create(player=owner, message='First notice')
		second = Notification.objects.create(player=owner, message='Second notice')
		Notification.objects.create(player=other, message='Private notice')
		self.authenticate_as(owner)

		list_response = self.client.get(f'/api/players/{owner.id}/notifications/')
		self.assertEqual(list_response.status_code, 200)
		self.assertEqual(list_response.json()['unread_count'], 2)
		self.assertEqual(len(list_response.json()['notifications']), 2)

		marked = self.client.post(f'/api/players/{owner.id}/notifications/{first.id}/read/')
		self.assertEqual(marked.status_code, 200)
		self.assertEqual(marked.json()['unread_count'], 1)
		self.assertTrue(Notification.objects.get(id=first.id).read)

		forbidden = self.client.post(f'/api/players/{other.id}/notifications/{second.id}/read/')
		self.assertEqual(forbidden.status_code, 403)
		self.assertFalse(Notification.objects.get(id=second.id).read)

		missing = self.client.post(f'/api/players/{owner.id}/notifications/99999/read/')
		self.assertEqual(missing.status_code, 404)

		read_all = self.client.post(f'/api/players/{owner.id}/notifications/read-all/')
		self.assertEqual(read_all.status_code, 200)
		self.assertEqual(read_all.json()['unread_count'], 0)
		self.assertFalse(owner.notifications.filter(read=False).exists())

	def test_friend_and_match_responses_mark_the_related_notification_read(self):
		sender = PlayerProfile.objects.create(username='RequestNotificationSender')
		receiver = PlayerProfile.objects.create(username='RequestNotificationReceiver')
		connection = FriendConnection.objects.create(sender=sender, receiver=receiver)
		friend_notice = Notification.objects.create(
			player=receiver,
			actor=sender,
			connection=connection,
			notification_type='friend_request',
			message='Friend request',
		)
		self.authenticate_as(receiver)
		self.assertEqual(self.client.post(
			f'/api/friends/{connection.id}/respond/',
			data=json.dumps({'action': 'accept'}),
			content_type='application/json',
		).status_code, 200)
		friend_notice.refresh_from_db()
		self.assertTrue(friend_notice.read)

		match = GameMatch.objects.create(
			white_player=sender,
			black_player=receiver,
			mode=GameMatch.Mode.MULTIPLAYER,
			status=GameMatch.Status.WAITING,
		)
		challenge_notice = Notification.objects.create(
			player=receiver,
			actor=sender,
			match=match,
			notification_type='match_challenge',
			message='Match challenge',
		)
		self.assertEqual(self.client.post(
			f'/api/matches/{match.id}/challenge-response/',
			data=json.dumps({'action': 'reject'}),
			content_type='application/json',
		).status_code, 200)
		challenge_notice.refresh_from_db()
		self.assertTrue(challenge_notice.read)

	def test_friend_challenge_notifies_receiver_and_can_be_accepted(self):
		sender = PlayerProfile.objects.create(username='Challenger')
		receiver = PlayerProfile.objects.create(username='Opponent')
		FriendConnection.objects.create(sender=sender, receiver=receiver, status=FriendConnection.Status.ACCEPTED)
		self.authenticate_as(sender)
		challenge = self.client.post('/api/friends/challenge/', data=json.dumps({'player_id': str(sender.id), 'friend_id': str(receiver.id)}), content_type='application/json')
		self.assertEqual(challenge.status_code, 201)
		match_id = challenge.json()['match_id']
		self.authenticate_as(receiver)
		notice = self.client.get(f'/api/players/{receiver.id}/notifications/').json()['notifications'][0]
		self.assertEqual(notice['type'], 'match_challenge')
		accepted = self.client.post(f'/api/matches/{match_id}/challenge-response/', data=json.dumps({'player_id': str(receiver.id), 'action': 'accept'}), content_type='application/json')
		self.assertEqual(accepted.status_code, 200)

	def test_protected_routes_require_session_and_reject_impersonation(self):
		player = PlayerProfile.objects.create(username='Owner')
		other = PlayerProfile.objects.create(username='ImpersonatorTarget')
		url = f'/api/players/{player.id}/daily-challenge/'
		self.assertEqual(self.client.get(url).status_code, 401)

		self.authenticate_as(other)
		self.assertEqual(self.client.get(url).status_code, 403)
		spoofed_request = self.client.post(
			'/api/friends/',
			data=json.dumps({'player_id': str(player.id), 'friend_id': str(other.id)}),
			content_type='application/json',
		)
		self.assertEqual(spoofed_request.status_code, 403)

	def test_expired_and_revoked_sessions_are_rejected(self):
		player = PlayerProfile.objects.create(username='SessionOwner')
		self.authenticate_as(player)
		session = PlayerSession.objects.get(player=player)
		session.expires_at = timezone.now() - timedelta(seconds=1)
		session.save(update_fields=['expires_at'])
		self.assertEqual(self.client.get(f'/api/players/{player.id}/daily-challenge/').status_code, 401)

		token = self.authenticate_as(player)
		logout = self.client.post('/api/auth/logout/')
		self.assertEqual(logout.status_code, 200)
		self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
		self.assertEqual(self.client.get(f'/api/players/{player.id}/daily-challenge/').status_code, 401)

	def test_non_friends_cannot_read_or_send_private_messages(self):
		player = PlayerProfile.objects.create(username='ChatOwner')
		other = PlayerProfile.objects.create(username='NotFriend')
		self.authenticate_as(player)
		url = f'/api/players/{player.id}/friends/{other.id}/messages/'
		self.assertEqual(self.client.get(url).status_code, 403)
		response = self.client.post(
			url,
			data=json.dumps({'message': 'Hello'}),
			content_type='application/json',
		)
		self.assertEqual(response.status_code, 403)

	@override_settings(
		GOOGLE_CLIENT_ID='test-google-client-id',
		GOOGLE_CLIENT_SECRET='test-google-client-secret',
		GOOGLE_REDIRECT_URI='http://127.0.0.1:8000/api/auth/google/callback/',
		FRONTEND_URL='http://127.0.0.1:5173',
	)
	@patch('api.views.urlopen')
	def test_google_oauth_callback_creates_account_and_one_time_login_ticket(self, mock_urlopen):
		state = secrets.token_urlsafe(24)
		session = self.client.session
		session['google_oauth_state'] = state
		session.save()
		profile = {
			'aud': 'test-google-client-id',
			'iss': 'https://accounts.google.com',
			'sub': 'google-user-subject-123',
			'email': 'chess-player@example.com',
			'email_verified': 'true',
			'exp': str(int((timezone.now() + timedelta(minutes=5)).timestamp())),
			'name': 'Chess Player',
		}
		mock_urlopen.side_effect = [
			io.BytesIO(json.dumps({'id_token': 'verified-id-token'}).encode()),
			io.BytesIO(json.dumps(profile).encode()),
		]

		callback = self.client.get(
			'/api/auth/google/callback/',
			{'code': 'authorization-code', 'state': state},
		)
		self.assertEqual(callback.status_code, 302)
		self.assertTrue(callback['Location'].startswith('http://127.0.0.1:5173/auth/callback#ticket='))

		ticket = parse_qs(urlparse(callback['Location']).fragment)['ticket'][0]
		exchange = self.client.post(
			'/api/auth/google/exchange/',
			data=json.dumps({'ticket': ticket}),
			content_type='application/json',
		)
		self.assertEqual(exchange.status_code, 200)
		self.assertEqual(exchange.json()['player']['username'], 'ChessPlayer')
		self.assertTrue(PlayerProfile.objects.filter(google_sub=profile['sub']).exists())

		reuse = self.client.post(
			'/api/auth/google/exchange/',
			data=json.dumps({'ticket': ticket}),
			content_type='application/json',
		)
		self.assertEqual(reuse.status_code, 401)

	@override_settings(
		GOOGLE_CLIENT_ID='test-google-client-id',
		GOOGLE_CLIENT_SECRET='test-google-client-secret',
		FRONTEND_URL='http://127.0.0.1:5173',
	)
	@patch('api.views.urlopen')
	def test_google_oauth_rejects_state_mismatch(self, mock_urlopen):
		session = self.client.session
		session['google_oauth_state'] = 'expected-state'
		session.save()

		callback = self.client.get(
			'/api/auth/google/callback/',
			{'code': 'authorization-code', 'state': 'incorrect-state'},
		)
		self.assertEqual(callback.status_code, 302)
		self.assertIn('error=invalid_oauth_state', callback['Location'])
		mock_urlopen.assert_not_called()

	@override_settings(
		GOOGLE_CLIENT_ID='test-google-client-id',
		GOOGLE_CLIENT_SECRET='test-google-client-secret',
		GOOGLE_REDIRECT_URI='http://127.0.0.1:8000/api/auth/google/callback/',
		FRONTEND_URL='http://127.0.0.1:5173',
	)
	@patch('api.views.urlopen')
	def test_google_oauth_reports_rejected_code_exchange(self, mock_urlopen):
		state = secrets.token_urlsafe(24)
		session = self.client.session
		session['google_oauth_state'] = state
		session.save()
		mock_urlopen.side_effect = HTTPError(
			'https://oauth2.googleapis.com/token',
			401,
			'Unauthorized',
			None,
			io.BytesIO(b'{"error":"invalid_client"}'),
		)

		callback = self.client.get(
			'/api/auth/google/callback/',
			{'code': 'authorization-code', 'state': state},
		)
		self.assertEqual(callback.status_code, 302)
		self.assertIn('error=google_token_exchange_failed', callback['Location'])


class MatchWebSocketTests(TransactionTestCase):
	def create_session(self, player):
		token = secrets.token_urlsafe(32)
		PlayerSession.objects.create(
			player=player,
			token_hash=hashlib.sha256(token.encode('utf-8')).hexdigest(),
			expires_at=timezone.now() + timedelta(days=30),
		)
		return token

	def test_authenticated_match_participants_receive_live_match_updates(self):
		white = PlayerProfile.objects.create(username='SocketWhite')
		black = PlayerProfile.objects.create(username='SocketBlack')
		match = GameMatch.objects.create(
			white_player=white,
			black_player=black,
			status=GameMatch.Status.ACTIVE,
		)
		token = self.create_session(white)
		black_token = self.create_session(black)

		async def exercise_socket():
			white_socket = WebsocketCommunicator(
				application,
				f'/ws/matches/{match.id}/',
				subprotocols=['battle-chess.v1', f'auth.{token}'],
				headers=[(b'origin', b'http://localhost:5173')],
			)
			connected, protocol = await white_socket.connect()
			self.assertTrue(connected, msg=f'WebSocket rejected: {protocol!r}')
			self.assertEqual(protocol, 'battle-chess.v1')
			snapshot = await white_socket.receive_json_from()
			self.assertEqual(snapshot['type'], 'match_snapshot')
			self.assertEqual(snapshot['match']['id'], str(match.id))

			black_socket = WebsocketCommunicator(
				application,
				f'/ws/matches/{match.id}/',
				subprotocols=['battle-chess.v1', f'auth.{black_token}'],
				headers=[(b'origin', b'http://localhost:5173')],
			)
			connected, protocol = await black_socket.connect()
			self.assertTrue(connected)
			await black_socket.receive_json_from()

			self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
			response = await sync_to_async(self.client.post)(
				f'/api/matches/{match.id}/moves/',
				data=json.dumps({'from': 'e2', 'to': 'e4'}),
				content_type='application/json',
			)
			self.assertEqual(response.status_code, 201)
			white_update = await white_socket.receive_json_from()
			black_update = await black_socket.receive_json_from()
			self.assertEqual(white_update['type'], 'match_update')
			self.assertEqual(black_update['type'], 'match_update')
			self.assertEqual(black_update['move']['notation'], 'e4')
			self.assertEqual(black_update['match']['moves'][0]['notation'], 'e4')
			chat_response = await sync_to_async(self.client.post)(
				f'/api/matches/{match.id}/messages/',
				data=json.dumps({'message': 'Hello opponent'}),
				content_type='application/json',
			)
			self.assertEqual(chat_response.status_code, 201)
			white_chat = await white_socket.receive_json_from()
			black_chat = await black_socket.receive_json_from()
			self.assertEqual(white_chat['type'], 'chat_message')
			self.assertEqual(black_chat['message']['message'], 'Hello opponent')
			await white_socket.disconnect()
			await black_socket.disconnect()

		async_to_sync(exercise_socket)()

	def test_websocket_requires_valid_session_and_match_membership(self):
		player = PlayerProfile.objects.create(username='SocketOwner')
		outsider = PlayerProfile.objects.create(username='SocketOutsider')
		match = GameMatch.objects.create(
			white_player=player,
			black_player=PlayerProfile.objects.create(username='SocketOpponent'),
			status=GameMatch.Status.ACTIVE,
		)
		token = self.create_session(outsider)

		async def exercise_rejections():
			unauthenticated = WebsocketCommunicator(
				application,
				f'/ws/matches/{match.id}/',
				subprotocols=['battle-chess.v1'],
				headers=[(b'origin', b'http://localhost:5173')],
			)
			connected, _ = await unauthenticated.connect()
			self.assertFalse(connected)

			not_a_player = WebsocketCommunicator(
				application,
				f'/ws/matches/{match.id}/',
				subprotocols=['battle-chess.v1', f'auth.{token}'],
				headers=[(b'origin', b'http://localhost:5173')],
			)
			connected, _ = await not_a_player.connect()
			self.assertFalse(connected)

			bad_origin = WebsocketCommunicator(
				application,
				f'/ws/matches/{match.id}/',
				subprotocols=['battle-chess.v1', f'auth.{token}'],
				headers=[(b'origin', b'https://untrusted.example')],
			)
			connected, _ = await bad_origin.connect()
			self.assertFalse(connected)

		async_to_sync(exercise_rejections)()
