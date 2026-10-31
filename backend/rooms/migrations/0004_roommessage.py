import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('rooms', '0003_unique_user_room_membership'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RoomMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.CharField(max_length=1000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='rooms.room')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='room_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['created_at', 'id']},
        ),
        migrations.AddIndex(
            model_name='roommessage',
            index=models.Index(fields=['room', 'created_at'], name='room_msg_room_created_idx'),
        ),
    ]
