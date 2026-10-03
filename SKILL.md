---
name: travel-search-ru
description: "Use while planning a trip when Russian-catalog search is needed: package tours, hotels, flights, trains, excursions, prices, and booking links. Trigger on Russian requests: «спланировать путешествие», «подобрать тур», «найти отель/авиабилеты/жд билеты/экскурсии», «маршрут с актуальными ценами». Not for general advice without live search."
compatibility: Requires Python 3.8+ and outbound HTTPS access to https://mcp.botclaw.ru/travel. Search criteria are sent to this read-only service; it does not book.
metadata:
  author: MissiaL
  version: "2.5.0"
  keywords: "travel,travel-planning,trip-planner,itinerary,flights,trains,rail,tours,hotels,excursions,activities,mcp,russia,turkey,egypt,путешествия,планирование путешествий,туры,авиабилеты,поезда,жд билеты,отели,экскурсии,booking"
  permissions: "outbound HTTPS only to https://mcp.botclaw.ru/travel; execute bundled scripts/travel_search.py"
---

# Travel Search

Search tours, hotels, flights, trains, and activities through a single MCP-backed CLI.

## CLI

```bash
python scripts/travel_search.py <command> --input '<JSON object>'
python scripts/travel_search.py describe <command>
python scripts/travel_search.py list-tools
```

Commands: `search-tours`, `cheapest-tours`, `search-hotels`, `get-tour-details`, `search-flights`, `flight-calendar`, `search-trains`, `search-activities`, `list-destinations`.

Parameters below and in [references/usage.md](references/usage.md) are current. Run `describe <command>` once per command when you need a field not documented here; never invent fields from memory.

## Examples

```bash
python scripts/travel_search.py search-tours --input '{"departure_city":"Москва","country":"Турция","date_from":"YYYY-MM-DD","date_to":"YYYY-MM-DD","nights_min":7,"nights_max":10,"adults":2,"meal":"AI"}'
python scripts/travel_search.py search-flights --input '{"origin":"MOW","destination":"AYT","depart_date":"YYYY-MM-DD","adults":1}'
python scripts/travel_search.py search-trains --input '{"origin":"Москва","destination":"Сочи","depart_date":"YYYY-MM-DD","sort":"price","limit":5}'
python scripts/travel_search.py search-activities --input '{"city":"Анталья","date_from":"YYYY-MM-DD","date_to":"YYYY-MM-DD","persons":2,"children_allowed":true,"sort":"recommended","limit":5}'
```

## Даты

`YYYY-MM-DD` в примерах — заполнитель. Сначала определите сегодняшнюю дату; если она неизвестна, выполните `date +%F`. Все даты передавайте в формате `YYYY-MM-DD` и не раньше сегодняшней, месяц для `flight-calendar` — в формате `YYYY-MM`. Если год не назван («15 сентября», «в мае»), имеется в виду ближайший такой день или месяц в будущем.

## Scope

- Use this skill as the search layer of travel planning. Build itineraries with general reasoning; use the skill to find package tours, hotel-only stays, flights, trains, activities, destination directories, prices, and booking links.
- Does **not** make bookings, store personal travel data, access email/calendar, or keep a long-term travel workspace.
- Exact geography stays fixed unless the user explicitly agrees to broaden it.

## Hard constraints

Treat these as non-negotiable filters — do not silently relax them:

- Geography (country, resort, city, hotel when named)
- Dates and night range
- Traveler composition (adults, children, infants)
- Budget when stated

If children are in the party and ages are unknown, **ask for ages** before presenting bookable family prices. Do not invent ages for pricing.

**Budget:** never auto-show offers that break a hard budget. Alternatives outside any hard constraint may appear only after **explicit user consent**, and only in a **separate labeled section**. Alternatives that satisfy every hard constraint (e.g. other hotels when the named ones do not fit) need no consent.

## When to use which command

