# Security Audit — ktcards

> Дата аудита: 2026-04-14  
> Состояние кодовой базы: после отмены PR #32 (master без security-хардинга)

---

## 🔴 КРИТИЧЕСКИЕ уязвимости

### ~~1. Предсказуемый токен аутентификации (GUID)~~ ✅ ИСПРАВЛЕНО
- **Файл:** `ktcards.Server/Helpers/AdminTokenService.cs`
- **Проблема:** `Guid.NewGuid().ToString("N")` — GUID-ы не являются криптографически безопасными источниками случайных данных. Возможна частичная предсказуемость при некоторых реализациях.
- **Решение:** Заменить на `RandomNumberGenerator.GetHexString(32)` (или `Convert.ToHexString(RandomNumberGenerator.GetBytes(32))`).
- **Статус:** Используется `Convert.ToHexString(RandomNumberGenerator.GetBytes(32))`.

---

### ~~2. Токен хранится в `sessionStorage` (доступен через XSS)~~ ✅ ИСПРАВЛЕНО
- **Файл:** `ktcards.client/src/pages/AdminPage.tsx`
- **Проблема:** `sessionStorage.setItem(SESSION_KEY, data.token)` — любой XSS-вектор в приложении получает прямой доступ к токену администратора.
- **Решение:** Перевести на `HttpOnly`-куки (флаги `HttpOnly`, `SameSite=Lax`, `Secure`). Серверные эндпоинты: `GET /api/auth/check` (проверка состояния), `POST /api/auth/logout` (инвалидация).
- **Статус:** Токен устанавливается сервером через `HttpOnly`-куку. Клиент использует `GET /api/auth/check` для проверки сессии и `POST /api/auth/logout` для выхода. Заголовок `Authorization` больше не используется.

---

### ~~3. Загрузка файла без проверки типа и размера (RCE / хранилище)~~ ✅ ИСПРАВЛЕНО
- **Файл:** `ktcards.Server/Controllers/TeamsController.cs` (метод `Create`)
- **Проблема:** Расширение файла берётся из `dto.Logo.FileName` без валидации. `ContentType` не проверяется. Лимит размера не задан на уровне контроллера. Возможна загрузка произвольных файлов (`.php`, `.aspx`, скрипты).
- **Решение:**
  - Белый список расширений: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`.
  - Проверять `ContentType` (MIME-тип).
  - Ограничить размер файла (например, ≤ 5 МБ).
  - Имя файла генерировать самостоятельно (`Guid.NewGuid() + ext`), не доверять оригинальному имени.
- **Статус:** Добавлены проверки расширения (белый список), ContentType и лимит 5 МБ. Расширение нормализуется в нижний регистр, имя файла генерируется через `Guid.NewGuid()`.

---

### ~~4. Path Traversal при удалении логотипа~~ ✅ ИСПРАВЛЕНО
- **Файл:** `ktcards.Server/Helpers/FileHelper.cs`
- **Проблема:** `logoPath` напрямую конкатенируется с путём без канонизации. Если значение в БД будет изменено злоумышленником (например, `../../appsettings.json`), возможно удаление произвольного файла.
- **Решение:** Канонизировать итоговый путь с помощью `Path.GetFullPath` и убедиться, что он начинается с разрешённой директории `wwwroot/uploads/`.
- **Статус:** Путь канонизируется через `Path.GetFullPath`, проверяется, что итоговый путь начинается с `wwwroot/uploads/`. Если нет — операция отменяется.

---

### ~~5. Деструктивная операция `EnsureDeleted()` в production~~ ✅ ИСПРАВЛЕНО
- **Файл:** `ktcards.Server/Program.cs`
- **Проблема:** При ошибке миграции вызывался `db.Database.EnsureDeleted()` — **полное уничтожение базы данных в production!**
- **Решение:** Убрать `EnsureDeleted()` из блока catch. Логировать ошибку и завершать приложение исключением (fail fast).
- **Статус:** `EnsureDeleted()` удалён. В catch логируется критическая ошибка через `ILogger`, после чего исключение пробрасывается (`throw`), останавливая приложение.

---

## 🟠 ВЫСОКИЕ уязвимости

### ~~6. Отсутствие rate limiting на `/api/auth/login`~~ ✅ ИСПРАВЛЕНО
- **Файл:** `ktcards.Server/Controllers/AuthController.cs`
- **Проблема:** Нет защиты от брутфорса. Злоумышленник может неограниченно перебирать пароли.
- **Решение:** Добавить `AddRateLimiter` (ASP.NET Core built-in) — например, 10 запросов/мин на IP. Учитывать реальный IP клиента через `UseForwardedHeaders` (за nginx).
- **Статус:** Добавлен `AddRateLimiter` с `FixedWindowLimiter` (10 запросов/мин на IP). Подключены `UseForwardedHeaders` и `UseRateLimiter`. Эндпоинт `/api/auth/login` защищён атрибутом `[EnableRateLimiting("login")]`.

---

### ~~7. Нет эндпоинта выхода (logout) / инвалидации токена~~ ✅ ИСПРАВЛЕНО
- **Файл:** `ktcards.Server/Controllers/AuthController.cs`
- **Проблема:** Токен нельзя инвалидировать на сервере. При компрометации токена нет способа его отозвать.
- **Решение:** Добавить `POST /api/auth/logout` — удаляет токен из `AdminTokenService`.
- **Статус:** Добавлен эндпоинт `POST /api/auth/logout`, который отзывает токен через `AdminTokenService.RevokeToken()` и удаляет `HttpOnly`-куку. Клиент вызывает `/api/auth/logout` при выходе из панели администратора.

---

### 8. Дефолтный пароль администратора в репозитории
- **Файл:** `ktcards.Server/appsettings.json`
- **Проблема:** `"AdminPassword": "change_me_before_deploy"` — слабый дефолт, который легко забыть поменять при деплое.
- **Решение:**
  - Установить значение `""` (пустое) в `appsettings.json`.
  - Добавить проверку при старте: если `AdminPassword` пустой — выбрасывать исключение (`throw new InvalidOperationException`), запрещая запуск без настройки.
  - Добавить `KTCARDS_ADMIN_PASSWORD` в `.env.example` и `docker-compose.yaml`.

---

### 9. Пароль БД в `appsettings.Development.json`
- **Файл:** `ktcards.Server/appsettings.Development.json`
- **Проблема:** `"password=ktcards;"` — учётные данные в открытом виде в репозитории.
- **Решение:** Заменить на плейсхолдер `REPLACE_ME`. Использовать User Secrets (`dotnet user-secrets`) или переменные окружения для локальной разработки.

---

## 🟡 СРЕДНИЕ уязвимости

### 10. Отсутствие security-заголовков в nginx
- **Файл:** `ktcards.client/nginx.conf`
- **Проблема:** Отсутствуют заголовки: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`. Возможны атаки Clickjacking, MIME sniffing.
- **Решение:** Добавить в конфигурацию nginx:
  ```
  add_header X-Content-Type-Options "nosniff" always;
  add_header X-Frame-Options "SAMEORIGIN" always;
  add_header Referrer-Policy "strict-origin-when-cross-origin" always;
  add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
  ```

