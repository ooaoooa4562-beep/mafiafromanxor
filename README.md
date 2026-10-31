# Mafia from Anxor

Онлайн-игра «Мафия»: Django backend и адаптивный браузерный интерфейс.

## Реализованная основа

- `frontend/index.html` и `frontend/app.js` — адаптивный UI, регистрация/вход, список и создание комнат, готовность, серверные роли/фазы, действия игроков и WebSocket-чат.
- `backend/accounts/` — регистрация, вход/выход по Django session, CSRF token и профиль пользователя.
- `backend/rooms/` — API комнат, участники, готовность, выход/передача владельца и WebSocket-чат.
- `backend/game/` — серверное назначение ролей, скрытая выдача своей роли, ночные действия, дневное голосование, таймеры фаз и определение победителя.
- `backend/voice/` — WebRTC signaling с проверкой участника и голосового канала: лобби, мафия ночью, живые игроки днём, отдельный канал выбывших.

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

Главная страница и frontend раздаются Django с одного origin: http://localhost:8000/. Файл backend/.env загружается автоматически. Для локальной разработки оставьте DJANGO_DEBUG=true и замените DJANGO_SECRET_KEY на длинную случайную строку.

## API

Auth: GET `/api/auth/csrf/`, POST `/api/auth/register/`, POST `/api/auth/login/`, POST `/api/auth/logout/`, GET `/api/auth/me/`.

Rooms: GET/POST `/api/rooms/`, GET `/api/rooms/<uuid>/`, POST `/api/rooms/<uuid>/join/`, POST `/api/rooms/<uuid>/ready/`, POST `/api/rooms/<uuid>/leave/`.

Game: POST `/api/game/<uuid>/start/`, GET `/api/game/<uuid>/state/`, POST `/api/game/<uuid>/action/`, POST `/api/game/<uuid>/advance/`.

Начать игру может создатель после того, как минимум 4 игрока присоединились и все отметили готовность. Роли видит только сам игрок. Ночью доступны действия мафии/доктора/комиссара, затем день и голосование. Владелец запускает переход после таймера; автоматический scheduler/worker ещё нужен для production.

## WebSockets

- Чат: `ws://localhost:8000/ws/rooms/<room-uuid>/chat/` — каналы по фазам: лобби, мафия ночью, живые днём и выбывшие отдельно; сообщения до 500 символов.
- WebRTC signaling: `ws://localhost:8000/ws/rooms/<room-uuid>/voice/` — offer/answer/ICE relay; аудио идёт между браузерами через WebRTC, не через Django.

Голосовые каналы ограничены по фазам: в лобби слышат все, ночью — мафия отдельно, выбывшие отдельно, днём — живые игроки вместе. При смене фазы сервер закрывает старые signaling-соединения. Для реального голоса в разных сетях настрой STUN/TURN (TURN обязателен для надёжного production-соединения); фронтенд должен подключать WebRTC peer connections. Пока UI умеет проверить микрофон, но WebRTC-клиент ещё не подключён.

Для нескольких процессов настрой Redis (`REDIS_URL=redis://...`). InMemoryChannelLayer только для локальной разработки.

## Перед production

Секретный ключ, ранее закоммиченный в истории репозитория, нужно ротировать. Установить DJANGO_SECRET_KEY, DJANGO_DEBUG=false, DJANGO_ALLOWED_HOSTS, Redis, HTTPS, secure cookies, CSRF/CORS policy, TURN server, rate limits, PostgreSQL, scheduler и тесты. Не коммитить db.sqlite3, __pycache__ и секреты.
