import hashlib

from channels.db import database_sync_to_async
from django.utils import timezone

from .models import PlayerSession


def _session_token(scope):
	protocols = scope.get('subprotocols', [])
	auth_protocols = [protocol[5:] for protocol in protocols if protocol.startswith('auth.')]
	if len(auth_protocols) != 1 or not auth_protocols[0]:
		return None
	return auth_protocols[0]


@database_sync_to_async
def _get_player_id(token):
	token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
	session = PlayerSession.objects.filter(
		token_hash=token_hash,
		expires_at__gt=timezone.now(),
		player__is_suspended=False,
	).values_list('player_id', flat=True).first()
	return str(session) if session else None


class PlayerSessionAuthMiddleware:
	def __init__(self, app):
		self.app = app

	async def __call__(self, scope, receive, send):
		token = _session_token(scope)
		scope['player_id'] = await _get_player_id(token) if token else None
		return await self.app(scope, receive, send)
