from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Friendship",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "Ожидает подтверждения"), ("accepted", "Друзья"), ("rejected", "Отклонена"), ("blocked", "Заблокирована")], default="pending", max_length=20, verbose_name="Статус")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Дата обновления")),
                ("receiver", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="received_friend_requests", to=settings.AUTH_USER_MODEL, verbose_name="Получатель")),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sent_friend_requests", to=settings.AUTH_USER_MODEL, verbose_name="Отправитель")),
            ],
            options={"verbose_name": "Дружба", "verbose_name_plural": "Друзья"},
        ),
        migrations.AddConstraint(model_name="friendship", constraint=models.UniqueConstraint(fields=("sender", "receiver"), name="unique_friendship")),
    ]
