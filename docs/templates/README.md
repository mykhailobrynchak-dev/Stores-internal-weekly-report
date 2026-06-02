# Templates — скелети файлів для нового звіту партнера

Усі файли в цій папці — **шаблони** з плейсхолдерами `{{...}}`. Агент копіює їх у нову папку партнера і замінює плейсхолдери на справжні значення.

## Список файлів

| Файл | Куди копіювати | Плейсхолдери для заміни |
|------|----------------|--------------------------|
| `generate_report.py` | `Reports/<Partner>/generate_report.py` | `{{PARTNER_NAME}}`, `{{PARTNER_DISPLAY}}`, `{{DATA_START}}` |
| `template.html` | `Reports/<Partner>/template.html` | `{{PARTNER_DISPLAY}}`, `{{INITIALS}}` |
| `publish.sh` | `Reports/<Partner>/publish.sh` (chmod +x) | `{{PARTNER_DISPLAY}}`, `{{PUBLIC_REPO}}` |
| `.env.example` | `Reports/<Partner>/.env` (зі справжнім токеном, НЕ commit) | `your_databricks_pat_here` → реальний `dapi...` |
| `.gitignore` | `Reports/<Partner>/.gitignore` | без змін |
| `requirements.txt` | `Reports/<Partner>/requirements.txt` | без змін |
| `github-workflow.yml` | `Reports/<Partner>/.github/workflows/update-report.yml` **і** в публічний репо `<partner>-report/.github/workflows/update-report.yml` | `{{PARTNER_DISPLAY}}` |
| `cursor-rule.mdc` | `.cursor/rules/<partner-slug>-report.mdc` | `{{PARTNER}}`, `{{PUBLIC_REPO}}`, `{{PARTNER_DB_NAME}}` |

## Значення плейсхолдерів — приклад для Beer Market

| Плейсхолдер | Значення для Beer Market |
|--------------|--------------------------|
| `{{PARTNER_NAME}}` | `BEER MARKET` (точне з `dim_provider_v2.group_name`) |
| `{{PARTNER_DISPLAY}}` | `BEER MARKET` |
| `{{PARTNER_DB_NAME}}` | `BEER MARKET` (так само) |
| `{{INITIALS}}` | `BM` |
| `{{PUBLIC_REPO}}` | `beer-market-report` |
| `{{DATA_START}}` | `2025-12-01` (або перший місяць активності партнера) |
| `{{PARTNER}}` | `Beer Market` (для назв папок і людських посилань) |

## Як замінювати плейсхолдери

### Bash one-liner (всередині папки нового партнера)
```bash
cd "Reports/Beer Market"
sed -i '' \
  -e 's|{{PARTNER_NAME}}|BEER MARKET|g' \
  -e 's|{{PARTNER_DISPLAY}}|BEER MARKET|g' \
  -e 's|{{PARTNER_DB_NAME}}|BEER MARKET|g' \
  -e 's|{{INITIALS}}|BM|g' \
  -e 's|{{PUBLIC_REPO}}|beer-market-report|g' \
  -e 's|{{DATA_START}}|2025-12-01|g' \
  -e 's|{{PARTNER}}|Beer Market|g' \
  generate_report.py template.html publish.sh \
  .github/workflows/update-report.yml \
  ../../.cursor/rules/beer-market-report.mdc
```

> На macOS (BSD sed) — обов'язково `sed -i ''` з порожнім рядком після `-i`.

### Або просто скажи агенту
```
Скопіюй усі файли з docs/templates/ у Reports/Beer Market/, заміни плейсхолдери:
PARTNER_NAME=BEER MARKET, PARTNER_DISPLAY=BEER MARKET, INITIALS=BM,
PUBLIC_REPO=beer-market-report, DATA_START=2025-12-01.
```

## Що робить кожен файл (одним рядком)

- **`generate_report.py`** — Python script. Підключається до Databricks, виконує ~10 SQL запитів, складає `report_data.json` і інжектить його в `template.html` → виходить `index.html`.
- **`template.html`** — порожній HTML з вкладками Monthly/Weekly. На рендерингу JavaScript бере дані з `REPORT_DATA` і малює всі таблиці/графіки.
- **`publish.sh`** — bash, що в одну команду: тягне дані → пере-генерує `index.html` → клонує публічний репо → копіює туди файл → push.
- **`.env`** — секрети (DATABRICKS_TOKEN). Тільки локально.
- **`github-workflow.yml`** — те саме, що `publish.sh`, але автоматично щопонеділка.
- **`cursor-rule.mdc`** — інструкція для агента: «після правок звіту — обов'язково `./publish.sh`».

## Перевірка коректності після заміни

```bash
grep -r '{{' Reports/<Partner>/  # Має бути порожньо
```

Якщо знаходить хоч один `{{...}}` — значить плейсхолдер не замінили, скрипт впаде.
