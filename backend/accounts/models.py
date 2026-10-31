from django.db import models

# Create your models here.


from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # Telegram
    telegram_id = models.BigIntegerField(
        unique=True,
        null=True,
        blank=True,
        verbose_name='Telegram ID'
    )

    telegram_username = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Telegram username'
    )

    telegram_is_verified = models.BooleanField(
        default=False,
        verbose_name='Telegram подтверждён'
    )

    # Игровой профиль
    nickname = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='Игровой никнейм'
    )

    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Аватар'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата регистрации'
    )

    def __str__(self):
        return self.nickname or self.username
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'