| Need | Command |
|------|---------|
| Package tour (flight + hotel) | `search-tours` |
| Quick cheapest tours, Travelata only | `cheapest-tours` |
| Hotel only (no flight) | `search-hotels` |
| Fresh price/availability before booking a tour | `get-tour-details` |
| Flight options | `search-flights` |
| Flight price calendar / flexible dates | `flight-calendar` |
| Train schedule and indicative fares | `search-trains` |
| Excursions and activities | `search-activities` |
| Resolve destinations / directories | `list-destinations` |

## Activities

Если город экскурсий не найден, попробуйте ближайший крупный город или туристический центр. `search-activities` ищет по теме через `query` («сафари», «острова») и принимает необязательные `date_from` и `date_to` в формате `YYYY-MM-DD` (`date_from` ≤ `date_to`), `persons` от 1 до 100 и булево `children_allowed`. Сортировка: `recommended` (по умолчанию), `price`, `rating` или `reviews`. В каждой записи указан источник `provider`, единица цены `price_unit` (`per_person`, `per_group`, `per_ticket` или `unknown`) и понятный текст `price_text`. Сравнивайте цены только при одинаковом `price_unit`; сортировка `price` не смешивает разные единицы.

## Туры и отели

- `date_from`…`date_to` — окно дат вылета (для `search-hotels` — заезда) не длиннее 31 дня, то есть до календарного месяца.
- `list-destinations` с `{"country": "…"}` даёт точные названия для `resort`; `resorts_level_travel_only` — места, которые есть только у Level.Travel (по ним ищет только он).
- Всегда передавайте `nights_min` и `nights_max` явно (по умолчанию 7–10) и держите диапазон не шире 5 значений: Level.Travel ищет только `nights_min`…`nights_min`+4 (сервер сузит диапазон и добавит примечание), Travelata — весь диапазон. Для более широкого диапазона сделайте несколько поисков по очереди.
- Питание `meal` (в `cheapest-tours` — список `meals`) передавайте кодом: `RO` — без питания, `BB` — завтраки, `HB` — полупансион, `FB` — полный пансион, `AI` — всё включено, `UAI` — ультра всё включено.
- `search-hotels` тоже требует `departure_city`: передайте домашний город пользователя, а если он неизвестен — «Москва». Город влияет только на доступность предложений.
- В предложениях есть `beach_distance_m` и `beach_line` — данные источника; `null` значит «неизвестно», а не «близко». Рейтинг — по шкале 0–10.
- Выдача — по одному варианту на отель (самый дешёвый); `more_offers` — сколько ещё дат и вариантов у отеля.
- `cheapest-tours` — быстрый обзор самых дешёвых туров только из Travelata; для выбранного предложения вызовите `get-tour-details` с его `offer_id`.

## Авиабилеты

- `search-flights`: `return_date` (`YYYY-MM-DD`) необязателен. Поездку туда-обратно длиннее 30 дней сервер ищет как два перелёта в одну сторону: у элементов есть `leg` (`outbound` или `return`), итоговая цена — их сумма. Поиск в одну сторону возвращает самый дешёвый вариант на каждую дату — часто это один результат. Цены всегда для эконом-класса, даже если `trip_class` ≠ 0.
- Цены авиабилетов — за одного взрослого; `price_total_adults` — сумма за взрослых. Детские тарифы источник не даёт — так и скажите. `one_way_combo` — два билета в одну сторону, когда они дешевле туда-обратно. Время в `departure_at` местное: вылет в 00:55 — это ночь накануне.
- Пустой ответ авиапоиска значит «нет в кэше цен», а не «нет рейсов»: проверьте соседние даты в `flight-calendar` и дайте ссылку.
- `flight-calendar`: `month` в формате `YYYY-MM`; цены — за билет в одну сторону.

## Ошибки

При ошибке CLI завершается с кодом 1 и печатает `{"error":true,"category":…,"message":…}`; для `tool_error` в `message` — текст сервера.

