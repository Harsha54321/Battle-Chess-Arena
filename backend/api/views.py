import json
import hashlib
import logging
import secrets
from datetime import timedelta
from functools import wraps
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import chess
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.http import JsonResponse
from django.db import IntegrityError, models, transaction
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from redis.exceptions import RedisError

from .chess_ai import choose_ai_move
from .models import AuthLoginTicket, DailyChallengeProgress, DailyChallengeSettings, FriendConnection, FriendMessage, GameMatch, GameMove, MatchMessage, Notification, PlayerProfile, PlayerSession, TrainingLessonProgress
from .review import review_match, training_trend
from .training import LESSONS, lesson_data, lesson_position

logger = logging.getLogger(__name__)
QUICK_MATCH_QUEUE_TIMEOUT = timedelta(minutes=5)


def _json_body(request):
	try:
		return json.loads(request.body or '{}')
	except json.JSONDecodeError:
		return None


def _player_data(player):
	return {
		'id': str(player.id),
		'username': player.username,
		'avatar': player.avatar,
		'rating': player.rating,
		'level': player.level,
		'coins': player.coins,
	}


def _auth_callback_url(error=None, ticket=None):
	if error:
		return f'{settings.FRONTEND_URL}/auth/callback?{urlencode({"error": error})}'
	return f'{settings.FRONTEND_URL}/auth/callback#{urlencode({"ticket": ticket})}'


def _google_json_request(url, data=None):
	request = Request(
		url,
		data=urlencode(data).encode('utf-8') if data is not None else None,
		headers={'Content-Type': 'application/x-www-form-urlencoded'} if data is not None else {},
	)
	with urlopen(request, timeout=10) as response:
		return json.loads(response.read().decode('utf-8'))


def _google_error_code(error):
	try:
		response_body = json.loads(error.read().decode('utf-8'))
	except (json.JSONDecodeError, UnicodeDecodeError, OSError):
		return 'unknown'
	code = response_body.get('error') if isinstance(response_body, dict) else None
	return code if isinstance(code, str) and code.isascii() and code.replace('_', '').isalnum() else 'unknown'


def _google_player(profile):
	google_sub = profile['sub']
	username_base = ''.join(
		char for char in (profile.get('name') or profile.get('email', '').split('@')[0])
		if char.isalnum() or char in {'_', '-'}
	).strip('_-')[:30] or 'ChessPlayer'

	with transaction.atomic():
		player = PlayerProfile.objects.filter(google_sub=google_sub).first()
		if player:
			return player

		username = username_base
		suffix = 1
		while PlayerProfile.objects.filter(username=username).exists():
			suffix += 1
			username = f'{username_base[:39 - len(str(suffix))]}{suffix}'
		return PlayerProfile.objects.create(username=username, google_sub=google_sub)


@require_http_methods(['GET'])
def google_auth_start(request):
	if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
		return redirect(_auth_callback_url(error='google_not_configured'))
	state = secrets.token_urlsafe(32)
	request.session['google_oauth_state'] = state
	params = urlencode({
		'client_id': settings.GOOGLE_CLIENT_ID,
		'redirect_uri': settings.GOOGLE_REDIRECT_URI,
		'response_type': 'code',
		'scope': 'openid email profile',
		'state': state,
		'access_type': 'online',
		'prompt': 'select_account',
	})
	return redirect(f'https://accounts.google.com/o/oauth2/v2/auth?{params}')


@require_http_methods(['GET'])
def google_auth_callback(request):
	expected_state = request.session.pop('google_oauth_state', None)
	if request.GET.get('error'):
		return redirect(_auth_callback_url(error='google_sign_in_cancelled'))
	if not expected_state or not secrets.compare_digest(expected_state, request.GET.get('state', '')):
		return redirect(_auth_callback_url(error='invalid_oauth_state'))
	if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
		return redirect(_auth_callback_url(error='google_not_configured'))

	code = request.GET.get('code')
	if not code:
		return redirect(_auth_callback_url(error='missing_authorization_code'))

	try:
		try:
			token_response = _google_json_request('https://oauth2.googleapis.com/token', {
				'code': code,
				'client_id': settings.GOOGLE_CLIENT_ID,
				'client_secret': settings.GOOGLE_CLIENT_SECRET,
				'redirect_uri': settings.GOOGLE_REDIRECT_URI,
				'grant_type': 'authorization_code',
			})
		except HTTPError as error:
			logger.warning(
				'Google OAuth code exchange rejected (status=%d, code=%s)',
				error.code,
				_google_error_code(error),
			)
			return redirect(_auth_callback_url(error='google_token_exchange_failed'))
		if not isinstance(token_response, dict):
			logger.warning('Google OAuth token exchange returned an invalid response.')
			return redirect(_auth_callback_url(error='google_verification_failed'))
		id_token = token_response.get('id_token')
		if not id_token:
			logger.warning('Google OAuth token exchange did not return an ID token.')
			return redirect(_auth_callback_url(error='google_verification_failed'))

		try:
			profile = _google_json_request(
				'https://oauth2.googleapis.com/tokeninfo?' + urlencode({'id_token': id_token})
			)
		except HTTPError as error:
			logger.warning(
				'Google OAuth ID token rejected (status=%d, code=%s)',
				error.code,
				_google_error_code(error),
			)
			return redirect(_auth_callback_url(error='google_id_token_rejected'))
	except (URLError, TimeoutError, json.JSONDecodeError, OSError) as error:
		logger.warning('Google OAuth provider request failed (%s)', type(error).__name__)
		return redirect(_auth_callback_url(error='google_provider_unavailable'))
	if not isinstance(profile, dict):
		logger.warning('Google OAuth ID token verification returned an invalid response.')
		return redirect(_auth_callback_url(error='google_verification_failed'))

	try:
		token_expires_at = int(profile.get('exp', '0'))
	except (TypeError, ValueError):
		token_expires_at = 0
	valid_issuer = profile.get('iss') in {'accounts.google.com', 'https://accounts.google.com'}
	invalid_claims = [
		name for name, valid in (
			('audience', profile.get('aud') == settings.GOOGLE_CLIENT_ID),
			('issuer', valid_issuer),
			('subject', bool(profile.get('sub'))),
			('email_verified', profile.get('email_verified') == 'true'),
			('expiry', token_expires_at > int(timezone.now().timestamp())),
		) if not valid
	]
	if invalid_claims:
		logger.warning('Google OAuth ID token claims rejected: %s', ','.join(invalid_claims))
		return redirect(_auth_callback_url(error='google_verification_failed'))

	player = _google_player(profile)
	ticket = secrets.token_urlsafe(32)
	AuthLoginTicket.objects.create(
		player=player,
		token_hash=hashlib.sha256(ticket.encode('utf-8')).hexdigest(),
		expires_at=timezone.now() + timedelta(minutes=1),
	)
	return redirect(_auth_callback_url(ticket=ticket))


