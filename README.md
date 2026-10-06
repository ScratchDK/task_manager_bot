# 🚀 Task Manager Bot
Телеграм-бот для управления задачами с возможностью назначать исполнителей, ставить дедлайны и приоритеты.
Бэкенд на FastAPI, база данных PostgreSQL, асинхронный ORM SQLAlchemy, кеширование состояний через Redis, бот на Aiogram 3.

**📌 Статус: Проект в активной разработке. Функционал и интерфейс будут дополняться и улучшаться.**

## 🛠️ Технологии

- **FastAPI** - современный веб-фреймворк для API
- **Aiogram 3** - асинхронный фреймворк для Telegram ботов
- **SQLAlchemy 2.0 (asyncio)** - ORM для работы с PostgreSQL
- **Alembic** - управление миграциями базы данных
- **PostgreSQL** - основная база данных
- **Redis** - хранение состояний FSM (диалогов)
- **Celery** - фоновые задачи и уведомления
- **Docker / Docker Compose** - контейнеризация всего стека
- **Pytest** - тестирование

## 📋 Функционал

### Бот
- ✅ Регистрация пользователей через Telegram (`/start`)
- ✅ Создание задач (заголовок, описание, дедлайн, приоритет, категория)
- ✅ Назначение исполнителя (по username или telegram_id)
- ✅ Авторегистрация исполнителей (даже если не запускали бота)
- ✅ Полный цикл согласования: `pending → in_progress → review → completed`
- ✅ Комментарий исполнителя при отправке на проверку
- ✅ Deep-link для быстрого принятия задачи
- ✅ Пагинация в `/my_tasks` (по 5 задач на страницу)
- ✅ Категории задач (CRUD)
- ✅ Уведомления через Celery
- ✅ Автоотмена задач при неактивном исполнителе

### API
- ✅ REST API v1 (`/api/v1`)
- ✅ CRUD для задач
- ✅ Получение информации о пользователях
- ✅ Swagger UI (`/docs`)

### Качество кода
- ✅ Middleware для управления сессиями БД в aiogram
- ✅ Dependency Injection (`db: AsyncSession` в хендлерах)
- ✅ 32 теста для сервисов и API
- ✅ Модульная архитектура

## 🐳 Запуск через Docker

1. Клонировать репозиторий
    ```bash
    git clone https://github.com/ScratchDK/task_manager_bot.git
    cd task_manager_bot

2. Создать файл .env на основе .env.example:
    ```bash
    cp .env.example .env

3. Запустить контейнеры
    ```bash
    docker-compose up --build -d
   
4. Применить миграции
    ```bash
    docker-compose exec web alembic upgrade head

5. Остановить контейнеры
    ```bash
    docker-compose down

## 🧪 Запуск тестов

```bash
pytest tests/ -v
```

**Покрытие:** 32 теста (сервисы + API)

## 🤖 Команды бота

| Command      | Description                   |
|--------------|-------------------------------|
| /start       | Регистрация и приветствие     |
| /new_task    | Создать новую задачу (диалог) |
| /my_tasks    | Показать список своих задач   |
| /categories  | Показать список категорий     |
| /help        | Помощь                        |

## 📡 API эндпоинты

### Пользователи
- `GET /api/v1/users/{telegram_chat_id}` — информация о пользователе

### Задачи
- `GET /api/v1/tasks/user/{telegram_chat_id}` — задачи пользователя
- `GET /api/v1/tasks/{task_id}` — задача по ID
- `POST /api/v1/tasks/` — создать задачу
- `PATCH /api/v1/tasks/{task_id}` — обновить задачу
- `DELETE /api/v1/tasks/{task_id}` — удалить задачу

**Swagger UI:** `http://localhost:8000/docs`

## 📁 Структура проекта
```
task_manager_bot/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── schemas.py     # Pydantic-схемы
│   │       ├── tasks.py       # Эндпоинты задач
│   │       └── users.py       # Эндпоинты пользователей
│   ├── bot/
│   │   ├── dialogs/           # Диалоги (FSM)
│   │   ├── handlers/          # Обработчики команд
│   │   ├── middlewares/       # Middleware (сессии БД)
│   │   ├── utils/
│   │   └── dispatcher.py      # Настройка бота
│   ├── core/
│   │   ├── config.py          # Pydantic настройки
│   │   ├── database.py        # Подключение к БД
│   │   └── celery.py          # Настройка Celery
│   ├── models/                # SQLAlchemy модели (User, Task, Category)
│   ├── services/              # Бизнес-логика
│   ├── main.py                # Точка входа FastAPI
│   └── dependencies.py        # DI для FastAPI
├── alembic/                   # Миграции
├── tests/                     # Тесты
│   ├── conftest.py
│   ├── test_api_tasks.py
│   ├── test_task_service.py
│   ├── test_user_service.py
│   └── test_category_service.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
├── .env.example
└── README.md
```

## 📝 TODO

- Webhook (переключатель polling/webhook)
- JWT-авторизация для API
- Email + пароль регистрация
- Роли и права доступа
- Редактирование задач
- Тэги / метки для задач
- Отчёты и аналитика
- Деплой на продакшн

## 🧪 Как протестировать

1. Найди своего бота в Telegram.
2. Отправь `/start`.
3. Создай задачу через `/new_task`.
4. Назначь исполнителя (можно себя) и проверь уведомление.
5. Посмотри список задач через `/my_tasks`.
6. Открой Swagger (`/docs`) и проверь API.

## 📄 Лицензия

**MIT © Коваль Дмитрий**
