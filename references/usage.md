# Travel Search CLI usage

**Privacy:** Every command sends the supplied JSON search criteria to the live external production service. Criteria may contain itinerary/location, dates, traveler counts/ages, budget, and preferences. Do not include names, contacts, passport/payment details, credentials, or unnecessary sensitive data. The local skill does not persist requests, but no server-side retention guarantee is declared, so treat it as an external service.

The skill talks only to the production MCP endpoint over Streamable HTTP. There is no public `--url` flag and no environment-based endpoint override.

## Commands

```bash
python scripts/travel_search.py list-tools
python scripts/travel_search.py describe <command>
python scripts/travel_search.py <command> --input '<JSON object>'
```

| CLI command | MCP tool |
|-------------|----------|
| `search-tours` | `search_tours` |
| `cheapest-tours` | `get_cheapest_travelata_tours` |
| `search-hotels` | `search_hotels` |
| `get-tour-details` | `get_tour_details` |
| `search-flights` | `search_flights` |
| `flight-calendar` | `get_flight_price_calendar` |
| `search-trains` | `search_train_tickets` |
| `search-activities` | `search_activities` |
| `list-destinations` | `list_destinations` |

## Input

`--input` must be a single JSON **object**. Arrays, strings, numbers, `null`, and `true`/`false` are rejected.

```bash
python scripts/travel_search.py search-tours --input '{"departure_city":"Москва","country":"Турция","date_from":"YYYY-MM-DD","date_to":"YYYY-MM-DD","nights_min":7,"nights_max":10,"adults":2,"meal":"AI"}'
python scripts/travel_search.py cheapest-tours --input '{"departure_city":"Москва","country":"Турция","date_from":"YYYY-MM-DD","date_to":"YYYY-MM-DD","nights_min":7,"nights_max":10,"resorts":["Кемер"],"meals":["AI","UAI"],"limit":5}'
python scripts/travel_search.py search-flights --input '{"origin":"MOW","destination":"AYT","depart_date":"YYYY-MM-DD","adults":1}'
python scripts/travel_search.py flight-calendar --input '{"origin":"MOW","destination":"AYT","month":"YYYY-MM"}'
python scripts/travel_search.py search-trains --input '{"origin":"Москва","destination":"Сочи","depart_date":"YYYY-MM-DD","sort":"price","limit":5}'
python scripts/travel_search.py search-activities --input '{"city":"Анталья","date_from":"YYYY-MM-DD","date_to":"YYYY-MM-DD","persons":2,"children_allowed":true,"sort":"recommended","limit":5}'
```

### Dates

`YYYY-MM-DD` / `YYYY-MM` above are placeholders. Determine today's date first (run `date +%F` if it is unknown). Every date is `YYYY-MM-DD` and must not be in the past; `flight-calendar` takes `month` as `YYYY-MM`. A day or month without a year means its next future occurrence. The server rejects past or malformed dates with a Russian validation message.

## Discover schemas

Do not hard-code provider field lists. Ask the live server:

```bash
python scripts/travel_search.py describe search-tours
```

Response shape:

```json
{
  "name": "search_tours",
  "description": "...",
  "inputSchema": { "type": "object", "properties": {} }
}
```

`list-tools` returns all nine CLI names with mapped MCP names and live descriptions.

## Tours and hotels

`search-tours`, `search-hotels`, and `cheapest-tours` share these rules:

- `date_from`…`date_to` is the departure (hotel check-in) window: `date_to` ≥ `date_from`, at most 30 days.
- Always pass `nights_min` and `nights_max` explicitly (`nights_min` ≤ `nights_max`; defaults are 7–10 for tours and hotels). Level.Travel searches at most 5 night values: a wider range is clamped to `nights_min`…`nights_min`+4 with a note, while Travelata searches the full range. For wider ranges run several searches one after another.
- Meal codes: `RO` (без питания), `BB` (завтраки), `HB` (полупансион), `FB` (полный пансион), `AI` (всё включено), `UAI` (ультра всё включено). Pass codes, not names: `meal` for `search-tours` / `search-hotels`, a `meals` list for `cheapest-tours`.
- `search-hotels` also requires `departure_city` even for hotel-only stays. Pass the user's home city, or `Москва` if unknown; it only affects availability.
- `cheapest-tours` (`get_cheapest_travelata_tours`) is a quick Travelata-only overview of the cheapest tours: `departure_city`, `country`, `date_from`, `date_to`, optional `nights_min` / `nights_max`, `adults` (default 2), `kids_ages`, `resorts` (list), `meals` (list of codes), `stars_min`, `limit` (default 10). Refresh a chosen result with `get-tour-details` using its `offer_id`.

