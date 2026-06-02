# 04 · Troubleshooting — типові проблеми

Коли щось пішло не так — спочатку шукай тут. Більшість проблем — то або токен, або SSL, або права на push.

## Помилки під час `./publish.sh`

### `Missing DATABRICKS_HOST` / `Missing DATABRICKS_TOKEN`

**Причина:** немає файлу `.env` у папці звіту, або в ньому немає потрібного ключа.

**Рішення:**
```bash
cd Reports/<Partner>
cp .env.example .env
# відкрий .env, постав справжній DATABRICKS_TOKEN (рядок dapi...)
```

### `DATABRICKS_TOKEN у .env — заглушка з .env.example`

**Причина:** скопіював `.env.example` як `.env`, але **не замінив** `your_databricks_pat_here` на справжній токен.

**Рішення:**
1. Databricks UI → User Settings → Developer → Access tokens → Generate new token (Lifetime: 90 днів)
2. Скопіюй рядок `dapi...`
3. У `.env` замість `your_databricks_pat_here` встав свій токен (без лапок).

### `[SSL: CERTIFICATE_VERIFY_FAILED] self-signed certificate in certificate chain`

**Причина:** корпоративний VPN або Charles Proxy перехоплює SSL.

**Рішення (тільки на Mac, локально):**
```bash
echo "DATABRICKS_TLS_NO_VERIFY=1" >> .env
./publish.sh
```

> ⚠️ Цей флаг — лише для Mac. У GitHub Actions — НЕ ставити, там SSL працює нормально.

### `databricks.sql.exc.OperationalError: ... 401 Unauthorized`

**Причина:** токен прострочився (за замовчуванням 90 днів) або відкликаний.

**Рішення:** генеруй новий PAT (як у попередньому пункті) і онови `.env`. Не забудь оновити секрет `DATABRICKS_TOKEN` у GitHub репо звіту:

```bash
gh secret set DATABRICKS_TOKEN --body "<новий dapi токен>" \
  --repo mykhailobrynchak-dev/<partner-slug>-report
```

### `databricks.sql.exc.ServerOperationError: ... resource not available`

**Причина:** SQL Warehouse заснув (auto-stop) і не встиг запуститися за timeout.

**Рішення:** просто перезапусти `./publish.sh`. Або зайди у Databricks UI → SQL Warehouses → твій warehouse → Start.

### `Could not resolve host: github.com`

**Причина:** немає інтернету або DNS зламався.

**Рішення:** перевір з'єднання, перевір VPN.

### `! [rejected] main -> main (fetch first)`

**Причина:** хтось (або GitHub Actions) запушив у публічний репо швидше, ніж ти.

**Рішення:**
```bash
cd /tmp  # переходимо туди, де publish.sh клонував репо
# АБО просто перезапусти ./publish.sh — він робить fresh clone
./publish.sh
```

Якщо помилка повторюється — `git pull --rebase origin main` всередині DEPLOY_DIR, потім push.

### `Permission denied (publickey)` при `git clone` / `git push`

**Причина:** SSH-ключ або gh-credentials не налаштовані.

**Рішення:**
```bash
gh auth login
# вибрати GitHub.com → HTTPS → Login with a web browser
gh auth status
```

Якщо все одно фейлить — використовуй HTTPS-клон у `publish.sh` (так і є за замовчуванням), або згенеруй SSH-ключ за інструкцією: https://docs.github.com/en/authentication/connecting-to-github-with-ssh

## Помилки в GitHub Actions

### Workflow падає з `Missing DATABRICKS_TOKEN`

**Причина:** не додані секрети в репо.

**Рішення:**
```bash
gh secret list --repo mykhailobrynchak-dev/<partner-slug>-report
# Має бути 3 секрети: DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID
```

Якщо немає — додай (див. [`02-partner-report-guide.md`](./02-partner-report-guide.md), крок 6).

### Workflow падає з `git push origin main` — `Permission denied`

**Причина:** в `permissions:` у `update-report.yml` немає `contents: write`, або репо protected branch.

**Рішення:** перевір, що в workflow є:
```yaml
permissions:
  contents: write
```

Якщо є branch protection — або вимкни його для main, або додай `DEPLOY_TOKEN` (PAT з `repo` scope) і використай у `git push`.

### Workflow зеленый, але звіт не оновився

**Причина:** Pages CDN кешує. Refresh — `Cmd+Shift+R` (hard reload).

**Альтернатива:** перевір `https://github.com/mykhailobrynchak-dev/<repo>/actions/workflows/update-report.yml` → останній run → крок `Commit and push report` — там видно, чи був реальний commit.

