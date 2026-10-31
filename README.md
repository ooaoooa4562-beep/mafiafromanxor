# Mafia from Anxor

Веб-игра «Мафия»: Django backend + браузерный интерфейс.

## Реализованная основа

- `frontend/index.html` — адаптивный UI-прототип: список комнат, создание комнаты, вход по коду, игровая комната, чат-интерфейс и локальная проверка микрофона.
- `backend/accounts/` — регистрация, вход/выход по Django session, CSRF token и профиль текущего пользователя.
- `backend/rooms/` — API комнат, участники, готовность и миграции.
- `backend/voice/` — аутентифицированный WebSocket relay для WebRTC SDP/ICE сигналинга с проверкой членства в комнате.
- Django settings читают секреты из окружения; Redis channel layer включается через REDIS_URL.

## Запуск backend локально

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env  # Windows; на macOS/Linux: cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Файл backend/.env автоматически загружается. Для локальной разработки используйте DJANGO_DEBUG=true и длинный случайный DJANGO_SECRET_KEY. Django admin доступен по /admin/.

## API

Все endpoints кроме CSRF, регистрации и входа требуют аутентифицированную Django session.

Auth:
- `GET /api/auth/csrf/` — получить CSRF token и cookie.
- `POST /api/auth/register/` — username, nickname, password (минимум 8 символов + Django password validators).
- `POST /api/auth/login/` — username/password.
- `POST /api/auth/logout/` — завершить session.
- `GET /api/auth/me/` — текущий профиль.

Rooms:
- `GET /api/rooms/` — открытые комнаты в ожидании.
- `POST /api/rooms/` — создать комнату (`name`, `max_players`, `is_private`). Создатель автоматически становится участником.
- `GET /api/rooms/<uuid>/` — детали комнаты.
- `POST /api/rooms/<uuid>/join/` — вступить в комнату.
- `POST /api/rooms/<uuid>/ready/` — изменить готовность (`is_ready: true/false`).

Для браузера используй same-origin deployment, credentials включены, а CSRF token передавай в заголовке X-CSRFToken при POST/PUT/PATCH/DELETE.

## Голосовой signaling

`ws://localhost:8000/ws/rooms/<room-uuid>/voice/` — только для авторизованной Django session и участника существующей незавершённой комнаты. Сообщения offer/answer/candidate маршрутизируются целевому user_id. Это signaling foundation, не готовый voice UI: клиентская WebRTC mesh-связь, TURN/STUN и проверка игровых аудиоканалов по фазам ещё требуют интеграции и тестирования.

Для нескольких процессов настройте Redis (`REDIS_URL=redis://...`). InMemoryChannelLayer предназначен только для локальной разработки.

## Запуск UI-прототипа

Из корня репозитория: `python -m http.server 8080`, затем откройте `http://localhost:8080/frontend/`. Комнаты и чат пока демонстрационные и не связаны с API. Для реального использования UI нужно раздавать с того же origin, что и API, либо настроить CORS и cookie policy.

## Перед production

Секретный ключ, ранее закоммиченный в истории репозитория, нужно ротировать и больше не использовать. Установить DJANGO_SECRET_KEY, DJANGO_DEBUG=false, DJANGO_ALLOWED_HOSTS, Redis, HTTPS, secure cookies, CSRF/CORS policy, TURN server, rate limits и тесты. SQLite оставить только для разработки; для production перейти на PostgreSQL.