@csrf_exempt
@require_http_methods(['POST'])
def exchange_google_login_ticket(request):
	body = _json_body(request)
	ticket = body.get('ticket') if isinstance(body, dict) else None
	if not isinstance(ticket, str) or not ticket:
		return JsonResponse({'error': 'A valid login ticket is required.'}, status=400)

	ticket_hash = hashlib.sha256(ticket.encode('utf-8')).hexdigest()
	try:
		with transaction.atomic():
			login_ticket = AuthLoginTicket.objects.select_for_update().select_related('player').get(
				token_hash=ticket_hash,
				expires_at__gt=timezone.now(),
			)
			player = login_ticket.player
			login_ticket.delete()
			session_token = secrets.token_urlsafe(32)
			PlayerSession.objects.create(
				player=player,
				token_hash=hashlib.sha256(session_token.encode('utf-8')).hexdigest(),
				expires_at=timezone.now() + timedelta(days=30),
			)
	except AuthLoginTicket.DoesNotExist:
		return JsonResponse({'error': 'Login ticket is invalid, expired, or already used.'}, status=401)
	return JsonResponse({'player': _player_data(player), 'session_token': session_token})


def require_player_session(view):
	@wraps(view)
	def wrapped(request, *args, **kwargs):
		authorization = request.headers.get('Authorization', '')
		scheme, separator, token = authorization.partition(' ')
		if scheme.lower() != 'bearer' or not separator or not token:
			return JsonResponse({'error': 'Authentication required.'}, status=401)

		token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
		session = PlayerSession.objects.select_related('player').filter(
			token_hash=token_hash,
			expires_at__gt=timezone.now(),
		).first()
		if not session:
			return JsonResponse({'error': 'Session is invalid or expired. Please sign in again.'}, status=401)
		if session.player.is_suspended:
			return JsonResponse({'error': 'This player account is suspended.'}, status=403)

		request.player = session.player
		request.player_session = session
		path_player_id = kwargs.get('player_id')
		if path_player_id and str(path_player_id) != str(session.player_id):
			return JsonResponse({'error': 'You are not authorized to access this player.'}, status=403)

		body = _json_body(request) if request.method in {'POST', 'PUT', 'PATCH'} else None
		body_player_id = body.get('player_id') if isinstance(body, dict) else None
		if body_player_id and str(body_player_id) != str(session.player_id):
			return JsonResponse({'error': 'You cannot act as another player.'}, status=403)
		return view(request, *args, **kwargs)

	return wrapped


def _board_termination(board):
	if board.is_checkmate():
		return 'checkmate'
	if board.is_stalemate():
		return 'stalemate'
	if board.is_insufficient_material():
		return 'insufficient_material'
	if board.is_seventyfive_moves():
		return 'seventyfive_moves'
	if board.is_fivefold_repetition():
		return 'fivefold_repetition'
	return None


def _match_data(match, board=None):
	board = board or _board_from_match(match)
	termination = _board_termination(board)
	if match.status == GameMatch.Status.COMPLETED and match.result == 'draw' and not termination:
		if board.can_claim_threefold_repetition():
			termination = 'threefold_repetition'
		elif board.can_claim_fifty_moves():
			termination = 'fifty_moves'
	return {
		'id': str(match.id),
		'mode': match.mode,
		'ai_difficulty': match.ai_difficulty,
		'status': match.status,
		'fen': board.fen(),
		'result': match.result,
		'termination': 'resignation' if (
			match.status == GameMatch.Status.ABANDONED and match.result
		) else termination,
		'can_claim_draw': match.status == GameMatch.Status.ACTIVE and board.can_claim_draw(),
		'white_player': _player_data(match.white_player),
		'black_player': _player_data(match.black_player) if match.black_player else None,
		'moves': [
			{
				'move_number': move.move_number,
				'notation': move.notation,
				'from': move.from_square,
				'to': move.to_square,
				'fen': move.fen_after,
			}
			for move in match.moves.all()
		],
	}


def _board_from_match(match):
	board = chess.Board()
	for move_number, move in enumerate(match.moves.all(), start=1):
		if move.move_number != move_number:
			raise ValueError('Match move numbers are not sequential.')
		if board.is_game_over():
			raise ValueError('Match contains moves after the game ended.')
		parsed_move = board.parse_san(move.notation)
		if (
			chess.square_name(parsed_move.from_square) != move.from_square
			or chess.square_name(parsed_move.to_square) != move.to_square
		):
			raise ValueError('Match move coordinates do not match the notation.')
		board.push(parsed_move)
	return board


def _board_result(board):
	if not board.is_game_over():
		return None
	if board.is_checkmate():
		return 'black_wins' if board.turn == chess.WHITE else 'white_wins'
	return 'draw'


def _finish_match(match, result):
	match.status = GameMatch.Status.COMPLETED
	match.result = result
	match.save(update_fields=['status', 'result', 'updated_at'])
	if match.mode == GameMatch.Mode.QUICK_MATCH and result != 'draw':
		winner_id = match.white_player_id if result == 'white_wins' else match.black_player_id
		if winner_id:
			settings = DailyChallengeSettings.get_current()
			challenge, _ = DailyChallengeProgress.objects.get_or_create(
				player_id=winner_id,
				date=timezone.localdate(),
				defaults={'target': settings.target, 'reward_coins': settings.reward_coins},
			)
			challenge.progress = min(challenge.progress + 1, challenge.target)
			challenge.save(update_fields=['progress'])