---

### 11. Отсутствие `proxy_set_header` для реального IP клиента
- **Файл:** `ktcards.client/nginx.conf`
- **Проблема:** Без `proxy_set_header X-Real-IP` и `X-Forwarded-For` бэкенд видит IP самого nginx, а не реального пользователя. Rate limiting по IP работать не будет корректно.
- **Решение:** Добавить в секцию `location /api`:
  ```
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
  ```
  Включить `UseForwardedHeaders` middleware в `Program.cs`.

---

### 12. Отсутствие KTCARDS_ADMIN_PASSWORD в инфраструктурных файлах
- **Файлы:** `.env.example`, `docker-compose.yaml`
- **Проблема:** Переменная для пароля администратора не описана в шаблоне `.env`, что ведёт к неправильной конфигурации при деплое.
- **Решение:** Добавить `KTCARDS_ADMIN_PASSWORD=` в `.env.example` и передавать через `environment:` в `docker-compose.yaml`.

---

## 🟢 НИЗКИЕ / ТЕХНИЧЕСКИЙ ДОЛГ

### 13. Scaffolding-файлы в production коде
- **Файлы:** `ktcards.Server/Controllers/WeatherForecastController.cs`, `ktcards.Server/WeatherForecast.cs`
- **Проблема:** Стандартные файлы ASP.NET шаблона не удалены. Лишняя поверхность атаки, путаница в коде.
- **Решение:** Удалить оба файла.

---

### 14. SQLite-файлы БД в репозитории
- **Файлы:** `ktcards.Server/ktcards.db`, `ktcards.Server/ktcards.db-shm`, `ktcards.Server/ktcards.db-wal`
- **Проблема:** Бинарные файлы базы данных попали в git (в т.ч. из-за отката PR #32). Могут содержать персональные/служебные данные.
- **Решение:**
  - Добавить в `.gitignore`:
    ```
    *.db
    *.db-shm
    *.db-wal
    ```
  - Удалить файлы из истории git (при необходимости — `git filter-branch` или `git-filter-repo`).

---

## Сводная таблица приоритетов

| # | Уязвимость | Критичность | Сложность фикса |
|---|-----------|-------------|-----------------|
| 1 | ~~Предсказуемый токен (GUID)~~ ✅ | 🔴 Критическая | Низкая |
| 2 | ~~Токен в sessionStorage (XSS)~~ ✅ | 🔴 Критическая | Средняя |
| 3 | ~~Загрузка файлов без проверки~~ ✅ | 🔴 Критическая | Низкая |
| 4 | ~~Path Traversal при удалении файла~~ ✅ | 🔴 Критическая | Низкая |
| 5 | ~~EnsureDeleted() в production~~ ✅ | 🔴 Критическая | Низкая |
| 6 | ~~Нет rate limiting на login~~ ✅ | 🟠 Высокая | Средняя |
| 7 | ~~Нет logout / инвалидации токена~~ ✅ | 🟠 Высокая | Низкая |
| 8 | Дефолтный пароль в репозитории | 🟠 Высокая | Низкая |
| 9 | Пароль БД в dev-конфиге | 🟠 Высокая | Низкая |
| 10 | Нет security-заголовков nginx | 🟡 Средняя | Низкая |
| 11 | Нет proxy forwarding IP | 🟡 Средняя | Низкая |
| 12 | AdminPassword не в .env.example | 🟡 Средняя | Низкая |
| 13 | Scaffolding WeatherForecast | 🟢 Низкая | Минимальная |
| 14 | SQLite файлы в git | 🟢 Низкая | Низкая |
