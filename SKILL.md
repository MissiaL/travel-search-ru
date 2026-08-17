---
name: travel-search-ru
description: "Use while planning a trip when Russian-catalog search is needed: package tours, hotels, flights, trains, excursions, prices, and booking links. Trigger on Russian requests: «спланировать путешествие», «подобрать тур», «найти отель/авиабилеты/жд билеты/экскурсии», «маршрут с актуальными ценами». Not for general advice without live search."
compatibility: Requires Python 3.8+ and outbound HTTPS access to https://mcp.botclaw.ru/travel. Search criteria are sent to this read-only service; it does not book.
metadata:
  author: MissiaL
  version: "2.2.0"
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

Commands: `search-tours`, `search-hotels`, `get-tour-details`, `search-flights`, `flight-calendar`, `search-trains`, `search-activities`, `list-destinations`.

Current tool schemas change over time. **Always** run `describe <command>` before a new parameter shape; do not invent fields from memory. See [references/usage.md](references/usage.md).

## Examples

```bash
python scripts/travel_search.py search-tours --input '{"departure_city":"Москва","country":"Турция","date_from":"2026-09-10","date_to":"2026-09-20","adults":2}'
python scripts/travel_search.py search-flights --input '{"origin":"MOW","destination":"AYT","depart_date":"2026-09-15","adults":1}'
python scripts/travel_search.py search-trains --input '{"origin":"Москва","destination":"Сочи","depart_date":"2026-09-15","sort":"price","limit":5}'
python scripts/travel_search.py search-activities --input '{"city":"Анталья","date_from":"2026-09-10","date_to":"2026-09-12","persons":2,"children_allowed":true,"sort":"recommended","limit":5}'
```

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

**Budget:** never auto-show offers that break a hard budget. Alternatives outside any hard constraint may appear only after **explicit user consent**, and only in a **separate labeled section**.

## When to use which command

| Need | Command |
|------|---------|
| Package tour (flight + hotel) | `search-tours` |
| Hotel only (no flight) | `search-hotels` |
| Fresh price/availability before booking a tour | `get-tour-details` |
| Flight options | `search-flights` |
| Flight price calendar / flexible dates | `flight-calendar` |
| Train schedule and indicative fares | `search-trains` |
| Excursions and activities | `search-activities` |
| Resolve destinations / directories | `list-destinations` |

## Activities

`search-activities` принимает необязательные `date_from` и `date_to` в формате `YYYY-MM-DD` (`date_from` ≤ `date_to`), `persons` от 1 до 100 и булево `children_allowed`. Сортировка: `recommended` (по умолчанию), `price`, `rating` или `reviews`. В каждой записи указан источник `provider`, единица цены `price_unit` (`per_person`, `per_group`, `per_ticket` или `unknown`) и понятный текст `price_text`. Сравнивайте цены только при одинаковом `price_unit`; сортировка `price` не смешивает разные единицы.
## Workflow

1. Clarify hard constraints (place, dates/nights, travelers, budget).
2. Resolve ambiguous places with `list-destinations` when needed.
3. `describe` the command you will call; build `--input` as one JSON object.
4. Call the command; preserve partial multi-provider results as success.
5. For a specific tour offer, refresh with `get-tour-details` before booking guidance.
6. Present a short shortlist with prices, key facts, and links the server returned.

## Rules

- Russian catalog values/examples are intentional: the upstream directory uses Russian names. Preserve the user's answer language where possible; do not force Russian conversation. Use Russian catalog values for MCP calls when required.
- **Hotel-only** requests use `search-hotels`, not package `search-tours`.
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
