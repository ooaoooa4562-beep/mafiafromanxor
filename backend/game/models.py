from django.conf import settings
from django.db import models


class GameMatch(models.Model):
    PHASES = (
        ('night', 'Ночь'),
        ('day', 'День'),
        ('finished', 'Завершена'),
    )
    room = models.OneToOneField('rooms.Room', on_delete=models.CASCADE, related_name='match')
    phase = models.CharField(max_length=12, choices=PHASES, default='night')
    round_number = models.PositiveIntegerField(default=1)
    winner = models.CharField(max_length=12, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    phase_started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.room.name} · {self.phase} #{self.round_number}'


class GameParticipant(models.Model):
    ROLES = (
        ('mafia', 'Мафия'),
        ('doctor', 'Доктор'),
        ('detective', 'Комиссар'),
        ('citizen', 'Мирный житель'),
    )
    match = models.ForeignKey(GameMatch, on_delete=models.CASCADE, related_name='participants')
    room_player = models.OneToOneField('rooms.RoomPlayer', on_delete=models.CASCADE, related_name='game_participant')
    role = models.CharField(max_length=12, choices=ROLES)
    is_alive = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(fields=['match', 'room_player'], name='unique_match_player'),
        ]

    @property
    def user(self):
        return self.room_player.user


class GameAction(models.Model):
    TYPES = (
        ('mafia', 'Выбор мафии'),
        ('doctor', 'Лечение'),
        ('detective', 'Проверка'),
        ('vote', 'Голосование'),
    )
    match = models.ForeignKey(GameMatch, on_delete=models.CASCADE, related_name='actions')
    round_number = models.PositiveIntegerField()
    action_type = models.CharField(max_length=12, choices=TYPES)
    actor = models.ForeignKey('rooms.RoomPlayer', on_delete=models.CASCADE, related_name='game_actions')
    target = models.ForeignKey('rooms.RoomPlayer', on_delete=models.SET_NULL, null=True, blank=True, related_name='targeted_game_actions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['match', 'round_number', 'action_type', 'actor'], name='unique_round_action'),
        ]
        ordering = ['created_at']