def _broadcast_match_update(match_id, payload):
	channel_layer = get_channel_layer()
	try:
		async_to_sync(channel_layer.group_send)(
			f'match_{str(match_id).replace("-", "")}',
			{'type': 'match.update', 'payload': payload},
		)
	except (OSError, RedisError, TimeoutError) as error:
		logger.warning(
			'Match update broadcast failed (match_id=%s, error=%s).',
			match_id,
			type(error).__name__,
		)


def health(request):
	return JsonResponse({'status': 'ok', 'service': 'battle-chess-api'})

@csrf_exempt
@require_http_methods(['POST'])
def create_guest_player(request):
	body = _json_body(request)
	if body is None:
		return JsonResponse({'error': 'Request body must be valid JSON.'}, status=400)

	username = str(body.get('username', '')).strip()
	avatar = str(body.get('avatar', 'king')).strip() or 'king'
	if not username or len(username) > 40:
		return JsonResponse({'error': 'username is required and must be 40 characters or fewer.'}, status=400)
	if PlayerProfile.objects.filter(username=username).exists():
		return JsonResponse({'error': 'That username is already in use.'}, status=409)

	player = PlayerProfile.objects.create(username=username, avatar=avatar[:10])
	token = secrets.token_urlsafe(32)
	PlayerSession.objects.create(
		player=player,
		token_hash=hashlib.sha256(token.encode('utf-8')).hexdigest(),
		expires_at=timezone.now() + timedelta(days=30),
	)
	return JsonResponse({'player': _player_data(player), 'session_token': token}, status=201)


@csrf_exempt
@require_http_methods(['POST'])
@require_player_session
def logout_session(request):
	request.player_session.delete()
	return JsonResponse({'status': 'signed_out'})

@require_http_methods(['GET'])
def player_detail(request, player_id):
	try:
		player = PlayerProfile.objects.get(id=player_id)
	except PlayerProfile.DoesNotExist:
		return JsonResponse({'error': 'Player not found.'}, status=404)
	return JsonResponse({'player': _player_data(player)})


@require_http_methods(['GET'])
@require_player_session
def player_profile_summary(request, player_id):
	player = request.player
	matches = GameMatch.objects.filter(
		(models.Q(white_player=player) | models.Q(black_player=player)),
		status__in=[GameMatch.Status.COMPLETED, GameMatch.Status.ABANDONED],
		result__in=['white_wins', 'black_wins', 'draw'],
	)
	wins = matches.filter(
		models.Q(white_player=player, result='white_wins')
		| models.Q(black_player=player, result='black_wins')
	).count()
	losses = matches.filter(
		models.Q(white_player=player, result='black_wins')
		| models.Q(black_player=player, result='white_wins')
	).count()
	draws = matches.filter(result='draw').count()
	matches_played = wins + losses + draws
	lesson_ids = [lesson['id'] for lesson in LESSONS]
	lessons_completed = TrainingLessonProgress.objects.filter(
		player=player,
		lesson_id__in=lesson_ids,
		completed_at__isnull=False,
	).count()
	achievements = []
	if wins >= 1:
		achievements.append({
			'id': 'first-victory',
			'title': 'First Victory',
			'description': 'Win your first recorded match.',
		})
	if wins >= 10:
		achievements.append({
			'id': 'ten-victories',
			'title': 'Ten Victories',
			'description': 'Win ten recorded matches.',
		})
	if lessons_completed >= 1:
		achievements.append({
			'id': 'first-lesson',
			'title': 'Chess Student',
			'description': 'Complete your first chess lesson.',
		})
	if lessons_completed >= 10:
		achievements.append({
			'id': 'ten-lessons',
			'title': 'Dedicated Learner',
			'description': 'Complete ten chess lessons.',
		})
	return JsonResponse({
		'player': _player_data(player),
		'stats': {
			'matches_played': matches_played,
			'wins': wins,
			'losses': losses,
			'draws': draws,
			'win_rate_percent': round(wins * 100 / matches_played) if matches_played else None,
		},
		'training': {
			'lessons_completed': lessons_completed,
			'lessons_total': len(LESSONS),
		},
		'achievements': achievements,
	})


@require_http_methods(['GET'])
@require_player_session
def daily_challenge(request, player_id):
	try:
		player = PlayerProfile.objects.get(id=player_id)
	except (PlayerProfile.DoesNotExist, ValueError):
		return JsonResponse({'error': 'Player not found.'}, status=404)
	settings = DailyChallengeSettings.get_current()
	challenge, _ = DailyChallengeProgress.objects.get_or_create(
		player=player,
		date=timezone.localdate(),
		defaults={'target': settings.target, 'reward_coins': settings.reward_coins},
	)
	return JsonResponse({
		'challenge': {
			'date': challenge.date.isoformat(),
			'progress': challenge.progress,
			'target': challenge.target,
			'reward_coins': challenge.reward_coins,
			'claimed': challenge.claimed,
		}
	})


@csrf_exempt
@require_http_methods(['POST'])
@require_player_session
def claim_daily_challenge(request, player_id):
	try:
		with transaction.atomic():
			player = PlayerProfile.objects.select_for_update().get(id=player_id)
			settings = DailyChallengeSettings.get_current()
			challenge, _ = DailyChallengeProgress.objects.select_for_update().get_or_create(
				player=player,
				date=timezone.localdate(),
				defaults={'target': settings.target, 'reward_coins': settings.reward_coins},
			)
			if not challenge.claimed and challenge.progress >= challenge.target:
				player.coins += challenge.reward_coins
				player.save(update_fields=['coins', 'updated_at'])
				challenge.claimed = True
				challenge.save(update_fields=['claimed'])
			elif challenge.progress < challenge.target:
				return JsonResponse({'error': 'Complete the daily challenge before claiming the reward.'}, status=409)
	except (PlayerProfile.DoesNotExist, ValueError):
		return JsonResponse({'error': 'Player not found.'}, status=404)
	return JsonResponse({'challenge': {
		'progress': challenge.progress,
		'target': challenge.target,
		'reward_coins': challenge.reward_coins,
		'claimed': challenge.claimed,
		'coins': player.coins,
	}})


