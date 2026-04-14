# Security & Quality Audit — ktcards

> Дата аудита: 2026-04-14  
> Состояние кодовой базы: после завершения первого цикла security-хардинга (PR #32 отменён → исправлен)

---

## 🔴 КРИТИЧЕСКИЕ уязвимости

### ~~1. XSS через загрузку SVG-логотипа~~ ✅ ИСПРАВЛЕНО
- **Файл:** `ktcards.Server/Controllers/TeamsController.cs`
- **Проблема:** `.svg` включён в белый список расширений логотипов. SVG — XML-файл, который может содержать `<script>` теги. Браузер исполнит JS при открытии файла напрямую (`/uploads/xxx.svg`). Кука `admin_token` защищена флагом `HttpOnly`, однако атака может использовать CSRF, читать другие cookie или манипулировать DOM.
- **Решение:** Убрать `.svg` / `image/svg+xml` из белых списков. Если SVG необходим, добавить серверную санитизацию (например, библиотека `Svg.Net` с удалением скриптов) или раздавать SVG с заголовком `Content-Disposition: attachment`.
- **Статус:** Разрешённые расширения: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp` — SVG отсутствует.

---

### ~~2. Обход rate limiting через подделку `X-Forwarded-For`~~ ✅ ИСПРАВЛЕНО
- **Файл:** `ktcards.Server/Program.cs`
- **Проблема:** `options.KnownIPNetworks.Clear()` и `options.KnownProxies.Clear()` заставляют ASP.NET Core доверять заголовку `X-Forwarded-For` от **любого** хоста. Злоумышленник может поставить `X-Forwarded-For: 1.2.3.4` в каждом запросе, имитируя разные IP, и обходить rate limiter на `/api/auth/login`.
- **Решение:** Указать конкретный IP nginx-контейнера в `KnownProxies` (или подсеть Docker-сети в `KnownIPNetworks`) вместо полной очистки списков.
- **Статус:** `KnownIPNetworks` настроен на Docker-подсеть `172.16.0.0/12`.

---

## 🟠 ВЫСОКИЕ уязвимости

### ~~3. `.env` не добавлен в `.gitignore`~~ ✅ ИСПРАВЛЕНО
- **Файл:** `.gitignore`
- **Проблема:** В `.gitignore` нет паттерна для `.env`. Если разработчик создаст `.env` с реальными паролями (`KTCARDS_ADMIN_PASSWORD`, `KTCARDS_DB_PASSWORD` и т.д.), он может случайно попасть в репозиторий.
- **Решение:** Добавить `.env` в `.gitignore`. Сохранить только `.env.example`.
- **Статус:** Паттерны `.env`, `.env.local`, `.env.*.local` добавлены в `.gitignore`.

---

### ~~4. Отсутствие Content-Security-Policy (CSP)~~ ✅ ИСПРАВЛЕНО
- **Файл:** `ktcards.client/nginx.conf`
- **Проблема:** Нет заголовка `Content-Security-Policy`. Без CSP любой XSS-вектор (например, через данные карточек, импортированных из `.bd`-файла) может загружать внешние ресурсы и выполнять произвольный JS.
- **Решение:** Добавить строгий CSP, например:
  ```
  add_header Content-Security-Policy "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; object-src 'none'; frame-ancestors 'none';" always;
  ```
- **Статус:** CSP-заголовок добавлен в `nginx.conf`.

---

### ~~5. Rate limit слишком мягкий (30 запросов/мин)~~ ✅ ИСПРАВЛЕНО
- **Файл:** `ktcards.Server/Program.cs`
- **Проблема:** `PermitLimit = 30` позволяет делать 30 попыток подбора пароля за минуту. При 8-символьном пароле из строчных букв это открывает возможность для медленного брутфорса. В комментариях предыдущего аудита фигурировало значение 10.
- **Решение:** Снизить лимит до 5–10 запросов в минуту. Рассмотреть прогрессивные задержки или блокировку IP после N неудачных попыток.
- **Статус:** `PermitLimit` снижен до 10.

---

### ~~6. Отсутствие таймаута у `HttpClient` при импорте карточек~~ ✅ ИСПРАВЛЕНО
- **Файл:** `ktcards.Server/Controllers/CardsController.cs`
- **Проблема:** `httpClientFactory.CreateClient()` создаёт клиент с дефолтным таймаутом 100 секунд. Если GitHub API не ответит, запрос к `/api/teams/{id}/cards/import` завис на 100 с, блокируя поток. Злоумышленник с правами администратора может вызвать DoS серверных потоков.
- **Решение:** Зарегистрировать именованный `HttpClient` с коротким таймаутом (например, 10–15 с) через `builder.Services.AddHttpClient("github", c => c.Timeout = TimeSpan.FromSeconds(15))`.
- **Статус:** Именованный клиент `"github"` с таймаутом 15 с зарегистрирован в `Program.cs`; `CardsController` обновлён для его использования.

---

## 🟡 СРЕДНИЕ уязвимости

### ~~7. Race condition при параллельном импорте карточек~~ ✅ ИСПРАВЛЕНО
- **Файл:** `ktcards.Server/Controllers/CardsController.cs`
- **Проблема:** Два одновременных запроса `POST /api/teams/{id}/cards/import` удаляют старые карточки и вставляют новые без блокировки. Оба запроса могут пройти фазу удаления параллельно, затем оба вставят данные — в итоге карточки задвоятся.
- **Решение:** Добавить транзакцию (`db.Database.BeginTransactionAsync`) или семафор на уровне `teamId` (например, `SemaphoreSlim` в `ConcurrentDictionary`).
- **Статус:** `SemaphoreSlim` через `ConcurrentDictionary<int, SemaphoreSlim>` на уровне `teamId` добавлен. Повторный импорт для той же команды возвращает 409 Conflict.

---

### ~~8. Нет защиты от CSRF на мутирующих эндпоинтах~~ ✅ ИСПРАВЛЕНО
- **Файлы:** `ktcards.Server/Controllers/AuthController.cs`, `TeamsController.cs`, `SeasonsController.cs`, `CardsController.cs`
- **Проблема:** `SameSite=Lax` защищает от CSRF при cross-site навигации в большинстве браузеров, но не от атак через `<form>` (метод POST в HTML-форме кросс-сайт). При `SameSite=Lax` куки передаются только при "top-level navigation" с безопасными методами; для POST из стороннего сайта куки не передаются — это частичная защита. Однако если приложение когда-либо переедет на `SameSite=None` (например, для iframe), CSRF станет реальной угрозой.
- **Решение:** Добавить явную CSRF-защиту через `IAntiforgery` (ASP.NET Core) или Double Submit Cookie pattern. Как минимум — задокументировать, что `SameSite=Lax` является текущей защитой.
- **Статус:** Добавлена явная CSRF-защита через `IAntiforgery` ASP.NET Core. Эндпоинт `GET /api/auth/csrf` выдаёт токен; `AntiforgeryValidationFilter` валидирует заголовок `X-CSRF-TOKEN` на всех мутирующих запросах к TeamsController, SeasonsController и CardsController. Фронтенд обновлён — все мутирующие fetch-вызовы используют `csrfFetch`, который автоматически добавляет токен.

---

### ~~9. HTTP без HTTPS — нет TLS и перенаправления~~ ✅ ИСПРАВЛЕНО
- **Файл:** `ktcards.client/nginx.conf`
- **Проблема:** nginx слушает только `port 80`. Нет HTTPS-блока и нет редиректа с HTTP на HTTPS. Все данные (включая `admin_token` куку при первом запросе) передаются в открытом виде. Флаг `Secure` на куке устанавливается в production, но nginx сам не терминирует TLS.
- **Решение:** Добавить HTTPS-блок (SSL/TLS termination) в nginx.conf с редиректом с HTTP на HTTPS. Рассмотреть интеграцию с Let's Encrypt через Certbot или внешний реверс-прокси.
- **Статус:** Добавлен редирект с HTTP на HTTPS (301) и HTTPS-блок на порту 443 с TLS 1.2/1.3. Добавлен заголовок `Strict-Transport-Security`. Сертификаты ожидаются по пути Let's Encrypt: `/etc/letsencrypt/live/ktcards.ru/`.

---

### ~~10. Нет `proxy_set_header Host` в `location /api`~~ ✅ ИСПРАВЛЕНО
- **Файл:** `ktcards.client/nginx.conf`
- **Проблема:** В блоке `location /api` не передаётся заголовок `Host`. ASP.NET Core получает имя хоста nginx (`back_ktcards`), а не оригинальный `Host` клиента. Это может влиять на формирование абсолютных URL, логирование и заголовок `Forwarded`.
- **Решение:** Добавить `proxy_set_header Host $host;` в секцию `location /api`.
- **Статус:** `proxy_set_header Host $host;` добавлен в блок `location /api`.

---

## 🟢 НИЗКИЕ / ТЕХНИЧЕСКИЙ ДОЛГ

### 11. Антипаттерн установки зависимостей в `Dockerfile` (frontend)
- **Файл:** `ktcards.client/Dockerfile`
- **Проблема:** Последовательность `npm ci --force` → `rm -rf node_modules package-lock.json` → `npm cache clean --force` → `npm install --force` нарушает воспроизводимость сборки. `npm ci` предназначен именно для воспроизводимых установок по `package-lock.json`; последующий `npm install` может поставить другие версии пакетов. Флаг `--force` скрывает конфликты зависимостей.
- **Решение:** Заменить весь блок на одну команду `RUN npm ci`. Починить конфликты зависимостей, из-за которых был добавлен `--force`.

---

### 12. Двойной `COPY` контекста в `Dockerfile` (backend)
- **Файл:** `ktcards.Server/Dockerfile`
- **Проблема:** Стадия `build` содержит `COPY . ktcards.Server/`, а затем `COPY . .` — файлы копируются дважды. Это раздувает Docker-слои и может приводить к непредсказуемому результату при конфликтах путей.
- **Решение:** Оставить один корректный `COPY`. Исправить структуру Dockerfile для правильного контекста сборки.

---

### 13. `AdminTokenService` хранит токены только в памяти
- **Файл:** `ktcards.Server/Helpers/AdminTokenService.cs`
- **Проблема:** При перезапуске контейнера все активные сессии сбрасываются. При горизонтальном масштабировании (несколько инстансов) токен, выданный одним инстансом, не признаётся другим.
- **Решение:** Сохранять токены в Redis или в таблице БД. Это также даст возможность аудита активных сессий.

---

### 14. Кастомный `AdminAuthorizeAttribute` реализует `IActionFilter` вместо `IAuthorizationFilter`
- **Файл:** `ktcards.Server/Filters/AdminAuthorizeAttribute.cs`
- **Проблема:** Авторизационная логика реализована через `IActionFilter`, который запускается **после** model binding. Это нарушает принцип defence-in-depth: `IAuthorizationFilter` вызывается раньше в pipeline и является семантически правильным местом для проверки прав.
- **Решение:** Переключить на `IAuthorizationFilter` или использовать стандартный механизм авторизации ASP.NET Core (`IAuthorizationHandler` + `[Authorize]`).

---

## Сводная таблица приоритетов

| # | Уязвимость | Критичность | Сложность фикса | Статус |
|---|-----------|-------------|-----------------|--------|
| 1 | XSS через SVG-логотип | 🔴 Критическая | Низкая | ✅ |
| 2 | Обход rate limiting (XFF спуфинг) | 🔴 Критическая | Низкая | ✅ |
| 3 | `.env` не в `.gitignore` | 🟠 Высокая | Минимальная | ✅ |
| 4 | Нет Content-Security-Policy | 🟠 Высокая | Низкая | ✅ |
| 5 | Rate limit слишком мягкий (30/мин) | 🟠 Высокая | Минимальная | ✅ |
| 6 | Нет таймаута у HttpClient | 🟠 Высокая | Низкая | ✅ |
| 7 | Race condition при импорте карточек | 🟡 Средняя | Средняя | ✅ |
| 8 | Нет CSRF-защиты | 🟡 Средняя | Средняя | ✅ |
| 9 | HTTP без HTTPS / нет TLS | 🟡 Средняя | Средняя | ✅ |
| 10 | Нет `proxy_set_header Host` | 🟡 Средняя | Минимальная | ✅ |
| 11 | Dockerfile frontend антипаттерн | 🟢 Низкая | Низкая | |
| 12 | Dockerfile backend двойной COPY | 🟢 Низкая | Низкая | |
| 13 | AdminTokenService в памяти | 🟢 Низкая | Высокая | |
| 14 | AdminAuthorizeAttribute — IActionFilter | 🟢 Низкая | Низкая | |
