# 02 · Покрокова інструкція — створення звіту для нового партнера

Ця інструкція **універсальна**: будь-який бренд (Beer Market, Pyvna Boroda, Rukavychka, ваш новий) робиться однаково. Якщо хочеш одразу побачити приклад — дивись [`03-beer-market-demo-prompt.md`](./03-beer-market-demo-prompt.md).

> **TL;DR**: Cursor → відкрий чат → встав готовий промт-скрипт → агент сам зробить все за 15–20 хв. Нижче — деталі для розуміння, що саме там відбувається.

## Передумови

✅ Виконав [`01-cursor-setup.md`](./01-cursor-setup.md) — Cursor, плагіни, токен, GitHub.

## Крок 1 · Знайти `group_name` партнера в Databricks

Звіти будуються по полю `dim_provider_v2.group_name`. У партнера може бути назва на латиниці, кирилиці, з пробілами або без.

**У Cursor чаті** (з увімкненим Databricks plugin):

```
Знайди в hive_metastore.ng_delivery_spark.dim_provider_v2 для country_code='ua'
всі унікальні group_name, що містять "<назва партнера>" (case-insensitive).
Покажи provider_name і group_name.
```

Агент виконає:

```sql
SELECT DISTINCT group_name, COUNT(*) AS stores
FROM hive_metastore.ng_delivery_spark.dim_provider_v2
WHERE country_code = 'ua'
  AND LOWER(group_name) LIKE '%<назва>%'
GROUP BY group_name
ORDER BY stores DESC
LIMIT 50;
```

Запиши **точне** значення `group_name` — воно йде в `PARTNER_NAME` у скрипті. Приклад: `HOP HEY`, `LOKO`, `BEER MARKET`.

## Крок 2 · Вибрати шаблон звіту

