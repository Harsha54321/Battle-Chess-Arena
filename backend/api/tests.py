import json

from django.test import TestCase

from .models import GameMatch, PlayerProfile

class GameApiTests(TestCase):
	def create_player(self, username='TestPlayer'):
		response = self.client.post(
			'/api/players/guest/',
			data=json.dumps({'username': username, 'avatar': 'knight'}),
			content_type='application/json',
		)
		self.assertEqual(response.status_code, 201)
		return response.json()['player']

	def test_guest_player_and_detail(self):
		player = self.create_player()
		response = self.client.get(f"/api/players/{player['id']}/")
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['player']['username'], 'TestPlayer')

	def test_match_move_and_surrender(self):
		player = self.create_player()
		response = self.client.post(
			'/api/matches/',
			data=json.dumps({'player_id': player['id'], 'mode': 'quick_match'}),
			content_type='application/json',
		)
		self.assertEqual(response.status_code, 201)
		match = response.json()['match']
		move_response = self.client.post(
			f"/api/matches/{match['id']}/moves/",
			data=json.dumps({
				'player_id': player['id'],
				'move_number': 1,
				'notation': 'e4',
				'from': 'e2',
				'to': 'e4',
				'fen': 'test-fen',
			}),
			content_type='application/json',
		)
		self.assertEqual(move_response.status_code, 201)
		surrender_response = self.client.post(
			f"/api/matches/{match['id']}/surrender/",
			data=json.dumps({'player_id': player['id']}),
			content_type='application/json',
		)
		self.assertEqual(surrender_response.status_code, 200)
		self.assertEqual(surrender_response.json()['match']['status'], GameMatch.Status.ABANDONED)

	def test_duplicate_username_is_rejected(self):
		self.create_player()
		response = self.client.post(
			'/api/players/guest/',
			data=json.dumps({'username': 'TestPlayer'}),
			content_type='application/json',
		)
		self.assertEqual(response.status_code, 409)
from django.test import TestCase

# Create your tests here.
