# Mafia from Anxor

Веб-игра «Мафия»: Django backend + браузерный интерфейс.

## Что уже заложено

- `frontend/index.html` — адаптивный UI-прототип: список комнат, создание комнаты, вход по коду, игровая комната, чат-интерфейс и локальная проверка микрофона.
- `backend/rooms/` — API комнат, участники, готовность и миграция базы данных.
- `backend/voice/` — аутентифицированный WebSocket relay для WebRTC SDP/ICE сигналинга. Сам аудиопоток идёт через WebRTC между браузерами, а не через Django Channels.
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

Настройки автоматически загружают backend/.env. Для локальной разработки оставьте DJANGO_DEBUG=true и замените DJANGO_SECRET_KEY на длинную случайную строку. Не используйте примерный ключ в production.

## API комнат

Все endpoints требуют аутентифицированную Django session:
- `GET /api/rooms/` — открытые комнаты в ожидании.
- `POST /api/rooms/` — создать комнату (`name`, `max_players`, `is_private`). Создатель автоматически становится участником.
- `GET /api/rooms/<uuid>/` — детали комнаты.
- `POST /api/rooms/<uuid>/join/` — вступить в комнату.
- `POST /api/rooms/<uuid>/ready/` — изменить готовность (`is_ready: true/false`).

## Голосовой signaling

`ws://localhost:8000/ws/rooms/<room-uuid>/voice/` — только для авторизованной Django session и существующей незавершённой комнаты. Сообщения offer/answer/candidate маршрутизируются целевому user_id. Это signaling foundation, не готовый voice UI: клиентская WebRTC mesh-связь, TURN/STUN и проверка членства/прав по фазам ещё требуют интеграции и тестирования.

Для нескольких процессов обязательно настройте Redis (`REDIS_URL=redis://...`). InMemoryChannelLayer предназначен только для локальной разработки.

## Запуск UI-прототипа

Из корня репозитория: `python -m http.server 8080`, затем откройте `http://localhost:8080/frontend/`. Комнаты и чат пока демонстрационные и не связаны с API.

## Перед production

Секретный ключ, ранее закоммиченный в истории репозитория, нужно ротировать и больше не использовать. Установить DJANGO_SECRET_KEY, DJANGO_DEBUG=false, DJANGO_ALLOWED_HOSTS, Redis, HTTPS, secure cookies, CSRF/CORS policy, TURN server, rate limits и тесты. SQLite оставить только для разработки; для production перейти на PostgreSQL.
