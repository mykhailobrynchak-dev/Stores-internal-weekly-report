# 01 · Налаштування Cursor — чек-лист (один раз)

Поки всі пункти не зроблені — **агент не зможе створити автоматичний звіт**. Це разовий setup, далі тільки використовуєш.

> Орієнтовно — 30 хвилин першого разу. Більшість пунктів — встановити-один-раз-і-забути.

## 0. Базові вимоги до Mac

- [ ] **macOS** (Intel або Apple Silicon)
- [ ] **Cursor** (свіжа версія) — https://cursor.com/download
- [ ] **Python 3.11+** перевір: `python3 --version`. Якщо ні — `brew install python@3.11`
- [ ] **Homebrew** — `brew --version`. Якщо ні — `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
- [ ] **Git** — приходить разом з Xcode CLT: `xcode-select --install`
- [ ] **GitHub CLI** — `brew install gh`, потім `gh auth login` (вибрати GitHub.com → HTTPS → авторизація через браузер)

## 1. Cursor — доступи та плагіни

### 1.1 Логін у Cursor
- [ ] Авторизований під робочим Bolt-акаунтом (Settings → Account)
- [ ] Активна Pro/Business підписка (інакше Claude / GPT-5 не дадуть стабільно працювати з великими файлами звіту)

### 1.2 Обов'язкові плагіни (Cursor → Settings → MCP / Plugins)

| Плагін | Що дає | Обов'язково? |
|--------|--------|--------------|
| **Databricks** (`Databricks` plugin) | Прямий доступ до SQL Warehouse, browse каталогів і таблиць, виконання запитів з чату | **Так** |
| **GitHub** (`user-github` MCP) | Створення / push / clone репо, керування Actions і секретами через чат | **Так** |
| **Atlassian** (Confluence + Jira) | Якщо документація команди в Confluence — корисно агенту для контексту | Бажано |
| **Slack** (`user-slack` MCP) | Постити сповіщення в канал коли звіт оновлено (опційно) | Опційно |
| **Firecrawl** | Скрейпити публічні сторінки партнера (опис, локації) для контексту | Опційно |

**Як додати плагін:** Cursor → `Cmd+Shift+P` → `MCP: Manage Servers` → `Add` → вибрати з маркетплейсу або вставити свій URL.

### 1.3 Skills (готові інструкції для агента)

Skills — це готові «навички» для агента: коли ти кажеш «Створи Databricks-додаток», агент сам читає інструкцію зі skill і не вигадує велосипед.

Команда вже використовує:

- [ ] **`databricks-core`** — CLI, profiles, exploration (входить у Databricks plugin)
- [ ] **`databricks-apps`** — для дашбордів і додатків на Databricks Apps
- [ ] **`databricks-jobs`** — для Lakeflow Jobs
- [ ] **`databricks-pipelines`** — для DLT
- [ ] **`databricks-dabs`** — для Asset Bundles

Усі вони ставляться разом з Databricks plugin. Перевір: Cursor Settings → Skills → має бути секція Databricks.

### 1.4 Cursor Rules (поведінка агента в цьому проєкті)

У робочій папці `Cursor folder/` має бути файл `.cursor/rules/` з правилами. Найважливіші:

```
.cursor/rules/
├── databricks-defaults.mdc       ← завжди order_state='delivered', LIMIT, partition column
├── reports-bolt-colors.mdc       ← кольори Bolt у HTML (#34D186, #1A1A2E, #F8F9FA)
└── partner-report.mdc            ← після правок — ./publish.sh, не вимагати Run workflow
```

Шаблон `partner-report.mdc` — у [`templates/cursor-rule.mdc`](./templates/cursor-rule.mdc). Скопіюй у `.cursor/rules/` коли створюєш новий звіт партнера.

### 1.5 User Rules (твої постійні налаштування)

Cursor → Settings → Rules → User Rules. Додай **обов'язково** такі (вони вже в команди стандартні):

```
При запитах до Databricks завжди фільтруй order_state = 'delivered'
Використовуй партиційну колонку order_created_date у WHERE
Завжди додавай LIMIT до SQL-запитів, якщо я не вказав інакше
При створенні HTML-звітів використовуй кольори Bolt: primary #34D186, dark #1A1A2E, background #F8F9FA
```

Це гарантує, що агент:
1. Не покаже партнеру хибні цифри з канселів і повернень.
2. Не з'їсть Databricks-квоту повним скан-фуллом таблиці.
3. Робить звіти у фірмовому стилі.

## 2. Databricks — токен і доступи

### 2.1 Personal Access Token (PAT)
- [ ] Зайти в Databricks UI: https://bolt-common.cloud.databricks.com
- [ ] **User Settings → Developer → Access tokens → Generate new token**
- [ ] Lifetime: 90 днів (максимум, потім перегенерувати)
- [ ] Скопіювати рядок `dapi...` — побачиш його **один раз**

> **Безпека:** PAT — це твій логін до всіх таблиць команди. Не зберігай у месенджерах, не комітити в git. Тримати лише в `.env` файлі (він у `.gitignore`).

### 2.2 SQL Warehouse ID
Стандартний для команди — `b39957853740b21d`. Перевірити: Databricks UI → SQL Warehouses → знайти ваш warehouse → Connection details → Path-частина `…/warehouses/<ID>`.

### 2.3 Перевірка з'єднання
```bash
pip3 install databricks-sql-connector
python3 -c "
from databricks import sql
import os
conn = sql.connect(
  server_hostname='bolt-common.cloud.databricks.com',
  http_path='/sql/1.0/warehouses/b39957853740b21d',
  access_token='<твій dapi токен>',
)
c = conn.cursor()
c.execute('SELECT current_user()')
print(c.fetchone())
"
```
Має надрукувати твій email. Якщо `CERTIFICATE_VERIFY_FAILED` — VPN/проксі заважає, додай `_tls_no_verify=True` в `connect(...)`.

## 3. GitHub — доступ і права

### 3.1 SSH-ключ (рекомендовано) або gh-credentials
- [ ] `gh auth status` має показати, що ти авторизований
- [ ] Можеш клонувати приватні репо: `git clone https://github.com/mykhailobrynchak-dev/<repo>.git` без запиту пароля

### 3.2 Права на створення репо
- [ ] Маєш доступ до org `mykhailobrynchak-dev` (або своєї робочої org) — можеш створювати публічні репо звітів партнерів

### 3.3 GitHub Personal Access Token (для Actions)
Якщо плануєш, що **GitHub Actions** з одного приватного репо пушить в інший публічний — потрібен `DEPLOY_TOKEN` (PAT з scope `repo`):
- [ ] GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token
- [ ] Scope: `repo` (повний)
- [ ] Зберегти у GitHub Secrets приватного репо як `DEPLOY_TOKEN`

## 4. Структура локальних папок

У робочій папці `Cursor folder/` має бути:

```
Cursor folder/
├── .cursor/rules/              ← правила агента
├── Reports/
│   ├── <Partner1>/             ← робоча папка партнера
│   │   ├── generate_report.py
│   │   ├── template.html
│   │   ├── publish.sh
│   │   ├── .env                ← НЕ в git
│   │   └── .gitignore
│   └── <Partner2>/
└── ...
```

Коли створюєш новий звіт партнера, агент створює нову підпапку в `Reports/<Партнер>/`.

## 5. Перевірка, що все готово

Прогени по чек-листу — нижче має бути все «так»:

- [ ] `python3 --version` → 3.11+
- [ ] `gh auth status` → logged in
- [ ] `gh repo view mykhailobrynchak-dev/Stores-internal-weekly-report` → видно репо
- [ ] У Cursor → Settings → MCP → Databricks `Connected`
- [ ] У `.cursor/rules/` є хоча б `databricks-defaults.mdc`
- [ ] У User Rules є 4 правила вище (Bolt кольори, `order_state`, partition, LIMIT)
- [ ] Pythoн-перевірка з'єднання з Databricks (п. 2.3) пройшла

Все ✓ — переходь до [`02-partner-report-guide.md`](./02-partner-report-guide.md).

## 6. Корисні shortcuts у Cursor

| Дія | Shortcut |
|-----|----------|
| Відкрити чат з агентом | `Cmd+L` |
| Згадати файл / папку в чаті | `@` + назва |
| Запустити команду в палітрі | `Cmd+Shift+P` |
| Прийняти всі правки агента | `Cmd+Enter` (у diff) |
| Відхилити правку | `Cmd+Backspace` |
| Перевести агента в **Plan mode** перед великим змінам | `Cmd+Shift+L` → Plan |

## 7. Що робити, якщо плагін Databricks не з'являється

1. Cursor → Settings → MCP → перевір, чи увімкнений
2. Перезавантаж Cursor
3. Перевір, що `databricks` CLI встановлений: `brew install databricks-cli`
4. Авторизуй CLI: `databricks auth login --host bolt-common.cloud.databricks.com`
5. Якщо нічого не допомагає — пиши у Slack-канал #cursor-help (або як у тебе він зветься)
