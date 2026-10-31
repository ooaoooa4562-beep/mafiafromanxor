from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [("rooms", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="Game",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phase", models.CharField(choices=[("night", "Ночь"), ("day", "День"), ("voting", "Голосование"), ("finished", "Завершена")], default="night", max_length=12)),
                ("round_number", models.PositiveSmallIntegerField(default=1)),
                ("phase_ends_at", models.DateTimeField(blank=True, null=True)),
                ("winner", models.CharField(blank=True, choices=[("mafia", "Мафия"), ("town", "Город")], max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("room", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="game", to="rooms.room")),
            ],
        ),
        migrations.CreateModel(
            name="PlayerRole",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("mafia", "Мафия"), ("doctor", "Доктор"), ("detective", "Комиссар"), ("civilian", "Мирный житель")], max_length=12)),
                ("is_alive", models.BooleanField(default=True)),
                ("game", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="players", to="game.game")),
                ("player", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="game_roles", to="rooms.roomplayer")),
            ],
        ),
        migrations.AddConstraint(model_name="playerrole", constraint=models.UniqueConstraint(fields=("game", "player"), name="unique_game_player_role")),
        migrations.CreateModel(
            name="GameAction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action_type", models.CharField(choices=[("kill", "Убийство"), ("heal", "Лечение"), ("investigate", "Проверка"), ("vote", "Голос")], max_length=12)),
                ("phase", models.CharField(max_length=12)),
                ("round_number", models.PositiveSmallIntegerField()),
                ("result", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="actions", to="game.playerrole")),
                ("game", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="actions", to="game.game")),
                ("target", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="targeted_actions", to="game.playerrole")),
            ],
        ),
        migrations.AddConstraint(model_name="gameaction", constraint=models.UniqueConstraint(fields=("actor", "phase", "round_number"), name="one_game_action_per_phase")),
    ]
