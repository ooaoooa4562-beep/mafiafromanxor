from django.conf import settings
from django.db import models


class Friendship(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Ожидает подтверждения'),
        ('accepted', 'Друзья'),
        ('rejected', 'Отклонена'),
        ('blocked', 'Заблокирована'),
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_friend_requests',
        verbose_name='Отправитель'
    )

    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_friend_requests',
        verbose_name='Получатель'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Дружба'
        verbose_name_plural = 'Друзья'
        constraints = [
            models.UniqueConstraint(
                fields=['sender', 'receiver'],
                name='unique_friendship'
            ),
        ]

    def __str__(self):
        return f'{self.sender} → {self.receiver} ({self.status})'