## Помилки в браузері (Pages)

### 404 Not Found

**Причина:** GitHub Pages ще не активований у Settings, або щойно створили — ще не задеплоїлось.

**Рішення:**
1. `https://github.com/mykhailobrynchak-dev/<repo>/settings/pages`
2. **Source: Deploy from a branch**, **Branch: main**, **/ (root)** → Save
3. Почекай 1–2 хвилини, refresh.

### Звіт відкрився, але всі значення `null` / `NaN`

**Причина:** `report_data.json` порожній — Databricks повернув 0 рядків. Найчастіше — неправильний `PARTNER_NAME` (regєl-залежний).

**Рішення:**
1. Перевір через Databricks UI:
   ```sql
   SELECT COUNT(*) FROM hive_metastore.ng_delivery_spark.dim_provider_v2
   WHERE country_code='ua' AND group_name='<твоє значення>';
   ```
2. Якщо 0 — пошукай правильне значення (з `LIKE '%...%'` як у [`02-partner-report-guide.md`](./02-partner-report-guide.md), крок 1).
3. У `generate_report.py` `PARTNER_NAME = "..."` має бути **точно** як у БД.

### Графіки не рендеряться (порожні `<canvas>`)

**Причина:** Chart.js не завантажився з CDN (jsdelivr заблокований корпоративним firewall).

**Рішення:** заміни в `template.html`:
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
```
на UNPKG:
```html
<script src="https://unpkg.com/chart.js@4.4.4/dist/chart.umd.min.js"></script>
```

### Дані старі (більше тижня)

**Причина:** workflow не виконався (cron не спрацював, або помилка в Actions).

**Рішення:**
1. Зайди в `https://github.com/mykhailobrynchak-dev/<repo>/actions`
2. Перевір останній run → якщо червоний, відкрий, читай помилку.
3. Запусти вручну: Actions → Run workflow.
4. Або локально: `cd Reports/<Partner> && ./publish.sh`.

## Помилки агента в Cursor

### Агент каже «не маю доступу до Databricks»

**Причина:** не активований Databricks plugin у Cursor.

**Рішення:** Cursor → Settings → MCP / Plugins → Databricks → Connect. Перевір [`01-cursor-setup.md`](./01-cursor-setup.md), п. 1.2.

### Агент створив SQL без `LIMIT` і без `order_state='delivered'`

**Причина:** не активовані User Rules.

**Рішення:** Cursor → Settings → Rules → User Rules → додай 4 правила з [`01-cursor-setup.md`](./01-cursor-setup.md), п. 1.5.

### Агент використовує неправильні кольори в HTML

**Причина:** не активоване правило про Bolt-кольори.

**Рішення:** додай у User Rules:
```
При створенні HTML-звітів використовуй кольори Bolt: primary #34D186, dark #1A1A2E, background #F8F9FA
```

### Агент пушить у `Stores-internal-weekly-report`, а має — у партнерський репо

**Причина:** агент не зрозумів структуру (один репо для doc, другий — для звіту партнера).

**Рішення:** уточни в чаті:
> «Stores-internal-weekly-report — це лише методичка для команди. Звіт партнера завжди йде в окремий публічний репо `<partner>-report`. Не плутай.»

## Швидкий діагностичний скрипт

Збережи як `Reports/<Partner>/diagnose.sh`:

```bash
#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "── Файли ──"
ls -la
echo ""
echo "── .env ключі (без значень) ──"
grep -E '^[A-Z_]+=' .env | cut -d= -f1 || true
echo ""
echo "── git remote ──"
git -C ../../$(basename $(git -C "../$(basename $(pwd))-report" rev-parse --show-toplevel 2>/dev/null) 2>/dev/null) remote -v 2>/dev/null || echo "[не клон публічного репо в цій папці]"
echo ""
echo "── gh auth ──"
gh auth status 2>&1 | head -5
echo ""
echo "── Python deps ──"
python3 -c "import databricks.sql; print('databricks-sql-connector:', databricks.sql.__version__)" || echo "Не встановлено"
echo ""
echo "── Тест Databricks ──"
python3 -c "
import os
from databricks import sql
os.environ.setdefault('DATABRICKS_TLS_NO_VERIFY','')
exec(open('.env').read().replace('=','=\"').replace('\n','\"\n').replace('\"\"','\"').strip()) if False else None
" 2>&1 | head -10 || true
```

Або просто скажи агенту:
> «Перевір, що Reports/<Partner>/ готова до publish: чи є .env, чи є всі плейсхолдери замінені, чи Databricks відповідає, чи git push працює».
