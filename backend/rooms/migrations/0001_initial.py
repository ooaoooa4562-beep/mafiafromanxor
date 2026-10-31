import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='Room',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Название комнаты')),
                ('code', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='Код комнаты')),
                ('max_players', models.PositiveSmallIntegerField(default=10, verbose_name='Максимум игроков')),
                ('is_private', models.BooleanField(default=True, verbose_name='Приватная комната')),
                ('status', models.CharField(choices=[('waiting', 'Ожидание игроков'), ('playing', 'Игра идёт'), ('finished', 'Игра завершена')], default='waiting', max_length=20, verbose_name='Статус')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_rooms', to=settings.AUTH_USER_MODEL, verbose_name='Создатель')),
            ],
            options={'verbose_name': 'Комната', 'verbose_name_plural': 'Комнаты', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='RoomPlayer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_ready', models.BooleanField(default=False)),
                ('is_alive', models.BooleanField(default=True)),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='players', to='rooms.room')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='room_memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['joined_at']},
        ),
        migrations.AddConstraint(
            model_name='roomplayer',
            constraint=models.UniqueConstraint(fields=('room', 'user'), name='unique_room_player'),
        ),
    ]
