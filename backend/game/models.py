from django.db import models


class Game(models.Model):
    PHASE_CHOICES = (("night", "Ночь"), ("day", "День"), ("voting", "Голосование"), ("finished", "Завершена"))
    WINNER_CHOICES = (("mafia", "Мафия"), ("town", "Город"))
    room = models.OneToOneField("rooms.Room", on_delete=models.CASCADE, related_name="game")
    phase = models.CharField(max_length=12, choices=PHASE_CHOICES, default="night")
    round_number = models.PositiveSmallIntegerField(default=1)
    phase_ends_at = models.DateTimeField(null=True, blank=True)
    winner = models.CharField(max_length=8, choices=WINNER_CHOICES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class PlayerRole(models.Model):
    ROLE_CHOICES = (("mafia", "Мафия"), ("doctor", "Доктор"), ("detective", "Комиссар"), ("civilian", "Мирный житель"))
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="players")
    player = models.ForeignKey("rooms.RoomPlayer", on_delete=models.CASCADE, related_name="game_roles")
    role = models.CharField(max_length=12, choices=ROLE_CHOICES)
    is_alive = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("game", "player"), name="unique_game_player_role")]


class GameAction(models.Model):
    ACTION_CHOICES = (("kill", "Убийство"), ("heal", "Лечение"), ("investigate", "Проверка"), ("vote", "Голос"))
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="actions")
    actor = models.ForeignKey(PlayerRole, on_delete=models.CASCADE, related_name="actions")
    target = models.ForeignKey(PlayerRole, on_delete=models.CASCADE, related_name="targeted_actions")
    action_type = models.CharField(max_length=12, choices=ACTION_CHOICES)
    phase = models.CharField(max_length=12)
    round_number = models.PositiveSmallIntegerField()
    result = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("actor", "phase", "round_number"), name="one_game_action_per_phase")]