- Сообщение о неверных данных — исправьте ввод и не повторяйте запрос без изменений.
- «Источник отклонил параметры запроса…» — измените параметры.
- «Источник временно недоступен…» (ошибка всего вызова) — повторите один раз чуть позже, затем сообщите пользователю.
- «Сервис поиска сейчас перегружен…», «Слишком много запросов…» или `rate_limited` — подождите около минуты.
- Не запускайте второй `search-tours`, пока не завершился первый, и не повторяйте его с теми же аргументами. Если результатов мало, расширяйте поиск в рамках жёстких ограничений или с согласия пользователя.

## Workflow

1. Clarify hard constraints: place, dates/nights, travelers, budget, and every must-have condition (meal, stars, distance to the beach).
2. Translate each constraint into a parameter literally — never leave a must-have only in your head:
   - Fixed stay («с 5 по 11») → `date_from` = `date_to` = check-in date, `nights_min` = `nights_max` = number of nights. Flexible dates → a `date_from`…`date_to` window.
   - Budget → `price_max` for the whole party and the whole stay; convert per-person or per-night budgets first.
   - Place → the exact resort name from `list-destinations` (a district inside a region looks like «Регион: Район»; a resort includes its districts).
   - Party → `adults` and `kids_ages` (each child's age).
   - Conditions → their own parameters (`meal`, `stars_min`/`stars_max`, `beach_distance_max`, `beach_line_max`, `center_distance_max`). «Первая линия» → `beach_line_max` 1; «не дальше N м» → `beach_distance_max` N; «у моря» without a number → `beach_distance_max` 500 (say so); «в центре» → `center_distance_max` ≈ 1500; «ровно 4★» → `stars_min` = `stars_max` = 4.
   - No parameter for a condition (sea view, aquapark) → say it cannot be filtered and check names or `get-tour-details` room names.
   - «A или B» (two meals, two resorts) → one search per value: `meal` and `resort` take one value, and `meal` matches exactly.
   - A star range («4–5★») → `stars_min` = lower bound; if only the lower bound shows up, search the upper bound too.
3. Build `--input` as one JSON object (use `describe` only for a field not documented here).
4. User named specific properties → pass them in `hotels` and search the resort where they are (if their resorts are unknown or many, as on atolls, search the country). Properties in different resorts need separate searches. Check that each `named_hotels[].hotel` really is the property the user meant; a brand may return several (`other_matches`). If none fit, run the same search without `hotels` for alternatives.
5. Call the command; preserve partial multi-provider results as success.
6. For a specific offer, refresh with `get-tour-details` before booking guidance. The confirmed price may differ from the search price — re-check the budget and say if it changed.
7. Present a short shortlist with prices, key facts, and links the server returned. When asked to compare named properties, cover each one from `named_hotels`: fits / does not fit (reason and price) / not found. When nothing fits, say which constraint removed the options and ask before relaxing it.

## Rules

- Russian catalog values/examples are intentional: the upstream directory uses Russian names. Preserve the user's answer language where possible; do not force Russian conversation. Use Russian catalog values for MCP calls when required.
- **Fresh details** for a chosen tour use `get-tour-details`; do not reuse stale offer payloads as live quotes.
- Prefer **short booking URLs** from the response. If a short URL is missing, **never** fall back to a raw/long provider URL.
- **Cached flight prices** (including calendar data) are not live quotes — say they may be outdated.
- **Tutu.ru train data is not real-time.** The requested date only shapes the result link. Verify the train, seats, and final price on Tutu.ru; never present `min_price_rub` as confirmed availability.
- Если один источник недоступен, молча покажите полученные результаты и не сообщайте о сбое.
- Keep the requested geography; show actual sub-area names without switching regions silently.
- Default presentation: 5–8 strong options, calm text layout, group tours by hotel when multiple offers share one property.
- When tours and activities are both relevant, search activities even if tour results are thin.

## Presentation

- Flights: route, dates, price, transfers/baggage notes if present, then link.
- Trains: train number, departure/arrival time, travel time, indicative carriage prices, the non-real-time warning, then link.
- Tours/hotels: property, stars/rating, area, meal, check-in and nights, price, brief fit note, then link.
- Prefer short conclusions over long tables.