def _friend_data(player):
	return {'id': str(player.id), 'username': player.username, 'avatar': player.avatar, 'rating': player.rating}


@require_http_methods(['GET'])
@require_player_session
def notifications(request, player_id):
	try:
		player = PlayerProfile.objects.get(id=player_id)
	except (PlayerProfile.DoesNotExist, ValueError):
		return JsonResponse({'error': 'Player not found.'}, status=404)
	items = player.notifications.select_related('actor').order_by('-created_at')[:30]
	return JsonResponse({'notifications': [
		{'id': item.id, 'message': item.message, 'read': item.read, 'type': item.notification_type,
		 'actor_id': str(item.actor_id) if item.actor_id else None,
		 'actor_username': item.actor.username if item.actor else None,
		 'connection_id': item.connection_id, 'match_id': str(item.match_id) if item.match_id else None,
		 'created_at': item.created_at.isoformat()}
		for item in items
	], 'unread_count': player.notifications.filter(read=False).count()})


@csrf_exempt
@require_http_methods(['POST'])
@require_player_session
def mark_notification_read(request, player_id, notification_id):
	if request.player.id != player_id:
		return JsonResponse({'error': 'Player cannot update another account’s notifications.'}, status=403)
	updated = Notification.objects.filter(
		id=notification_id,
		player=request.player,
		read=False,
	).update(read=True)
	if not updated and not Notification.objects.filter(
		id=notification_id,
		player=request.player,
	).exists():
		return JsonResponse({'error': 'Notification not found.'}, status=404)
	return JsonResponse({
		'status': 'read',
		'unread_count': request.player.notifications.filter(read=False).count(),
	})


@csrf_exempt
@require_http_methods(['POST'])
@require_player_session
def mark_all_notifications_read(request, player_id):
	if request.player.id != player_id:
		return JsonResponse({'error': 'Player cannot update another account’s notifications.'}, status=403)
	request.player.notifications.filter(read=False).update(read=True)
	return JsonResponse({
		'status': 'read',
		'unread_count': request.player.notifications.filter(read=False).count(),
	})


@require_http_methods(['GET'])
def search_players(request):
	query = request.GET.get('q', '').strip()
	players = PlayerProfile.objects.filter(username__icontains=query).order_by('username')[:20] if query else []
	return JsonResponse({'players': [_friend_data(player) for player in players]})


@csrf_exempt
@require_http_methods(['POST'])
@require_player_session
def add_friend(request):
	body = _json_body(request)
	try:
		sender = request.player
		receiver = PlayerProfile.objects.get(id=body.get('friend_id'))
	except (PlayerProfile.DoesNotExist, ValueError, TypeError, AttributeError):
		return JsonResponse({'error': 'Valid player_id and friend_id are required.'}, status=400)
	if sender.id == receiver.id:
		return JsonResponse({'error': 'You cannot add yourself.'}, status=400)
	connection, created = FriendConnection.objects.get_or_create(
		sender=sender,
		receiver=receiver,
		defaults={'status': FriendConnection.Status.PENDING},
	)
	if not created and connection.status == FriendConnection.Status.ACCEPTED:
		return JsonResponse({'error': 'You are already connected.'}, status=409)
	Notification.objects.create(player=receiver, actor=sender, connection=connection,
		notification_type='friend_request', message=f'{sender.username} sent you a friend request.')
	return JsonResponse({'friend': _friend_data(receiver), 'status': connection.status}, status=201 if created else 200)


@csrf_exempt
@require_http_methods(['POST'])
@require_player_session
def respond_friend_request(request, connection_id):
	body = _json_body(request)
	action = body.get('action') if body else None
	try:
		connection = FriendConnection.objects.select_related('sender', 'receiver').get(id=connection_id)
		player = request.player
	except (FriendConnection.DoesNotExist, ValueError, TypeError):
		return JsonResponse({'error': 'Friend request not found.'}, status=404)
	if not player or player.id != connection.receiver_id:
		return JsonResponse({'error': 'Only the recipient can respond.'}, status=403)
	if connection.status != FriendConnection.Status.PENDING:
		return JsonResponse({'error': 'This friend request was already handled.'}, status=409)
	if action not in {'accept', 'reject'}:
		return JsonResponse({'error': 'action must be accept or reject.'}, status=400)
	if action == 'reject':
		connection.delete()
	else:
		connection.status = FriendConnection.Status.ACCEPTED
		connection.save(update_fields=['status'])
		Notification.objects.filter(
			player=connection.receiver,
			connection=connection,
			notification_type='friend_request',
		).update(read=True)
		Notification.objects.create(player=connection.sender, actor=connection.receiver,
			connection=connection, notification_type='friend_request_accepted',
			message=f'{connection.receiver.username} accepted your friend request.')
	return JsonResponse({'status': action})


@require_http_methods(['GET'])
@require_player_session
def friends_list(request, player_id):
	try:
		player = PlayerProfile.objects.get(id=player_id)
	except (PlayerProfile.DoesNotExist, ValueError):
		return JsonResponse({'error': 'Player not found.'}, status=404)
	connections = FriendConnection.objects.filter(status=FriendConnection.Status.ACCEPTED).filter(
		models.Q(sender=player) | models.Q(receiver=player)
	).select_related('sender', 'receiver')
	friends = [connection.receiver if connection.sender_id == player.id else connection.sender for connection in connections]
	return JsonResponse({'friends': [_friend_data(friend) for friend in friends]})


@csrf_exempt
@require_http_methods(['POST'])
@require_player_session
def challenge_friend(request):
	body = _json_body(request)
	try:
		sender = request.player
		receiver = PlayerProfile.objects.get(id=body.get('friend_id'))
	except (PlayerProfile.DoesNotExist, ValueError, TypeError, AttributeError):
		return JsonResponse({'error': 'Valid player_id and friend_id are required.'}, status=400)
	connected = FriendConnection.objects.filter(status=FriendConnection.Status.ACCEPTED).filter(
		(models.Q(sender=sender, receiver=receiver) | models.Q(sender=receiver, receiver=sender))
	).exists()
	if not connected:
		return JsonResponse({'error': 'Accept the friend request before challenging this player.'}, status=403)
	match = GameMatch.objects.create(mode=GameMatch.Mode.MULTIPLAYER, status=GameMatch.Status.WAITING,
		white_player=sender, black_player=receiver)
	notification = Notification.objects.create(player=receiver, actor=sender, match=match,
		notification_type='match_challenge', message=f'{sender.username} challenged you to a match.')
	return JsonResponse({'match_id': str(match.id), 'notification_id': notification.id}, status=201)


