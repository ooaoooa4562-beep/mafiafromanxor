import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('rooms', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='GameMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phase', models.CharField(choices=[('night', 'Ночь'), ('day', 'День'), ('finished', 'Завершена')], default='night', max_length=12)),
                ('round_number', models.PositiveIntegerField(default=1)),
                ('winner', models.CharField(blank=True, max_length=12)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('phase_started_at', models.DateTimeField(auto_now_add=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('room', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='match', to='rooms.room')),
            ],
        ),
        migrations.CreateModel(
            name='GameParticipant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('mafia', 'Мафия'), ('doctor', 'Доктор'), ('detective', 'Комиссар'), ('citizen', 'Мирный житель')], max_length=12)),
                ('is_alive', models.BooleanField(default=True)),
                ('match', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participants', to='game.gamematch')),
                ('room_player', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='game_participant', to='rooms.roomplayer')),
            ],
            options={'ordering': ['id']},
        ),
        migrations.AddConstraint(
            model_name='gameparticipant',
            constraint=models.UniqueConstraint(fields=('match', 'room_player'), name='unique_match_player'),
        ),
        migrations.CreateModel(
            name='GameAction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('round_number', models.PositiveIntegerField()),
                ('action_type', models.CharField(choices=[('mafia', 'Выбор мафии'), ('doctor', 'Лечение'), ('detective', 'Проверка'), ('vote', 'Голосование')], max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='game_actions', to='rooms.roomplayer')),
                ('match', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='actions', to='game.gamematch')),
                ('target', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='targeted_game_actions', to='rooms.roomplayer')),
            ],
            options={'ordering': ['created_at']},
        ),
        migrations.AddConstraint(
            model_name='gameaction',
            constraint=models.UniqueConstraint(fields=('match', 'round_number', 'action_type', 'actor'), name='unique_round_action'),
        ),
    ]
