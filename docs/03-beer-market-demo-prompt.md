# 03 · Beer Market — готовий промт для демо

Це текст, який копіюєш у Cursor чат (`Cmd+L`) і відправляєш агенту. Все, що йому потрібно для створення повноцінного звіту Beer Market — у цьому промті.

> Перед запуском перевір: ✅ зробив [`01-cursor-setup.md`](./01-cursor-setup.md), ✅ Databricks plugin підключений, ✅ `gh auth status` → logged in.

## Як використати під час демо колегам

1. Відкрий Cursor у робочій папці `Cursor folder/`.
2. `Cmd+L` — новий чат.
3. **Скопіюй блок нижче повністю** і встав у чат.
4. Натисни Enter. Спостерігай разом з колегами.
5. Орієнтовний час виконання — **15–20 хвилин**:
   - 1 хв — створення папок і файлів
   - 5–10 хв — Databricks queries (4 запити по фінансах + операціях)
   - 1 хв — генерація HTML
   - 1 хв — створення публічного репо і налаштування Pages
   - 1 хв — `git push` і чекання GitHub Pages CDN

---

## Промт (копіювати все, що між горизонтальними лініями)

---

```
Створи новий звіт для партнера Beer Market — за зразком Hop Hey
(/Users/<user>/Library/CloudStorage/Google Drive Desktop/My Drive/Cursor folder/Reports/Hop Hey/).

# Параметри партнера
- Робоча назва: Beer Market
- Display name (заголовок звіту): BEER MARKET
- Initials для логотипу: BM
- Slug для публічного репо і Pages: beer-market-report
- Group name у Databricks (hive_metastore.ng_delivery_spark.dim_provider_v2.group_name):
  ПЕРЕД СТВОРЕННЯМ — підтверди точне значення запитом:
  SELECT DISTINCT group_name, COUNT(*) AS stores
  FROM hive_metastore.ng_delivery_spark.dim_provider_v2
  WHERE country_code='ua' AND LOWER(group_name) LIKE '%beer%'
  GROUP BY group_name ORDER BY stores DESC LIMIT 20;
  → У промт використай те, де stores найбільше і назва містить "BEER MARKET".

# Що робити (по порядку)

## 1. Створи структуру локально
mkdir -p "Reports/Beer Market"
cd "Reports/Beer Market"

Скопіюй з docs/templates/ цього самого workspace такі файли і заміни плейсхолдери:

| Шаблон | Куди | Що замінити |
|--------|------|-------------|
| docs/templates/generate_report.py | Reports/Beer Market/generate_report.py | <PARTNER_NAME> → точний group_name з Databricks |
| docs/templates/template.html      | Reports/Beer Market/template.html      | <PARTNER_DISPLAY> → BEER MARKET; <INITIALS> → BM; <PAGE_TITLE> → BEER MARKET — Бізнес-огляд Bolt Food |
| docs/templates/publish.sh         | Reports/Beer Market/publish.sh         | <PUBLIC_REPO> → beer-market-report; <PARTNER_DISPLAY> → BEER MARKET |
| docs/templates/.env.example       | Reports/Beer Market/.env (НЕ commit)   | DATABRICKS_TOKEN — візьми з існуючого Reports/LOKO/MBR/.env |
| docs/templates/.gitignore         | Reports/Beer Market/.gitignore         | без змін |
| docs/templates/requirements.txt   | Reports/Beer Market/requirements.txt   | без змін |
| docs/templates/github-workflow.yml | Reports/Beer Market/.github/workflows/update-report.yml | <PARTNER_DISPLAY> → BEER MARKET |

Cursor rule:
| docs/templates/cursor-rule.mdc | .cursor/rules/beer-market-report.mdc | <PARTNER> → Beer Market; <PUBLIC_REPO> → beer-market-report |

chmod +x publish.sh

## 2. Створи публічний репо та налаштуй GitHub Pages

gh repo create mykhailobrynchak-dev/beer-market-report --public \
  --description "Звіт BEER MARKET — Bolt Food UA" \
  --homepage "https://mykhailobrynchak-dev.github.io/beer-market-report/"

Після створення:
- Через gh API увімкни GitHub Pages з main / root:
  gh api -X POST /repos/mykhailobrynchak-dev/beer-market-report/pages \
    -f "source[branch]=main" -f "source[path]=/"
- Додай README.md з рядком: "# BEER MARKET — Bolt Food UA\n\nЗвіт: https://mykhailobrynchak-dev.github.io/beer-market-report/"
- Додай у новостворений публічний репо .github/workflows/update-report.yml (копія з шаблона).

## 3. Додай GitHub Secrets у новий репо

Зчитай DATABRICKS_TOKEN з Reports/LOKO/MBR/.env (поле DATABRICKS_TOKEN).

gh secret set DATABRICKS_HOST --body "bolt-common.cloud.databricks.com" \
  --repo mykhailobrynchak-dev/beer-market-report
gh secret set DATABRICKS_WAREHOUSE_ID --body "b39957853740b21d" \
  --repo mykhailobrynchak-dev/beer-market-report
gh secret set DATABRICKS_TOKEN --body "<токен>" \
  --repo mykhailobrynchak-dev/beer-market-report

## 4. Згенеруй і запушь звіт

cd "Reports/Beer Market"
./publish.sh

Скрипт:
- pip install -r requirements.txt
- python3 generate_report.py (тягне дані з Databricks, пише index.html)
- клонує beer-market-report у tmp, копіює index.html, commit + push

## 5. Перевір

Відкрий https://mykhailobrynchak-dev.github.io/beer-market-report/ через ~30 сек (Cmd+Shift+R).
Якщо 404 — почекай ще хвилину (Pages CDN), або перевір Settings → Pages у репо.

## 6. У фінальній відповіді мені поверни

- Точний group_name партнера, який ти знайшов
- Кількість магазинів Beer Market у мережі (з того ж запиту)
- Посилання на публічний репо: https://github.com/mykhailobrynchak-dev/beer-market-report
- Посилання на live звіт: https://mykhailobrynchak-dev.github.io/beer-market-report/
- Кількість delivered orders за останній місяць (як sanity-check, що дані тягнуться)
- Скріншот або текстовий опис основних KPI (orders, GMV, AOV, active stores)

# Правила під час виконання
- НЕ комітити .env у git (перевір що в .gitignore)
- Усі SQL-запити — з order_state='delivered', WHERE order_created_date BETWEEN ... AND ..., LIMIT
- HTML кольори: --green:#34D186, --accent-dark:#1A1A2E, --bg:#F8F9FA
- Якщо publish.sh падає на SSL (CERTIFICATE_VERIFY_FAILED) — додай DATABRICKS_TLS_NO_VERIFY=1 у .env
- Якщо щось не зрозуміло — задай уточнююче питання, не вигадуй
```

