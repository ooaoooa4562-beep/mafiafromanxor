# Mafia from Anxor

Браузерная онлайн-мафия: адаптивный интерфейс, Django backend, комнаты, роли, игровые фазы, друзья и WebRTC signaling.

## Реализовано в текущей ветке

- `frontend/index.html` — главная страница проекта.
- `frontend/play.html` — браузерный клиент: регистрация/вход, создание публичных комнат, вход по UUID, игроки за столом, запуск партии, личная роль, игровые действия, друзья и статистика.
- `GET /api/auth/me/`, `POST /api/auth/register/`, `POST /api/auth/login/`, `POST /api/auth/logout/` — сессионная авторизация с CSRF.
- `GET/POST /api/rooms/`, `POST /api/rooms/<uuid>/join/` — список, создание и вступление в комнаты.
- `POST /api/game/rooms/<uuid>/start/` — запуск матча создателем комнаты (минимум 4 игрока).
- `GET /api/game/rooms/<uuid>/state/` — состояние матча; роли других игроков скрыты до окончания игры.
- `POST /api/game/rooms/<uuid>/action/` — ночные действия мафии/доктора/комиссара и дневное голосование.
- `GET /api/game/stats/` — статистика завершённых матчей.
- `GET /api/friends/`, `POST /api/friends/requests/`, `POST /api/friends/requests/<id>/respond/`, `POST /api/friends/<user_id>/block/` — друзья, заявки и блокировки.
- `ws/rooms/<uuid>/` — аутентифицированные события комнаты и signaling WebRTC.
- Голосовые каналы проверяются сервером: lobby до игры, мафия ночью, живые игроки днём, отдельный канал выбывших; при смене фазы доступ перепроверяется.

## Запуск локально

1. Установи Python и создай виртуальное окружение.
2. Установи зависимости из корня репозитория:

```bash
pip install -r requirements.txt
```

3. Задай переменные окружения из `backend/.env.example`. Для локальной разработки допустимы значения по умолчанию; для production обязательно задай новый случайный `DJANGO_SECRET_KEY`.
4. Запусти сервер из каталога `backend`:

```bash
python manage.py migrate
python manage.py runserver
```

5. Открой http://localhost:8000/ и нажми «Играть онлайн». Для микрофона нужен localhost или HTTPS. Вход и регистрация используют Django session cookies и CSRF.

## Голосовой чат: ограничения

Браузеры устанавливают P2P WebRTC-соединения; Django Channels только аутентифицирует пользователей, проверяет доступ к голосовой комнате и пересылает SDP/ICE signaling. Для соединений между сетями с жёстким NAT/корпоративными firewall понадобится TURN. Для больших комнат вместо mesh P2P потребуется SFU (например, LiveKit/mediasoup). Текущий клиент использует публичный STUN для базового тестирования.

## Перед production

- Установить Redis и задать `REDIS_URL`; in-memory channel layer предназначен только для локального процесса.
- Установить новый `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS` и HTTPS.
- Настроить TURN или SFU для стабильного голоса и масштабирования.
- Перейти с SQLite на PostgreSQL.
- Запустить `python manage.py check`, `python manage.py makemigrations --check --dry-run` и `python manage.py test`.
- Настроить резервное копирование, мониторинг, модерацию и rate limiting.

## Важное замечание

Это активная разработка. API и клиент реализованы в ветке разработки, но полный Django test suite и реальную проверку WebRTC между разными сетями ещё необходимо выполнить. Не считай текущую версию production-ready.