@csrf_exempt
@require_http_methods(['POST'])
@require_player_session
def respond_challenge(request, match_id):
	body = _json_body(request)
	action = body.get('action') if body else None
	try:
		match = GameMatch.objects.get(id=match_id)
		player = request.player
	except (GameMatch.DoesNotExist, ValueError, TypeError):
		return JsonResponse({'error': 'Challenge not found.'}, status=404)
	if not player or player.id != match.black_player_id:
		return JsonResponse({'error': 'Only the challenged player can respond.'}, status=403)
	if match.status != GameMatch.Status.WAITING:
		return JsonResponse({'error': 'This challenge was already handled.'}, status=409)
	if action == 'accept':
		match.status = GameMatch.Status.ACTIVE
		match.save(update_fields=['status', 'updated_at'])
		Notification.objects.filter(
			player=player,
			match=match,
			notification_type='match_challenge',
		).update(read=True)
		Notification.objects.create(player=match.white_player, actor=player, match=match,
			notification_type='match_challenge_accepted', message=f'{player.username} accepted your match challenge.')
		return JsonResponse({'status': 'accepted', 'match_id': str(match.id)})
	if action == 'reject':
		match.status = GameMatch.Status.ABANDONED
		match.save(update_fields=['status', 'updated_at'])
		Notification.objects.filter(
			player=player,
			match=match,
			notification_type='match_challenge',
		).update(read=True)
		return JsonResponse({'status': 'rejected'})
	return JsonResponse({'error': 'action must be accept or reject.'}, status=400)


@csrf_exempt
@require_http_methods(['GET', 'POST'])
@require_player_session
def friend_messages(request, player_id, friend_id):
	try:
		sender = request.player
		receiver = PlayerProfile.objects.get(id=friend_id)
	except (PlayerProfile.DoesNotExist, ValueError):
		return JsonResponse({'error': 'Player not found.'}, status=404)
	connected = FriendConnection.objects.filter(status=FriendConnection.Status.ACCEPTED).filter(
		(models.Q(sender=sender, receiver=receiver) | models.Q(sender=receiver, receiver=sender))
	).exists()
	if not connected:
		return JsonResponse({'error': 'Messaging is available only between accepted friends.'}, status=403)
	if request.method == 'POST':
		body = _json_body(request)
		message = str(body.get('message', '')).strip() if body else ''
		if not message or len(message) > 500:
			return JsonResponse({'error': 'Message must be between 1 and 500 characters.'}, status=400)
		item = FriendMessage.objects.create(sender=sender, receiver=receiver, message=message)
		return JsonResponse({'message': {'id': item.id, 'sender_id': str(sender.id), 'message': item.message}}, status=201)
	items = FriendMessage.objects.filter(
		models.Q(sender=sender, receiver=receiver) | models.Q(sender=receiver, receiver=sender)
	).order_by('created_at')[:100]
	return JsonResponse({'messages': [{'id': item.id, 'sender_id': str(item.sender_id), 'message': item.message} for item in items]})


@require_http_methods(['GET'])
def leaderboard(request):
	try:
		limit = min(max(int(request.GET.get('limit', 5)), 1), 50)
	except ValueError:
		limit = 5
	players = PlayerProfile.objects.order_by('-rating', 'username')[:limit]
	return JsonResponse({
		'players': [
			{
				'rank': index,
				'name': player.username,
				'elo': player.rating,
				'avatar': player.avatar,
			}
			for index, player in enumerate(players, start=1)
		]
	})

@csrf_exempt
@require_http_methods(['POST'])
@require_player_session
def create_match(request):
	body = _json_body(request)
	if body is None:
		return JsonResponse({'error': 'Request body must be valid JSON.'}, status=400)

	player = request.player

	mode = body.get('mode', GameMatch.Mode.QUICK_MATCH)
	if mode not in GameMatch.Mode.values:
		return JsonResponse({'error': 'Unsupported match mode.'}, status=400)

	if mode != GameMatch.Mode.QUICK_MATCH:
		match_options = {'white_player': player, 'mode': mode}
		if mode == GameMatch.Mode.AI:
			difficulty = body.get('difficulty', GameMatch.AIDifficulty.BEGINNER)
			if difficulty not in GameMatch.AIDifficulty.values:
				return JsonResponse({'error': 'Unsupported AI difficulty.'}, status=400)
			match_options['ai_difficulty'] = difficulty
		match = GameMatch.objects.create(**match_options)
		return JsonResponse({'match': _match_data(match)}, status=201)

	with transaction.atomic():
		queue_cutoff = timezone.now() - QUICK_MATCH_QUEUE_TIMEOUT
		GameMatch.objects.filter(
			mode=GameMatch.Mode.QUICK_MATCH,
			status=GameMatch.Status.WAITING,
			black_player__isnull=True,
			updated_at__lt=queue_cutoff,
		).update(status=GameMatch.Status.ABANDONED)
		waiting_match = GameMatch.objects.select_for_update().filter(
			mode=GameMatch.Mode.QUICK_MATCH,
			status=GameMatch.Status.WAITING,
			black_player__isnull=True,
			white_player=player,
			updated_at__gte=queue_cutoff,
		).first()
		if waiting_match:
			return JsonResponse({'match': _match_data(waiting_match)}, status=200)

		candidates = GameMatch.objects.filter(
			mode=GameMatch.Mode.QUICK_MATCH,
			status=GameMatch.Status.WAITING,
			black_player__isnull=True,
			updated_at__gte=queue_cutoff,
		).exclude(white_player=player).order_by('created_at')
		for candidate in candidates:
			candidate = GameMatch.objects.select_for_update().get(id=candidate.id)
			first_player_id = candidate.white_player_id
			if secrets.randbelow(2):
				updated = GameMatch.objects.filter(
					id=candidate.id,
					status=GameMatch.Status.WAITING,
					black_player__isnull=True,
				).update(
					white_player=player,
					black_player_id=first_player_id,
					status=GameMatch.Status.ACTIVE,
				)
			else:
				updated = GameMatch.objects.filter(
					id=candidate.id,
					status=GameMatch.Status.WAITING,
					black_player__isnull=True,
				).update(black_player=player, status=GameMatch.Status.ACTIVE)
			if updated:
				match = GameMatch.objects.select_related(
					'white_player', 'black_player'
				).get(id=candidate.id)
				return JsonResponse({'match': _match_data(match)}, status=200)

		try:
			with transaction.atomic():
				match = GameMatch.objects.create(
					white_player=player,
					mode=GameMatch.Mode.QUICK_MATCH,
					status=GameMatch.Status.WAITING,
				)
		except IntegrityError:
			match = GameMatch.objects.filter(
				mode=GameMatch.Mode.QUICK_MATCH,
				status=GameMatch.Status.WAITING,
				black_player__isnull=True,
				white_player=player,
			).first()
			if not match:
				raise
			return JsonResponse({'match': _match_data(match)}, status=200)
	return JsonResponse({'match': _match_data(match)}, status=201)