Дивись таблицю в [README](./README.md#вибір-шаблону-звіту):

- **Простий (Hop Hey)** — Monthly + Weekly tabs. Файли в [`templates/`](./templates/).
- **Повний (LOKO MBR)** — додатково Stores + Failed orders + Customer feedback. Зразок у `Reports/LOKO/MBR/`.

> Якщо вагаєшся — починай з простого. Завжди можна потім сказати агенту: «Додай вкладку Stores у звіт <партнер>».

## Крок 3 · Створити локальну папку партнера

```bash
cd "/Users/<you>/Library/CloudStorage/Google Drive Desktop/My Drive/Cursor folder"
mkdir -p "Reports/<Partner>"
cd "Reports/<Partner>"
```

Назва папки — зрозуміла людині (`Beer Market`, `Pyvna Boroda`). Може бути з пробілами.

## Крок 4 · Скопіювати скелети з templates/

З цього репо `docs/templates/` копіюй у нову папку:

| Файл | Куди | Що поправити |
|------|------|--------------|
| `generate_report.py` | `Reports/<Partner>/` | Замінити `<PARTNER_NAME>` на точне значення з кроку 1 |
| `template.html` | `Reports/<Partner>/` | Замінити `<PARTNER_DISPLAY>` на красиву назву (для заголовка), `<INITIALS>` на ініціали (наприклад, `BM`) |
| `publish.sh` | `Reports/<Partner>/` | Замінити `<PUBLIC_REPO>` на `<partner-slug>-report` |
| `.env.example` | `Reports/<Partner>/.env` | Підставити справжній PAT |
| `.gitignore` | `Reports/<Partner>/` | Без змін |
| `requirements.txt` | `Reports/<Partner>/` | Без змін |
| `github-workflow.yml` | `Reports/<Partner>/.github/workflows/update-report.yml` | Без змін |
| `cursor-rule.mdc` | `.cursor/rules/<partner>-report.mdc` | Замінити `<PARTNER>` і `<PUBLIC_REPO>` |

> Усе це робить агент автоматично, якщо ти вказуєш йому промт зі змінними. Не треба руками — дивись крок 8.

## Крок 5 · Створити публічний репо для GitHub Pages

```bash
gh repo create mykhailobrynchak-dev/<partner-slug>-report --public \
  --description "Звіт <Partner Display> — Bolt Food UA" \
  --homepage "https://mykhailobrynchak-dev.github.io/<partner-slug>-report/"
```

Після створення:

1. Відкрий `https://github.com/mykhailobrynchak-dev/<partner-slug>-report/settings/pages`
2. **Source: Deploy from a branch**, **Branch: main**, **/ (root)** → Save
3. Через 1–2 хв за посиланням `https://mykhailobrynchak-dev.github.io/<partner-slug>-report/` буде сторінка-заглушка (404 поки що).

## Крок 6 · Додати GitHub Secrets для автоматичного оновлення

У публічному репо (`<partner-slug>-report`):

```bash
gh secret set DATABRICKS_HOST --body "bolt-common.cloud.databricks.com" \
  --repo mykhailobrynchak-dev/<partner-slug>-report
gh secret set DATABRICKS_WAREHOUSE_ID --body "b39957853740b21d" \
  --repo mykhailobrynchak-dev/<partner-slug>-report
gh secret set DATABRICKS_TOKEN --body "<твій dapi токен>" \
  --repo mykhailobrynchak-dev/<partner-slug>-report
```

Після цього в репо буде workflow `Оновлення звіту` (з `templates/github-workflow.yml`). Кожен понеділок 05:00 UTC він сам перегенерує звіт.

## Крок 7 · Першу генерацію — локально

```bash
cd "Reports/<Partner>"
chmod +x publish.sh
./publish.sh
```

Що відбувається:

1. `pip install -r requirements.txt` — підставляє `databricks-sql-connector`.
2. `python3 generate_report.py` — тягне дані з Databricks → пише `index.html` локально.
3. `git clone <partner>-report` у тимчасову папку, копіює туди `index.html`, комітить, пушить.
4. Через 30–60 секунд звіт живий за GitHub Pages URL.

Перевір: відкрий `https://mykhailobrynchak-dev.github.io/<partner-slug>-report/` → `Cmd+Shift+R` (hard refresh, бо CDN).

## Крок 8 · Делегувати все це агенту в Cursor

Замість всіх кроків 3–7 — **відкрий Cursor**, потім чат (`Cmd+L`) і встав один промт:

```
Створи звіт для партнера <Назва партнера> на базі Hop Hey.

Group_name у Databricks: <точне значення>.
Slug для публічного репо: <partner-slug>.
Display name: <Красива назва>.
Initials: <BM>.

Шаблони — у docs/templates/ репо Stores-internal-weekly-report.

Виконай:
1. Створи папку Reports/<Назва>/
2. Скопіюй усі шаблони, замінивши плейсхолдери
3. Створи .env з токеном з .env моєї поточної робочої папки (Reports/LOKO/MBR/.env)
4. Створи публічний репо <partner-slug>-report (gh repo create)
5. Налаштуй GitHub Pages (через gh API)
6. Додай 3 секрети (DATABRICKS_*) у новий репо
7. Запусти ./publish.sh
8. Поверни мені посилання на live звіт
```

Готовий, заповнений промт для прикладу — дивись [`03-beer-market-demo-prompt.md`](./03-beer-market-demo-prompt.md).

## Крок 9 · Передати посилання партнеру

Після успішного `publish.sh`:

```
https://mykhailobrynchak-dev.github.io/<partner-slug>-report/
```

Це посилання:
- Постійне (не змінюється з оновленнями)
- Без авторизації (публічне)
- Оновлюється автоматично щопонеділка
- Містить **тільки** ті дані, що ти показав партнеру

> **Перед відправкою партнеру** — обов'язково сам відкрий сторінку, перевір цифри, переконайся, що нема нічого зайвого (debug-логів, посилань на внутрішні системи).

## Що далі

- **Партнер просить нову метрику** → у Cursor чаті: `Додай у звіт <Partner> метрику <X> у вкладку <Y>` — агент знайде колонку, оновить SQL і шаблон.
- **Партнер хоче drill-down по магазинах** → `Перетвори звіт <Partner> у формат LOKO MBR з вкладкою Stores`.
- **Партнер хоче відгуки клієнтів** → `Додай вкладку Customer Feedback як у LOKO MBR`.
- **Звіт зламався після оновлення** → дивись [`04-troubleshooting.md`](./04-troubleshooting.md).

## Чек-лист готовності звіту (перед відправкою партнеру)

- [ ] `index.html` відкривається без 404
- [ ] Всі вкладки працюють (натиснути по черзі)
- [ ] Цифри **НЕ** включають канцеловані замовлення (звір з власним SQL з `order_state='delivered'`)
- [ ] Шапка має правильну назву партнера і кольори Bolt
- [ ] Дата генерації внизу — свіжа (не старша за 7 днів)
- [ ] Графіки рендеряться (Chart.js завантажився з CDN)
- [ ] Mobile view ОК (Chrome DevTools → Device toolbar → iPhone 13)
- [ ] GitHub Actions workflow `Run workflow` виконується успішно (тестовий ручний запуск)
- [ ] У Slack команди залишив пост: «Запустив звіт для <Partner>: <URL>»
