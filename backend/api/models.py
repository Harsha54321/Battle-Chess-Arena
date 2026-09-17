import uuid

from django.db import models


class PlayerProfile(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	username = models.CharField(max_length=40, unique=True)
	avatar = models.CharField(max_length=10, default='king')
	rating = models.PositiveIntegerField(default=1200)
	level = models.PositiveIntegerField(default=1)
	coins = models.PositiveIntegerField(default=500)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return self.username


class GameMatch(models.Model):
	class Status(models.TextChoices):
		WAITING = 'waiting', 'Waiting'
		ACTIVE = 'active', 'Active'
		COMPLETED = 'completed', 'Completed'
		ABANDONED = 'abandoned', 'Abandoned'

	class Mode(models.TextChoices):
		QUICK_MATCH = 'quick_match', 'Quick match'
		AI = 'ai', 'Play vs AI'
		MULTIPLAYER = 'multiplayer', 'Multiplayer'

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.QUICK_MATCH)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
	white_player = models.ForeignKey(PlayerProfile, on_delete=models.PROTECT, related_name='white_matches')
	black_player = models.ForeignKey(
		PlayerProfile,
		on_delete=models.PROTECT,
		related_name='black_matches',
		null=True,
		blank=True,
	)
	fen = models.CharField(max_length=100, default='startpos')
	result = models.CharField(max_length=20, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)


class GameMove(models.Model):
	match = models.ForeignKey(GameMatch, on_delete=models.CASCADE, related_name='moves')
	move_number = models.PositiveIntegerField()
	notation = models.CharField(max_length=20)
	from_square = models.CharField(max_length=2)
	to_square = models.CharField(max_length=2)
	fen_after = models.CharField(max_length=100)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['move_number', 'created_at']
		constraints = [
			models.UniqueConstraint(fields=['match', 'move_number'], name='unique_match_move_number'),
		]