@csrf_exempt
@require_http_methods(['POST'])
@require_player_session
def cancel_matchmaking(request):
	body = _json_body(request)
	match_id = body.get('match_id') if isinstance(body, dict) else None
	if not match_id:
		return JsonResponse({'error': 'match_id is required.'}, status=400)
	with transaction.atomic():
		try:
			match = GameMatch.objects.select_for_update().select_related(
				'white_player', 'black_player'
			).get(id=match_id)
		except (GameMatch.DoesNotExist, ValueError, TypeError):
			return JsonResponse({'error': 'Match not found.'}, status=404)
		if request.player.id not in {match.white_player_id, match.black_player_id}:
			return JsonResponse({'error': 'Player is not part of this match.'}, status=403)
		if match.status == GameMatch.Status.ACTIVE:
			return JsonResponse({'status': 'already_matched', 'match': _match_data(match)})
		if (
			match.mode != GameMatch.Mode.QUICK_MATCH
			or match.status != GameMatch.Status.WAITING
			or match.black_player_id
		):
			return JsonResponse({'status': 'not_waiting'})
		match.status = GameMatch.Status.ABANDONED
		match.save(update_fields=['status', 'updated_at'])
	return JsonResponse({'status': 'cancelled', 'match_id': str(match.id)})


@require_http_methods(['GET'])
@require_player_session
def match_detail(request, match_id):
	try:
		match = GameMatch.objects.select_related('white_player', 'black_player').prefetch_related('moves').get(id=match_id)
	except (GameMatch.DoesNotExist, ValueError):
		return JsonResponse({'error': 'Match not found.'}, status=404)
	if request.player.id not in {match.white_player_id, match.black_player_id}:
		return JsonResponse({'error': 'Player is not part of this match.'}, status=403)
	if (
		match.mode == GameMatch.Mode.QUICK_MATCH
		and match.status == GameMatch.Status.WAITING
		and match.black_player_id is None
		and match.updated_at < timezone.now() - QUICK_MATCH_QUEUE_TIMEOUT
	):
		GameMatch.objects.filter(
			id=match.id,
			status=GameMatch.Status.WAITING,
			black_player__isnull=True,
		).update(status=GameMatch.Status.ABANDONED)
		match.refresh_from_db()
	try:
		board = _board_from_match(match)
	except ValueError:
		return JsonResponse({'error': 'The stored match history is invalid.'}, status=409)
	match_data = _match_data(match, board)
	return JsonResponse({'match': match_data})


@require_http_methods(['GET'])
@require_player_session
def match_review(request, match_id):
	try:
		match = GameMatch.objects.select_related(
			'white_player', 'black_player'
		).prefetch_related('moves').get(id=match_id)
	except (GameMatch.DoesNotExist, ValueError, TypeError):
		return JsonResponse({'error': 'Match not found.'}, status=404)
	if request.player.id not in {match.white_player_id, match.black_player_id}:
		return JsonResponse({'error': 'Player is not part of this match.'}, status=403)
	if match.status not in {GameMatch.Status.COMPLETED, GameMatch.Status.ABANDONED}:
		return JsonResponse({'error': 'Review is available after the match has ended.'}, status=409)
	if not match.moves.exists():
		return JsonResponse({'error': 'This match has no recorded moves to review.'}, status=409)
	try:
		return JsonResponse({'review': review_match(match, request.player.id)})
	except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError):
		logger.error('Stored move history is invalid for match %s.', match.id)
		return JsonResponse({'error': 'The stored match history is invalid.'}, status=409)


@require_http_methods(['GET'])
@require_player_session
def player_training(request, player_id):
	player = request.player
	recent_matches = GameMatch.objects.filter(
		(models.Q(white_player=player) | models.Q(black_player=player)),
		status__in=[GameMatch.Status.COMPLETED, GameMatch.Status.ABANDONED],
	).order_by('-updated_at').prefetch_related('moves')[:10]
	game_trend = training_trend(recent_matches, player.id)
	progress_by_id = {
		progress.lesson_id: progress
		for progress in TrainingLessonProgress.objects.filter(player=player)
	}
	completed_ids = {
		lesson['id'] for lesson in LESSONS
		if progress_by_id.get(lesson['id']) and progress_by_id[lesson['id']].completed_at
	}
	next_lesson = next((lesson for lesson in LESSONS if lesson['id'] not in completed_ids), None)
	current_level = next_lesson['level'] if next_lesson else LESSONS[-1]['level']
	lesson_list = [
		lesson_data(
			lesson,
			progress_by_id.get(lesson['id']),
			unlocked=lesson['id'] in completed_ids or lesson is next_lesson,
		)
		for lesson in LESSONS
	]
	lessons_completed = len(completed_ids)
	return JsonResponse({
		'progress': {
			'lessons_completed': lessons_completed,
			'lessons_total': len(LESSONS),
			'training_xp': lessons_completed * 100,
			'current_level': current_level,
			'current_level_title': next_lesson['level_title'] if next_lesson else LESSONS[-1]['level_title'],
		},
		'game_trend': game_trend,
		'lessons': lesson_list,
	})