## Flights

- `search-flights` takes optional `return_date` (`YYYY-MM-DD`). A round trip longer than 30 days is answered as two one-way legs: items carry `"leg": "outbound"` or `"leg": "return"`, the total is their sum, and a note explains it.
- One-way searches return the cheapest option per date, often a single item.
- Prices are economy even when `trip_class` is not `0` (the server adds a note).
- `flight-calendar` requires `month` in `YYYY-MM`.

## Trains

`search-trains` accepts Russian location names or 7-digit station codes,
`depart_date` in `YYYY-MM-DD`, `sort` (`price`, `duration`, or `departure`), and
`limit` from 1 to 20. Tutu.ru returns cached schedules and indicative prices,
not live inventory. The date is used in the result link but does not filter the
upstream timetable. Always tell the user to verify that the train runs, seats
are available, and the final price on Tutu.ru.

## Activities

`search-activities` принимает необязательные `date_from` и `date_to` в формате `YYYY-MM-DD` (`date_from` ≤ `date_to`), `persons` от 1 до 100 и булево `children_allowed`. Для `sort`: `recommended` (по умолчанию), `price`, `rating` или `reviews`.

Каждый смешанный результат содержит `provider`, `price_unit` и `price_text`. Сравнивайте цены только при одинаковом `price_unit`; сортировка по цене не смешивает цену за человека, группу, билет и неизвестную единицу. Если один источник недоступен, покажите оставшиеся результаты без сообщения о сбое.

## Output and exit codes

Every invocation prints exactly one JSON document to stdout (including `-h` / `--help`).

| Code | Meaning |
|------|---------|
| 0 | Success (including useful partial multi-provider results; also help) |
| 2 | Usage or input error |
| 1 | MCP / transport failure |

On failure, stdout is a small JSON object with `error`, `category`, and `message`. Stderr may contain only a short category token.

| Category | Meaning | What to do |
|----------|---------|------------|
| `tool_error` | The server rejected or could not run the call; `message` is its text | See below |
| `rate_limited` | HTTP 429 from the service; `message` includes `retry after N s` when the server sent `Retry-After` | Wait about a minute (or `N` seconds) |
| `timeout`, `network_error`, `http_error`, others | Transport or protocol failure | Retry once later, then tell the user |

For `tool_error`, `message` is the first text item of the server's error with the `Error executing tool <name>: ` prefix and any URLs removed, capped at 300 characters. Typical texts:

- Russian validation message (dates, nights, meal codes, …) — fix the input; do not repeat the same call.
- «Источник отклонил параметры запроса…» — the provider rejected the parameters; change them.
- «Источник временно недоступен. Повторите позже.» — provider outage; retry once later, then tell the user.
- «Сервис поиска сейчас перегружен…» or «Слишком много запросов…» — rate limit; wait about a minute.

Never start a second `search-tours` while one is running, and do not repeat it with identical arguments — widen dates or filters within the user's hard constraints instead.

## Result normalization

For tool calls the CLI preserves normalized MCP data:

1. If the tool result has `isError` exactly `true`, fail with `tool_error` (exit 1); only the sanitized first text item is surfaced as `message`, never `structuredContent`.
2. Prefer `structuredContent` when present.
3. Else, if the first text content item is a JSON document, decode and return it.
4. Else return the MCP result/content object without inventing fields.

Useful partial multi-provider payloads without `isError: true` remain success (exit 0).

## Agent checklist

- Exact geography, dates, nights, traveler composition, and **budget** are hard constraints.
- Do **not** auto-show above-budget offers. Alternatives outside a hard constraint only after **explicit user consent**, in a **separate labeled section**.
- Unknown child ages → clarify before bookable family prices.
- Hotel-only → `search-hotels`.
- Refresh a chosen tour → `get-tour-details`.
- Missing short booking URL → do not substitute a raw URL.
- Flight prices from search/calendar may be cached — not live tickets.
- Tutu.ru train schedules/fares are cached and not date-verified — keep the warning and verify details through the returned link.
