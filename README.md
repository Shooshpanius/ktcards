# KillTeam Cards

Веб-приложение для отображения карточек команд по игре [Kill Team](https://www.warhammer-community.com/en-gb/kill-team/), организованных по сезонам. Включает публичную страницу с карточками команд и панель администратора для управления данными.

## Стек технологий

| Слой | Технология |
|------|-----------|
| Фронтенд | React 19 + TypeScript + Vite |
| Бэкенд | ASP.NET Core 10 (Web API) |
| База данных (dev) | SQLite (через Entity Framework Core 10) |
| База данных (production) | MySQL / MariaDB |
| Маршрутизация | React Router v7 |
| Контейнеризация | Docker + Docker Compose |

## Структура проекта

```
ktcards/
├── .env.example             # Шаблон переменных окружения для Docker
├── datacards/               # PDF и .bd файлы дата-карт
├── docker-compose.yaml      # Сборка и запуск всех сервисов
├── scripts/                 # Вспомогательные Python-скрипты и SQL-инициализация
│   ├── mariadb_init/        # SQL-скрипты, выполняемые MariaDB при первом старте
│   │   └── 01-grant.sql     # Явная выдача привилегий пользователю ktcards
│   ├── parse_pdf_to_bd.py   # Парсинг PDF в формат .bd (OpenAI)
│   └── import_bd_to_db.py   # Прямой импорт .bd в базу данных MySQL
├── ktcards.Server/          # ASP.NET Core Web API
│   ├── Controllers/
│   │   ├── AuthController.cs          # Аутентификация администратора
│   │   ├── CardsController.cs         # Получение и импорт дата-карт команды
│   │   ├── SeasonsController.cs       # CRUD для сезонов
│   │   └── TeamsController.cs         # CRUD для команд (+ загрузка логотипа)
│   ├── Data/
│   │   └── AppDbContext.cs            # EF Core контекст (SQLite / MySQL)
│   ├── Filters/
│   │   └── AdminAuthorizeAttribute.cs # Фильтр авторизации по Bearer-токену
│   ├── Helpers/
│   │   ├── AdminTokenService.cs       # Генерация и валидация токенов (24 ч)
│   │   └── FileHelper.cs             # Удаление файлов логотипов
│   ├── Migrations/                    # EF Core миграции
│   ├── Models/
│   │   ├── Season.cs
│   │   ├── Team.cs
│   │   ├── Operative.cs
│   │   ├── OperativeAbility.cs
│   │   ├── OperativeAttack.cs
│   │   ├── FactionRule.cs
│   │   ├── MarkerToken.cs
│   │   ├── StrategyPloy.cs
│   │   ├── FirefightPloy.cs
│   │   └── FactionEquipment.cs
│   └── Program.cs
└── ktcards.client/          # React + TypeScript фронтенд
    ├── Dockerfile            # Сборка образа фронтенда (nginx)
    ├── nginx.conf            # Конфиг nginx: статика + прокси /api и /uploads
    └── src/
        ├── components/
        │   └── TeamCard.tsx       # Карточка команды
        ├── pages/
        │   ├── HomePage.tsx       # Публичная страница с карточками команд
        │   ├── AdminPage.tsx      # Панель администратора
        │   └── TeamCardsPage.tsx  # Страница просмотра дата-карт команды
        ├── types.ts               # Типы Season, Team и всех карточных сущностей
        └── App.tsx                # Маршрутизация
```

## Запуск проекта

### Вариант 1 — Docker Compose (рекомендуется для production)

1. Скопируйте `.env.example` в `.env` и заполните значения:

```bash
cp .env.example .env
```

```dotenv
KTCARDS_DB_ROOT_PASSWORD=secret_root
KTCARDS_DB_USER=ktcards
KTCARDS_DB_PASSWORD=secret
```

2. Соберите и запустите образы:

```bash
docker compose build
docker compose up -d
```

| Сервис | URL |
|--------|-----|
| Фронтенд | `http://localhost:84` |
| Бэкенд (API) | `http://localhost:8080` |
| MariaDB | `localhost:3306` (только внутри сети `ktcards_net`) |

Nginx во фронтенд-контейнере проксирует `/api` и `/uploads` на бэкенд автоматически.

### Вариант 2 — локальный запуск (dev)

#### Требования

- [.NET 10 SDK](https://dotnet.microsoft.com/download)
- [Node.js 20+](https://nodejs.org/) и npm

#### Установка зависимостей фронтенда

```bash
cd ktcards.client
npm install
```

#### Запуск через Visual Studio

Откройте `ktcards.slnx` в Visual Studio и запустите решение — бэкенд и фронтенд запустятся совместно.

#### Запуск вручную

**Бэкенд:**
```bash
cd ktcards.Server
dotnet run
```
Сервер запускается на `http://localhost:5069`. SQLite-база (`ktcards.db`) создаётся автоматически при первом запуске.

**Фронтенд (dev-режим):**
```bash
cd ktcards.client
npm run dev
```
Vite проксирует запросы `/api/...` на бэкенд.

## Конфигурация

### Пароль администратора

Задаётся в `appsettings.json`:

```json
{
  "AdminPassword": "your_secure_password"
}
```

### Строка подключения к БД

По умолчанию (dev) используется SQLite. Для переключения на MySQL/MariaDB передайте строку подключения через переменную окружения (например, в Docker Compose):

```
ConnectionStrings__Default=server=<host>;port=3306;database=ktcards;user=<user>;password=<password>;
```

## Аутентификация

Все защищённые эндпоинты требуют Bearer-токена в заголовке `Authorization`.

**Получение токена:**

```
POST /api/auth/login
Content-Type: application/json

{ "password": "your_admin_password" }
```

Токен действителен 24 часа. Передавайте его во все защищённые запросы:

```
Authorization: Bearer <token>
```

## API

Базовый URL: `http://localhost:5069`

### Аутентификация

| Метод | URL | Описание |
|-------|-----|----------|
| `POST` | `/api/auth/login` | Получить токен `{ "password": "..." }` |

### Сезоны

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| `GET` | `/api/seasons` | Публичный | Список всех сезонов с командами |
| `POST` | `/api/seasons` | 🔒 Админ | Создать сезон `{ "name": "..." }` |
| `DELETE` | `/api/seasons/{id}` | 🔒 Админ | Удалить сезон и все его команды |

### Команды

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| `GET` | `/api/teams` | Публичный | Список всех команд |
| `POST` | `/api/teams` | 🔒 Админ | Создать команду (`multipart/form-data`: `name`, `seasonId`, `logo?`) |
| `DELETE` | `/api/teams/{id}` | 🔒 Админ | Удалить команду |

Загруженные логотипы сохраняются в `wwwroot/uploads/` и доступны по пути `/uploads/<filename>`.

### Дата-карты команды

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| `GET` | `/api/teams/{teamId}/cards` | Публичный | Все карты команды (оперативники, плои и т.д.) |
| `POST` | `/api/teams/{teamId}/cards/import` | 🔒 Админ | Импортировать карты из файла `<TeamName>.bd` |

## Типы дата-карт команды

Дата-карты команды бывают нескольких типов:

- **Карты оперативников** — статы, способности, атаки каждого бойца
- **Карта описания состава команды** — общее описание фракции
- **Faction Rule** — правила команды
- **Marker/Token Guide** — описание токенов и маркеров команды
- **Strategy Ploy** — плои стратегии
- **Firefight Ploy** — плои перестрелки
- **Faction Equipment** — снаряжение фракции

## Страницы

- **`/`** — публичная страница: отображает карточки команд, сгруппированные по сезонам.
- **`/teams/:teamId`** — страница команды: все дата-карты (оперативники, faction rules, плои, снаряжение).
- **`/admin`** — панель администратора: управление сезонами и командами, импорт дата-карт из `.bd` файлов.

## Python-скрипты

### parse_pdf_to_bd.py

Парсит PDF с дата-картами команды в формат `.bd` с помощью `pdfplumber` + OpenAI GPT-4o.

**Требования:** `pip install pdfplumber openai` и переменная окружения `OPENAI_API_KEY`.

```bash
python scripts/parse_pdf_to_bd.py datacards/TeamName.pdf
# создаёт datacards/TeamName.bd
```

### import_bd_to_db.py

Напрямую импортирует `.bd` файлы в базу данных MySQL (обходит веб-API).

**Требования:** `pip install pymysql`

```bash
# Импорт всех .bd файлов из datacards/
python scripts/import_bd_to_db.py --host 127.0.0.1 --user root --password secret --database ktcards

# Импорт конкретного файла
python scripts/import_bd_to_db.py datacards/TeamName.bd --season-id 1
```

Параметры подключения также принимаются через переменные окружения: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`.

## Сборка фронтенда для production

```bash
cd ktcards.client
npm run build
```

Собранные файлы помещаются в `wwwroot` бэкенда и раздаются им как статика.

## Устранение неполадок

### `Access denied for user 'ktcards'@'...'` при старте бэкенда

**Причина.** MariaDB Docker выполняет инициализацию пользователя (`MYSQL_USER` / `MYSQL_PASSWORD`) и выдачу привилегий **только при первом запуске**, когда директория с данными пуста. Если том `/opt/docker/data/_ktcards/mariadb_ktcards` уже содержал данные от предыдущего деплоя, пользователь `ktcards` мог не получить доступ к базе.

**Вариант 1 — ручная выдача привилегий (данные сохраняются):**

```bash
source .env   # загрузить переменные KTCARDS_DB_ROOT_PASSWORD и KTCARDS_DB_PASSWORD
docker exec mariadb_ktcards \
  mysql -uroot -p"${KTCARDS_DB_ROOT_PASSWORD}" -e \
  "GRANT ALL PRIVILEGES ON \`ktcards\`.* TO 'ktcards'@'%' IDENTIFIED BY '${KTCARDS_DB_PASSWORD}'; FLUSH PRIVILEGES;"
```

После этого перезапустите бэкенд:
```bash
docker compose restart back_ktcards
```

**Вариант 2 — сброс тома MariaDB (все данные удаляются):**

```bash
docker compose down
sudo rm -rf /opt/docker/data/_ktcards/mariadb_ktcards
docker compose up -d
```

MariaDB переинициализируется с нуля: база `ktcards`, пользователь и привилегии будут созданы автоматически, а скрипт `scripts/mariadb_init/01-grant.sql` дополнительно подтвердит права.

> **Почему не возникает при свежей установке?** Директория `scripts/mariadb_init/` монтируется в `/docker-entrypoint-initdb.d/` контейнера MariaDB, поэтому скрипт `01-grant.sql` выполняется при каждой **первой** инициализации и явно выдаёт привилегии.