@csrf_exempt
@require_http_methods(['POST'])
@require_player_session
def submit_training_attempt(request, player_id):
	body = _json_body(request)
	if not isinstance(body, dict):
		return JsonResponse({'error': 'Request body must be valid JSON.'}, status=400)
	lesson_id = body.get('lesson_id')
	lesson = next((item for item in LESSONS if item['id'] == lesson_id), None)
	if lesson is None:
		return JsonResponse({'error': 'Training lesson not found.'}, status=404)
	lesson_index = LESSONS.index(lesson)
	previous_lessons = LESSONS[:lesson_index]
	completed_lesson_ids = set(TrainingLessonProgress.objects.filter(
		player=request.player,
		lesson_id__in=[item['id'] for item in previous_lessons],
		completed_at__isnull=False,
	).values_list('lesson_id', flat=True))
	if any(item['id'] not in completed_lesson_ids for item in previous_lessons):
		return JsonResponse({'error': 'Complete the previous lesson to unlock this one.'}, status=409)

	from_square = body.get('from')
	to_square = body.get('to')
	promotion = body.get('promotion', '')
	if (
		not isinstance(from_square, str)
		or from_square not in chess.SQUARE_NAMES
		or not isinstance(to_square, str)
		or to_square not in chess.SQUARE_NAMES
		or not isinstance(promotion, str)
		or promotion not in {'', 'q', 'r', 'b', 'n'}
	):
		return JsonResponse({'error': 'A valid from, to, and optional promotion are required.'}, status=400)
	board = lesson_position(lesson)
	try:
		move = chess.Move.from_uci(from_square + to_square + promotion)
	except ValueError:
		return JsonResponse({'error': 'The submitted move is invalid.'}, status=400)
	if move not in board.legal_moves:
		return JsonResponse({'error': 'That move is not legal in this puzzle position.'}, status=409)
	is_correct = move.uci() == lesson['solution']
	progress, _ = TrainingLessonProgress.objects.get_or_create(
		player=request.player,
		lesson_id=lesson_id,
	)
	progress.attempts += 1
	if is_correct and progress.completed_at is None:
		progress.completed_at = timezone.now()
	progress.save(update_fields=['attempts', 'completed_at', 'updated_at'])
	return JsonResponse({
		'correct': is_correct,
		'feedback': lesson['explanation'] if is_correct else (
			lesson['feedback']
		),
		'notation': board.san(move) if is_correct else None,
		'progress': {
			'attempts': progress.attempts,
			'completed': bool(progress.completed_at),
		},
	})


@csrf_exempt
@require_http_methods(['GET', 'POST'])
@require_player_session
def match_messages(request, match_id):
	try:
		match = GameMatch.objects.select_related('white_player', 'black_player').get(id=match_id)
	except (GameMatch.DoesNotExist, ValueError, TypeError):
		return JsonResponse({'error': 'Match not found.'}, status=404)
	player = request.player
	if player.id not in {match.white_player_id, match.black_player_id}:
		return JsonResponse({'error': 'Player is not part of this match.'}, status=403)

	if request.method == 'POST':
		if match.status != GameMatch.Status.ACTIVE:
			return JsonResponse({'error': 'Match chat is available only during an active match.'}, status=409)
		body = _json_body(request)
		message = body.get('message') if isinstance(body, dict) else None
		if not isinstance(message, str) or not message.strip() or len(message.strip()) > 500:
			return JsonResponse({'error': 'Message must be between 1 and 500 characters.'}, status=400)
		item = MatchMessage.objects.create(
			match=match,
			player=player,
			message=message.strip(),
		)
		data = {
			'id': item.id,
			'player_id': str(player.id),
			'username': player.username,
			'message': item.message,
			'created_at': item.created_at.isoformat(),
		}
		_broadcast_match_update(match.id, {'type': 'chat_message', 'message': data})
		return JsonResponse({'message': data}, status=201)

	items = match.messages.select_related('player').all()[:100]
	return JsonResponse({
		'messages': [{
			'id': item.id,
			'player_id': str(item.player_id),
			'username': item.player.username,
			'message': item.message,
			'created_at': item.created_at.isoformat(),
		} for item in items]
	})