---

## Що робити, якщо агент щось не доробив

Якщо агент зупинився — попроси продовжити з конкретного кроку:

```
Перевір, що зробив, з чек-листа:
1. Папка Reports/Beer Market створена і всі файли всередині? Покажи `ls -la`.
2. .env з токеном існує і не закомічений?
3. Публічний репо beer-market-report створений і Pages увімкнено?
4. Секрети додані (gh secret list --repo)?
5. publish.sh виконався без помилок?
6. URL https://mykhailobrynchak-dev.github.io/beer-market-report/ повертає не 404?

Зроби те, що залишилось.
```

## Якщо агент попросив підтвердження на видалення/перезапис

Перевір **точно** що агент хоче зробити перед `Y`. Особливо коли йде операція на існуючий репо `Reports/LOKO/MBR/` — там працюючий звіт LOKO, його **НЕ ЧІПАТИ**.

## Демо-сценарій для колег (10 хв розмови)

1. **0–2 хв**. Показуєш `Reports/Hop Hey/` і живий Hop Hey звіт у браузері. Пояснюєш, що це публічна сторінка, що оновлюється сама.
2. **2–4 хв**. Показуєш `Reports/LOKO/MBR/` — складніший приклад з 4 вкладками. Показуєш `publish.sh` і пояснюєш потік.
3. **4–6 хв**. Перемикаєшся в Cursor, показуєш `.cursor/rules/`, `User Rules`, плагіни (Databricks, GitHub).
4. **6 хв**. Відкриваєш чат `Cmd+L`, показуєш `docs/03-beer-market-demo-prompt.md` у репо, копіюєш промт-блок.
5. **6–7 хв**. Вставляєш у чат, відправляєш.
6. **7–22 хв**. Поки агент працює — відповідаєш на питання колег. Періодично коментуєш, що зараз робить агент (можеш слідкувати в timeline).
7. **22–25 хв**. Відкриваєте разом готовий звіт `https://mykhailobrynchak-dev.github.io/beer-market-report/`. Показуєш, що він автооновиться у понеділок.
8. **25–30 хв**. Q&A. Передаєш їм лінк на цей репо `Stores-internal-weekly-report/docs/`.
