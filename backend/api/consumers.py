from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import GameMatch
from .views import _board_from_match, _match_data


@database_sync_to_async
def _match_snapshot(match_id, player_id):
	try:
		match = GameMatch.objects.select_related(
			'white_player', 'black_player'
		).prefetch_related('moves').get(id=match_id)
	except (GameMatch.DoesNotExist, ValueError, TypeError):
		return None, None
	if player_id not in {str(match.white_player_id), str(match.black_player_id)}:
		return None, 'forbidden'
	try:
		board = _board_from_match(match)
	except ValueError:
		return None, 'invalid'
	data = _match_data(match)
	data['fen'] = board.fen()
	return data, None


class MatchConsumer(AsyncJsonWebsocketConsumer):
	async def connect(self):
		player_id = self.scope.get('player_id')
		if not player_id:
			await self.close(code=4401)
			return

		self.match_id = str(self.scope['url_route']['kwargs']['match_id'])
		match, error = await _match_snapshot(self.match_id, player_id)
		if error:
			await self.close(code=4403 if error == 'forbidden' else 4404)
			return

		self.group_name = f'match_{self.match_id.replace("-", "")}'
		await self.channel_layer.group_add(self.group_name, self.channel_name)
		await self.accept(subprotocol='battle-chess.v1')
		await self.send_json({'type': 'match_snapshot', 'match': match})

	async def disconnect(self, close_code):
		group_name = getattr(self, 'group_name', None)
		if group_name:
			await self.channel_layer.group_discard(group_name, self.channel_name)

	async def match_update(self, event):
		await self.send_json(event['payload'])
