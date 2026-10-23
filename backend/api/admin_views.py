from functools import wraps

from django.contrib.auth import authenticate, get_user_model
from django.core import signing
from django.db import transaction
from django.db.models import Q, Value
from django.db.models.functions import Least
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import DailyChallengeProgress, DailyChallengeSettings, GameMatch, PlayerProfile, PlayerSession
from .views import _json_body

ADMIN_TOKEN_SALT = 'battle-chess-admin'
ADMIN_TOKEN_MAX_AGE = 60 * 60
ADMIN_PAGE_SIZE = 25
DAILY_CHALLENGE_TARGET_MIN = 1
DAILY_CHALLENGE_TARGET_MAX = 20
DAILY_CHALLENGE_REWARD_MAX = 100_000


@csrf_exempt
@require_http_methods(['POST'])
def admin_login(request):
	body = _json_body(request)
	if not isinstance(body, dict):
		return JsonResponse({'error': 'Request body must be valid JSON.'}, status=400)

	username = body.get('username')
	password = body.get('password')
	if not isinstance(username, str) or not username or not isinstance(password, str) or not password:
		return JsonResponse({'error': 'Username and password are required.'}, status=400)

	user = authenticate(request, username=username, password=password)
	if user is None:
		return JsonResponse({'error': 'Invalid username or password.'}, status=401)
	if not user.is_active or not user.is_staff:
		return JsonResponse({'error': 'This account is not authorized for admin access.'}, status=403)

	token = signing.dumps({'user_id': user.pk}, salt=ADMIN_TOKEN_SALT)
	return JsonResponse({
		'token': token,
		'expires_in': ADMIN_TOKEN_MAX_AGE,
		'admin': {'username': user.get_username()},
	})


def require_admin(view):
	@wraps(view)
	def wrapped(request, *args, **kwargs):
		authorization = request.headers.get('Authorization', '')
		scheme, separator, token = authorization.partition(' ')
		if scheme.lower() != 'bearer' or not separator or not token:
			return JsonResponse({'error': 'Admin authentication required.'}, status=401)
		try:
			payload = signing.loads(token, salt=ADMIN_TOKEN_SALT, max_age=ADMIN_TOKEN_MAX_AGE)
			user = get_user_model().objects.get(pk=payload.get('user_id'), is_active=True, is_staff=True)
		except (signing.BadSignature, signing.SignatureExpired, get_user_model().DoesNotExist, AttributeError):
			return JsonResponse({'error': 'Admin session is invalid or expired. Sign in again.'}, status=401)
		request.admin_user = user
		return view(request, *args, **kwargs)

	return wrapped


@require_http_methods(['GET'])
@require_admin
def admin_overview(request):
	today = timezone.localdate()
	return JsonResponse({
		'admin': {'username': request.admin_user.get_username()},
		'overview': {
			'players_total': PlayerProfile.objects.count(),
			'players_suspended': PlayerProfile.objects.filter(is_suspended=True).count(),
			'matches_total': GameMatch.objects.count(),
			'matches_active': GameMatch.objects.filter(status=GameMatch.Status.ACTIVE).count(),
			'matches_today': GameMatch.objects.filter(created_at__date=today).count(),
		},
	})


@require_http_methods(['GET'])
@require_admin
def admin_players(request):
	query = request.GET.get('q', '').strip()[:100]
	try:
		page = max(1, int(request.GET.get('page', '1')))
	except ValueError:
		return JsonResponse({'error': 'page must be a positive integer.'}, status=400)
	if page > 1_000_000:
		return JsonResponse({'error': 'page is out of range.'}, status=400)

	players = PlayerProfile.objects.all()
	if query:
		players = players.filter(Q(username__icontains=query) | Q(id__icontains=query))
	total = players.count()
	start = (page - 1) * ADMIN_PAGE_SIZE
	results = players.order_by('-created_at', 'id')[start:start + ADMIN_PAGE_SIZE]
	return JsonResponse({
		'players': [{
			'id': str(player.id),
			'username': player.username,
			'rating': player.rating,
			'level': player.level,
			'coins': player.coins,
			'is_suspended': player.is_suspended,
			'created_at': player.created_at.isoformat(),
		} for player in results],
		'pagination': {
			'page': page,
			'page_size': ADMIN_PAGE_SIZE,
			'total': total,
			'pages': (total + ADMIN_PAGE_SIZE - 1) // ADMIN_PAGE_SIZE,
		},
	})


@csrf_exempt
@require_http_methods(['POST'])
@require_admin
def admin_set_player_suspension(request, player_id):
	body = _json_body(request)
	if not isinstance(body, dict) or not isinstance(body.get('suspended'), bool):
		return JsonResponse({'error': 'suspended must be true or false.'}, status=400)
	try:
		player = PlayerProfile.objects.get(id=player_id)
	except (PlayerProfile.DoesNotExist, ValueError, TypeError):
		return JsonResponse({'error': 'Player not found.'}, status=404)

	player.is_suspended = body['suspended']
	player.save(update_fields=['is_suspended', 'updated_at'])
	if player.is_suspended:
		PlayerSession.objects.filter(player=player).delete()
	return JsonResponse({
		'player': {
			'id': str(player.id),
			'username': player.username,
			'is_suspended': player.is_suspended,
		},
	})


@require_http_methods(['GET'])
@require_admin
def admin_matches(request):
	matches = GameMatch.objects.select_related('white_player', 'black_player').order_by('-created_at')[:50]
	return JsonResponse({
		'matches': [{
			'id': str(match.id),
			'mode': match.get_mode_display(),
			'status': match.get_status_display(),
			'white_player': match.white_player.username,
			'black_player': match.black_player.username if match.black_player else 'Waiting for opponent',
			'result': match.result,
			'created_at': match.created_at.isoformat(),
		} for match in matches],
	})


@csrf_exempt
@require_http_methods(['GET', 'POST'])
@require_admin
def admin_daily_challenge(request):
	if request.method == 'GET':
		challenge = DailyChallengeSettings.get_current()
		return JsonResponse({
			'target': challenge.target,
			'reward_coins': challenge.reward_coins,
		})

	body = _json_body(request)
	if not isinstance(body, dict):
		return JsonResponse({'error': 'Request body must be valid JSON.'}, status=400)

	target = body.get('target')
	reward_coins = body.get('reward_coins')
	if type(target) is not int or not DAILY_CHALLENGE_TARGET_MIN <= target <= DAILY_CHALLENGE_TARGET_MAX:
		return JsonResponse({
			'error': f'target must be an integer from {DAILY_CHALLENGE_TARGET_MIN} to {DAILY_CHALLENGE_TARGET_MAX}.',
		}, status=400)
	if type(reward_coins) is not int or not 0 <= reward_coins <= DAILY_CHALLENGE_REWARD_MAX:
		return JsonResponse({
			'error': f'reward_coins must be an integer from 0 to {DAILY_CHALLENGE_REWARD_MAX}.',
		}, status=400)

	with transaction.atomic():
		challenge, _ = DailyChallengeSettings.objects.select_for_update().get_or_create(pk=1)
		challenge.target = target
		challenge.reward_coins = reward_coins
		challenge.save(update_fields=['target', 'reward_coins', 'updated_at'])
		DailyChallengeProgress.objects.filter(date=timezone.localdate()).update(
			target=target,
			reward_coins=reward_coins,
			progress=Least('progress', Value(target)),
		)

	return JsonResponse({
		'target': challenge.target,
		'reward_coins': challenge.reward_coins,
	})
