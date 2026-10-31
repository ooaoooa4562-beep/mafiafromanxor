import uuid

from django.conf import settings
from django.db import models


class Room(models.Model):

    STATUS_CHOICES = (
        ('waiting', 'Ожидание игроков'),
        ('playing', 'Игра идёт'),
        ('finished', 'Игра завершена'),
    )

    name = models.CharField(
        max_length=100,
        verbose_name='Название комнаты'
    )

    code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name='Код комнаты'
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_rooms',
        verbose_name='Создатель'
    )

    max_players = models.PositiveSmallIntegerField(
        default=10,
        verbose_name='Максимум игроков'
    )

    is_private = models.BooleanField(
        default=True,
        verbose_name='Приватная комната'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='waiting',
        verbose_name='Статус'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    def __str__(self):
        return f'{self.name} ({self.code})'

    class Meta:
        verbose_name = 'Комната'
        verbose_name_plural = 'Комнаты'
        ordering = ['-created_at']