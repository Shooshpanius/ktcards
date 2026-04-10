# KillTeam Cards

Веб-приложение для отображения карточек команд по игре [Kill Team](https://www.warhammer-community.com/en-gb/kill-team/), организованных по сезонам. Включает публичную страницу с карточками команд и панель администратора для управления данными.

## Стек технологий

| Слой | Технология |
|------|-----------|
| Фронтенд | React 19 + TypeScript + Vite |
| Бэкенд | ASP.NET Core 10 (Web API) |
| База данных | SQLite (через Entity Framework Core 10) |
| Маршрутизация | React Router v7 |

## Структура проекта

```
ktcards/
├── ktcards.Server/          # ASP.NET Core Web API
│   ├── Controllers/
│   │   ├── SeasonsController.cs   # CRUD для сезонов
│   │   └── TeamsController.cs     # CRUD для команд (+ загрузка логотипа)
│   ├── Data/
│   │   └── AppDbContext.cs        # EF Core контекст (SQLite)
│   ├── Models/
│   │   ├── Season.cs
│   │   └── Team.cs
│   ├── Helpers/
│   │   └── FileHelper.cs          # Удаление файлов логотипов
│   └── Program.cs
└── ktcards.client/          # React + TypeScript фронтенд
    └── src/
        ├── pages/
        │   ├── HomePage.tsx       # Публичная страница с карточками
        │   └── AdminPage.tsx      # Панель администратора
        ├── components/
        │   └── TeamCard.tsx       # Компонент карточки команды
        ├── types.ts               # Типы Season и Team
        └── App.tsx                # Маршрутизация
```

## Запуск проекта

### Требования

- [.NET 10 SDK](https://dotnet.microsoft.com/download)
- [Node.js 20+](https://nodejs.org/) и npm

### Установка зависимостей фронтенда

```bash
cd ktcards.client
npm install
```

### Запуск через Visual Studio

Откройте `ktcards.slnx` в Visual Studio и запустите решение — бэкенд и фронтенд запустятся совместно.

### Запуск вручную

**Бэкенд:**
```bash
cd ktcards.Server
dotnet run
```
Сервер запускается на `http://localhost:5069`. База данных (`ktcards.db`) создаётся автоматически при первом запуске.

**Фронтенд (dev-режим):**
```bash
cd ktcards.client
npm run dev
```
Vite проксирует запросы `/api/...` на бэкенд.

## API

Базовый URL: `http://localhost:5069`

### Сезоны

| Метод | URL | Описание |
|-------|-----|----------|
| `GET` | `/api/seasons` | Список всех сезонов с командами |
| `POST` | `/api/seasons` | Создать сезон `{ "name": "..." }` |
| `DELETE` | `/api/seasons/{id}` | Удалить сезон и все его команды |

### Команды

| Метод | URL | Описание |
|-------|-----|----------|
| `GET` | `/api/teams` | Список всех команд |
| `POST` | `/api/teams` | Создать команду (`multipart/form-data`: `name`, `seasonId`, `logo?`) |
| `DELETE` | `/api/teams/{id}` | Удалить команду |

Загруженные логотипы сохраняются в `wwwroot/uploads/` и доступны по пути `/uploads/<filename>`.

## Страницы

- **`/`** — публичная страница: отображает карточки команд, сгруппированные по сезонам.
- **`/admin`** — панель администратора: добавление и удаление сезонов и команд с возможностью загрузки логотипа.

## Сборка фронтенда для production

```bash
cd ktcards.client
npm run build
```

Собранные файлы помещаются в `wwwroot` бэкенда и раздаются им как статика.
