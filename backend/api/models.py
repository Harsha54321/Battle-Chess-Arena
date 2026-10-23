import uuid

from django.db import models


class PlayerProfile(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	username = models.CharField(max_length=40, unique=True)
	google_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)
	avatar = models.CharField(max_length=10, default='king')
	rating = models.PositiveIntegerField(default=1200)
	level = models.PositiveIntegerField(default=1)
	coins = models.PositiveIntegerField(default=500)
	is_suspended = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return self.username


class PlayerSession(models.Model):
	player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='sessions')
	token_hash = models.CharField(max_length=64, unique=True)
	expires_at = models.DateTimeField()
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f'{self.player.username} session'


class AuthLoginTicket(models.Model):
	player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='login_tickets')
	token_hash = models.CharField(max_length=64, unique=True)
	expires_at = models.DateTimeField()
	created_at = models.DateTimeField(auto_now_add=True)


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

	class AIDifficulty(models.TextChoices):
		BEGINNER = 'beginner', 'Beginner'
		INTERMEDIATE = 'intermediate', 'Intermediate'
		ADVANCED = 'advanced', 'Advanced'

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.QUICK_MATCH)
	ai_difficulty = models.CharField(
		max_length=20,
		choices=AIDifficulty.choices,
		default=AIDifficulty.BEGINNER,
	)
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

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=['white_player'],
				condition=models.Q(
					mode='quick_match',
					status='waiting',
					black_player__isnull=True,
				),
				name='unique_waiting_quick_match_player',
			),
		]


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


class TrainingLessonProgress(models.Model):
	player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='training_lesson_progress')
	lesson_id = models.CharField(max_length=60)
	attempts = models.PositiveIntegerField(default=0)
	completed_at = models.DateTimeField(null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['player', 'lesson_id'], name='unique_player_training_lesson'),
		]
		ordering = ['lesson_id']


class MatchMessage(models.Model):
	match = models.ForeignKey(GameMatch, on_delete=models.CASCADE, related_name='messages')
	player = models.ForeignKey(PlayerProfile, on_delete=models.PROTECT, related_name='match_messages')
	message = models.CharField(max_length=500)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at', 'id']


class DailyChallengeProgress(models.Model):
	player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='daily_challenges')
	date = models.DateField()
	progress = models.PositiveIntegerField(default=0)
	target = models.PositiveIntegerField(default=3)
	reward_coins = models.PositiveIntegerField(default=500)
	claimed = models.BooleanField(default=False)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['player', 'date'], name='unique_player_daily_challenge'),
		]


class DailyChallengeSettings(models.Model):
	id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
	target = models.PositiveIntegerField(default=3)
	reward_coins = models.PositiveIntegerField(default=500)
	updated_at = models.DateTimeField(auto_now=True)

	@classmethod
	def get_current(cls):
		settings, _ = cls.objects.get_or_create(pk=1)
		return settings


class FriendConnection(models.Model):
	class Status(models.TextChoices):
		PENDING = 'pending', 'Pending'
		ACCEPTED = 'accepted', 'Accepted'

	sender = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='sent_friend_requests')
	receiver = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='received_friend_requests')
	status = models.CharField(
		max_length=10,
		choices=[('pending', 'Pending'), ('accepted', 'Accepted')],
		default='pending',
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['sender', 'receiver'], name='unique_friend_request'),
		]


class Notification(models.Model):
	player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='notifications')
	actor = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='created_notifications', null=True, blank=True)
	connection = models.ForeignKey(FriendConnection, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
	match = models.ForeignKey('GameMatch', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
	notification_type = models.CharField(max_length=30, default='system')
	message = models.CharField(max_length=200)
	read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)


class FriendMessage(models.Model):
	sender = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='sent_friend_messages')
	receiver = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='received_friend_messages')
	message = models.CharField(max_length=500)
	created_at = models.DateTimeField(auto_now_add=True)
