import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import GameMatch, GameMove, PlayerProfile


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


def _match_data(match):
	return {
		'id': str(match.id),
		'mode': match.mode,
		'status': match.status,
		'fen': match.fen,
		'result': match.result,
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
	return JsonResponse({'player': _player_data(player)}, status=201)

@require_http_methods(['GET'])
def player_detail(request, player_id):
	try:
		player = PlayerProfile.objects.get(id=player_id)
	except PlayerProfile.DoesNotExist:
		return JsonResponse({'error': 'Player not found.'}, status=404)
	return JsonResponse({'player': _player_data(player)})

@csrf_exempt
@require_http_methods(['POST'])
def create_match(request):
	body = _json_body(request)
	if body is None:
		return JsonResponse({'error': 'Request body must be valid JSON.'}, status=400)

	try:
		player = PlayerProfile.objects.get(id=body.get('player_id'))
	except (PlayerProfile.DoesNotExist, ValueError, TypeError):
		return JsonResponse({'error': 'Valid player_id is required.'}, status=400)

	mode = body.get('mode', GameMatch.Mode.QUICK_MATCH)
	if mode not in GameMatch.Mode.values:
		return JsonResponse({'error': 'Unsupported match mode.'}, status=400)

	match = GameMatch.objects.create(white_player=player, mode=mode)
	return JsonResponse({'match': _match_data(match)}, status=201)

@require_http_methods(['GET'])
def match_detail(request, match_id):
	try:
		match = GameMatch.objects.select_related('white_player', 'black_player').prefetch_related('moves').get(id=match_id)
	except (GameMatch.DoesNotExist, ValueError):
		return JsonResponse({'error': 'Match not found.'}, status=404)
	return JsonResponse({'match': _match_data(match)})

@csrf_exempt
@require_http_methods(['POST'])
def record_move(request, match_id):
	body = _json_body(request)
	if body is None:
		return JsonResponse({'error': 'Request body must be valid JSON.'}, status=400)
	try:
		match = GameMatch.objects.get(id=match_id)
		player = PlayerProfile.objects.get(id=body.get('player_id'))
	except (GameMatch.DoesNotExist, PlayerProfile.DoesNotExist, ValueError, TypeError):
		return JsonResponse({'error': 'Valid match and player are required.'}, status=400)

	if player.id not in {match.white_player_id, match.black_player_id}:
		return JsonResponse({'error': 'Player is not part of this match.'}, status=403)
	required = ['move_number', 'notation', 'from', 'to', 'fen']
	if any(not body.get(field) for field in required):
		return JsonResponse({'error': 'move_number, notation, from, to, and fen are required.'}, status=400)
	move, created = GameMove.objects.get_or_create(
		match=match,
		move_number=body['move_number'],
		defaults={
			'notation': body['notation'],
			'from_square': body['from'],
			'to_square': body['to'],
			'fen_after': body['fen'],
		},
	)
	if not created:
		return JsonResponse({'error': 'That move number already exists.'}, status=409)
	match.fen = body['fen']
	match.save(update_fields=['fen', 'updated_at'])
	return JsonResponse({'move': {'move_number': move.move_number, 'notation': move.notation}, 'match': _match_data(match)}, status=201)

@csrf_exempt
@require_http_methods(['POST'])
def surrender_match(request, match_id):
	body = _json_body(request)
	try:
		match = GameMatch.objects.get(id=match_id)
		player = PlayerProfile.objects.get(id=body.get('player_id')) if body else None
	except (GameMatch.DoesNotExist, PlayerProfile.DoesNotExist, ValueError, TypeError):
		return JsonResponse({'error': 'Valid match and player are required.'}, status=400)
	if player.id not in {match.white_player_id, match.black_player_id}:
		return JsonResponse({'error': 'Player is not part of this match.'}, status=403)
	match.status = GameMatch.Status.ABANDONED
	match.result = 'black_wins' if player.id == match.white_player_id else 'white_wins'
	match.save(update_fields=['status', 'result', 'updated_at'])
	return JsonResponse({'match': _match_data(match)})
