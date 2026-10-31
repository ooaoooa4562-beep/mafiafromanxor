# Mafia from Anxor

Онлайн-игра «Мафия»: Django backend и адаптивный браузерный интерфейс.

## Реализованная основа

- `frontend/index.html` — адаптивный UI-прототип: список комнат, создание комнаты, вход по коду, игровая комната, чат-интерфейс и локальная проверка микрофона.
- `backend/accounts/` — регистрация, вход/выход по Django session, CSRF token и профиль пользователя.
- `backend/rooms/` — API комнат, участники, готовность, выход/передача владельца и WebSocket-чат.
- `backend/game/` — серверное назначение ролей, скрытая выдача своей роли, действия ночью, дневное голосование, таймеры фаз и определение победителя.
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

Файл backend/.env автоматически загружается. Для локальной разработки оставьте DJANGO_DEBUG=true и замените DJANGO_SECRET_KEY на длинную случайную строку. Django admin доступен по /admin/.

## API

Auth: GET `/api/auth/csrf/`, POST `/api/auth/register/`, POST `/api/auth/login/`, POST `/api/auth/logout/`, GET `/api/auth/me/`.

Rooms: GET/POST `/api/rooms/`, GET `/api/rooms/<uuid>/`, POST `/api/rooms/<uuid>/join/`, POST `/api/rooms/<uuid>/ready/`, POST `/api/rooms/<uuid>/leave/`.

Game: POST `/api/game/<uuid>/start/`, GET `/api/game/<uuid>/state/`, POST `/api/game/<uuid>/action/`, POST `/api/game/<uuid>/advance/`.

Все игровые endpoints требуют авторизованного участника комнаты. Начать игру может создатель после того, как минимум 4 игрока присоединились и все нажали «готов». Роли видит только сам игрок. Ночью доступны действия мафии/доктора/комиссара, днём — обсуждение, затем голосование. Переход фаз сейчас запускается запросом владельца комнаты после истечения таймера; для production нужен серверный scheduler/worker и широковещательные события.

Для браузера используй same-origin deployment, credentials включены, а CSRF token передавай в заголовке X-CSRFToken при POST/PUT/PATCH/DELETE.

## Голосовой signaling

`ws://localhost:8000/ws/rooms/<room-uuid>/voice/` — только для авторизованной Django session и участника существующей незавершённой комнаты. Сообщения offer/answer/candidate маршрутизируются целевому user_id. Это signaling foundation, не готовый voice UI: клиентская WebRTC mesh-связь, TURN/STUN и проверка игровых аудиоканалов по фазам ещё требуют интеграции и тестирования.

WebSocket-чат: `ws://localhost:8000/ws/rooms/<room-uuid>/chat/` (только участники комнаты, сообщения до 500 символов).\n\nДля нескольких процессов настройте Redis (`REDIS_URL=redis://...`). InMemoryChannelLayer предназначен только для локальной разработки.

## Запуск UI-прототипа

Из корня репозитория: `python -m http.server 8080`, затем откройте `http://localhost:8080/frontend/`. Комнаты и чат пока демонстрационные и не связаны с API. Для реального использования UI нужно раздавать с того же origin, что и API, либо настроить CORS и cookie policy.

## Перед production

Секретный ключ, ранее закоммиченный в истории репозитория, нужно ротировать и больше не использовать. Установить DJANGO_SECRET_KEY, DJANGO_DEBUG=false, DJANGO_ALLOWED_HOSTS, Redis, HTTPS, secure cookies, CSRF/CORS policy, TURN server, rate limits и тесты. SQLite оставить только для разработки; для production перейти на PostgreSQL.