@csrf_exempt
@require_http_methods(['POST'])
@require_player_session
def record_move(request, match_id):
	body = _json_body(request)
	if body is None:
		return JsonResponse({'error': 'Request body must be valid JSON.'}, status=400)
	try:
		with transaction.atomic():
			match = GameMatch.objects.select_for_update().select_related(
				'white_player', 'black_player'
			).get(id=match_id)
			player = request.player
			if player.id not in {match.white_player_id, match.black_player_id}:
				return JsonResponse({'error': 'Player is not part of this match.'}, status=403)
			if match.status != GameMatch.Status.ACTIVE:
				return JsonResponse({'error': 'This match is not active.'}, status=409)

			try:
				board = _board_from_match(match)
			except ValueError:
				return JsonResponse({'error': 'The stored match history is invalid.'}, status=409)

			if (
				not match.black_player_id
				and board.turn == chess.BLACK
				and match.mode != GameMatch.Mode.AI
			):
				return JsonResponse({'error': 'No player is assigned to this turn.'}, status=409)
			if match.mode == GameMatch.Mode.AI and board.turn == chess.BLACK:
				return JsonResponse({'error': 'The AI is choosing its move.'}, status=409)
			expected_player_id = match.white_player_id if board.turn == chess.WHITE else match.black_player_id
			if expected_player_id != player.id:
				return JsonResponse({'error': 'It is not your turn.'}, status=403)

			from_square = body.get('from')
			to_square = body.get('to')
			promotion = body.get('promotion', '')
			if (
				not isinstance(from_square, str)
				or from_square not in chess.SQUARE_NAMES
				or not isinstance(to_square, str)
				or to_square not in chess.SQUARE_NAMES
				or not isinstance(promotion, str)
				or promotion not in {'', 'q', 'r', 'b', 'n'}
			):
				return JsonResponse({'error': 'A valid from, to, and optional promotion are required.'}, status=400)

			try:
				move = chess.Move.from_uci(from_square + to_square + promotion)
			except ValueError:
				return JsonResponse({'error': 'The requested move is invalid.'}, status=400)
			if move not in board.legal_moves:
				return JsonResponse({'error': 'The requested move is not legal.'}, status=409)

			move_number = match.moves.count() + 1
			if 'move_number' in body and (
				type(body['move_number']) is not int or body['move_number'] != move_number
			):
				return JsonResponse({'error': 'The match has changed; refresh before moving.'}, status=409)
			notation = board.san(move)
			board.push(move)
			game_move = GameMove.objects.create(
				match=match,
				move_number=move_number,
				notation=notation,
				from_square=from_square,
				to_square=to_square,
				fen_after=board.fen(),
			)
			if match.mode == GameMatch.Mode.AI and not board.is_game_over():
				ai_move = choose_ai_move(board, match.ai_difficulty)
				if ai_move is None:
					return JsonResponse({'error': 'The AI could not find a legal move.'}, status=409)
				ai_move_number = move_number + 1
				ai_notation = board.san(ai_move)
				ai_from_square = chess.square_name(ai_move.from_square)
				ai_to_square = chess.square_name(ai_move.to_square)
				board.push(ai_move)
				GameMove.objects.create(
					match=match,
					move_number=ai_move_number,
					notation=ai_notation,
					from_square=ai_from_square,
					to_square=ai_to_square,
					fen_after=board.fen(),
				)
			match.fen = board.fen()
			match.save(update_fields=['fen', 'updated_at'])

			result = _board_result(board)
			if result:
				_finish_match(match, result)

			match_data = _match_data(match)
			match_data['fen'] = board.fen()
	except IntegrityError:
		return JsonResponse({'error': 'The match changed while the move was being saved.'}, status=409)
	except (GameMatch.DoesNotExist, ValueError, TypeError):
		return JsonResponse({'error': 'Valid match is required.'}, status=400)
	_broadcast_match_update(match.id, {
		'type': 'match_update',
		'match': match_data,
		'move': {'move_number': game_move.move_number, 'notation': game_move.notation},
	})
	return JsonResponse({
		'move': {'move_number': game_move.move_number, 'notation': game_move.notation},
		'match': match_data,
	}, status=201)


@csrf_exempt
@require_http_methods(['POST'])
@require_player_session
def complete_match(request, match_id):
	body = _json_body(request)
	if body is None:
		return JsonResponse({'error': 'Request body must be valid JSON.'}, status=400)
	try:
		with transaction.atomic():
			match = GameMatch.objects.select_for_update().select_related(
				'white_player', 'black_player'
			).prefetch_related('moves').get(id=match_id)
			player = request.player
			if player.id not in {match.white_player_id, match.black_player_id}:
				return JsonResponse({'error': 'Player is not part of this match.'}, status=403)
			try:
				board = _board_from_match(match)
			except ValueError:
				return JsonResponse({'error': 'The stored match history is invalid.'}, status=409)
			result = _board_result(board)
			if not result:
				return JsonResponse({'error': 'The game has not reached a final position.'}, status=409)
			requested_result = body.get('result') if isinstance(body, dict) else None
			if requested_result and requested_result != result:
				return JsonResponse({'error': 'The submitted result does not match the board.'}, status=409)
			if match.status == GameMatch.Status.ACTIVE:
				_finish_match(match, result)
			elif match.status != GameMatch.Status.COMPLETED or match.result != result:
				return JsonResponse({'error': 'This match cannot be completed.'}, status=409)
	except (GameMatch.DoesNotExist, ValueError, TypeError):
		return JsonResponse({'error': 'Valid match is required.'}, status=400)
	return JsonResponse({'match': _match_data(match)})


@csrf_exempt
@require_http_methods(['POST'])
@require_player_session
def claim_match_draw(request, match_id):
	try:
		with transaction.atomic():
			match = GameMatch.objects.select_for_update().select_related(
				'white_player', 'black_player'
			).prefetch_related('moves').get(id=match_id)
			if request.player.id not in {match.white_player_id, match.black_player_id}:
				return JsonResponse({'error': 'Player is not part of this match.'}, status=403)
			if match.status != GameMatch.Status.ACTIVE:
				return JsonResponse({'error': 'This match is not active.'}, status=409)
			try:
				board = _board_from_match(match)
			except ValueError:
				return JsonResponse({'error': 'The stored match history is invalid.'}, status=409)
			if not board.can_claim_draw():
				return JsonResponse({
					'error': 'A draw cannot be claimed by threefold repetition or the 50-move rule yet.'
				}, status=409)
			termination = (
				'threefold_repetition'
				if board.can_claim_threefold_repetition()
				else 'fifty_moves'
			)
			_finish_match(match, 'draw')
			match_data = _match_data(match, board)
			match_data['termination'] = termination
	except (GameMatch.DoesNotExist, ValueError, TypeError):
		return JsonResponse({'error': 'Valid match is required.'}, status=400)
	_broadcast_match_update(match.id, {'type': 'match_update', 'match': match_data})
	return JsonResponse({'match': match_data})


@csrf_exempt
@require_http_methods(['POST'])
@require_player_session
def surrender_match(request, match_id):
	try:
		with transaction.atomic():
			match = GameMatch.objects.select_for_update().get(id=match_id)
			player = request.player
			if player.id not in {match.white_player_id, match.black_player_id}:
				return JsonResponse({'error': 'Player is not part of this match.'}, status=403)
			if match.status != GameMatch.Status.ACTIVE:
				return JsonResponse({'error': 'This match is not active.'}, status=409)
			match.status = GameMatch.Status.ABANDONED
			match.result = 'black_wins' if player.id == match.white_player_id else 'white_wins'
			match.save(update_fields=['status', 'result', 'updated_at'])
			match = GameMatch.objects.select_related(
				'white_player', 'black_player'
			).prefetch_related('moves').get(id=match.id)
	except (GameMatch.DoesNotExist, ValueError, TypeError):
		return JsonResponse({'error': 'Valid match is required.'}, status=400)
	_broadcast_match_update(match.id, {'type': 'match_update', 'match': _match_data(match)})
	return JsonResponse({'match': _match_data(match)})
