# Level.Travel API

Package tours (flight + hotel) and hotel-only offers via Level.Travel live async search.
Same tier as Travelata: call both on every tour request, wait once, fetch both result sets,
merge and label the source of each option.

Base URL: `https://api.botclaw.ru/leveltravel/`

## Endpoints

```text
GET  https://api.botclaw.ru/leveltravel/search/enqueue
GET  https://api.botclaw.ru/leveltravel/search/status
GET  https://api.botclaw.ru/leveltravel/search/get_grouped_hotels
GET  https://api.botclaw.ru/leveltravel/search/hotel_rooms
GET  https://api.botclaw.ru/leveltravel/packages/package_details
GET  https://api.botclaw.ru/leveltravel/references/departures
GET  https://api.botclaw.ru/leveltravel/references/destinations
GET  https://api.botclaw.ru/leveltravel/references/hotels
```

All endpoints are GET and return JSON. Results come from live async search.

## Search Flow

Mirror the Travelata two-step pattern with Level.Travel's own endpoint names:

1. **Start async search** with `GET /search/enqueue` — returns `request_id` and a per-operator `status` map.
2. **Wait** before fetching results:
   - Close destinations (Turkey, Egypt, UAE, Cyprus, Greece): ~7 seconds
   - Far destinations (Vietnam, Thailand, Indonesia/Bali, Cuba, Dominican Republic, Maldives, Mexico): ~10 seconds
   - When running Travelata and Level.Travel together, wait the **longer** of the two recommended waits for that destination, then fetch both.
3. **Fetch hotels** with `GET /search/get_grouped_hotels?request_id=...&limit=10..20`.
4. **If fewer than ~5 hotels came back** and operators still look unfinished (`performing` in the enqueue `status` map, or after an optional `search/status` check), wait another 3–5 seconds and re-call `get_grouped_hotels` with the **same** `request_id`. No new enqueue.

Do **not** make `GET /search/status` a mandatory step. It is optional, for edge-case debugging only — it costs an extra call and does not return hotel data. Soft-polling via a second `get_grouped_hotels` is enough in the normal flow.

### Step 1 — enqueue search

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/leveltravel/search/enqueue" \
  --params '{"from_city":"Moscow","to_country":"TR","adults":"2","start_date":"28.07.2026","nights":"7..9","kids":"0"}'
```

Typical response:

```json
{
  "success": true,
  "request_id": "abc123...",
  "status": {
    "12": "pending",
    "34": "pending"
  }
}
```

### Step 2 — fetch grouped hotels

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/leveltravel/search/get_grouped_hotels" \
  --params '{"request_id":"<request_id>","limit":"15"}'
```

Always pass `limit=10..20` to keep responses small (API default is 30, max 100).

## Enqueue Parameters (`GET /search/enqueue`)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `from_city` | string | yes | Departure city `name_en` (e.g. `Moscow`). See departures table / `references/departures` |
| `to_country` | string | yes | Destination country ISO2 (e.g. `TR`). From `references/destinations` |
| `adults` | int | yes | Number of adults |
| `start_date` | string | yes* | Check-in date in **DD.MM.YYYY** (e.g. `28.07.2026`) — not ISO |
| `nights` | string | yes* | Night range, e.g. `7..9` |
| `flex_dates` | int | no | ± days around `start_date` |
| `start_date_from` / `start_date_till` / `end_date_from` / `end_date_till` | string | no | Alternative to `start_date` + `flex_dates`: date-interval bounds |
| `to_city` | string | no | Destination city `name_en` — narrows within the country |
| `kids` | int | no | Number of children. Default 0 |
| `kids_ages[]` | int array | **required when kids > 0** | One age per child; repeated query param |
| `hotel_ids[]` | int/string array | no | Search specific hotels only |
| `search_type` | string | no | `package` (default, flight+hotel) or `hotel` (hotel only, no flight) |

\* Use either `start_date` + `nights` (optionally with `flex_dates`) **or** the date-interval params. Prefer `start_date` + `nights` for normal queries.

### Kids handling

Whenever `kids > 0`, always pass `kids_ages[]` with one age per child:

```json
{
  "from_city": "Moscow",
  "to_country": "TR",
  "adults": "2",
  "kids": "2",
  "kids_ages[]": ["8", "5"],
  "start_date": "28.07.2026",
  "nights": "7..9"
}
```

`api_call.py` uses `doseq=True` for GET, so bracketed array keys work as repeated params.

### Date format warning (common bug)

| Context | `start_date` format |
|---------|---------------------|
| **Enqueue API** (`search/enqueue`) | **DD.MM.YYYY** — e.g. `28.07.2026` |
| **Site link** (`https://level.travel/hotels/...?start_date=...`) | **YYYY-MM-DD** — e.g. `2026-07-28` |

These formats are different on purpose. Converting incorrectly is a frequent source of broken links or failed searches. Always reformat when moving between the API and the booking URL.

There is **no meal-plan / pansion parameter** on enqueue. Filter meal type client-side from each hotel's `pansion_prices` keys in the results (see below).

## Results Parameters (`GET /search/get_grouped_hotels`)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | string | yes | From enqueue response |
| `limit` | int | no | Max hotels returned. **Pass 10–20.** Default 30, max 100 |
| `filter_price_min` | int | no | Minimum price (RUB) |
| `filter_price_max` | int | no | Maximum price (RUB) |
| `filter_stars` | string | no | Comma list of star ratings, e.g. `5,4` |
| `filter_rating` | number | no | Minimum hotel rating (0–10 scale) |
| `filter_hotel_name` | string | no | Hotel name substring |
| `filter_regions` | string | no | Region filter |

Additional filter params may exist beyond this list; the common ones above cover most agent needs.

## Response Shape (`get_grouped_hotels`)

```json
{
  "success": true,
  "status": {},
  "hotels": [
    {
      "hotel": {
        "id": 9136093,
        "name": "Seyithan Palace Spa Hotel",
        "stars": 5,
        "rating": 8.7,
        "reviews_count": 342,
        "link": "/hotels/9136093-Seyithan_Palace_Spa_Hotel",
        "region_name": "Kemer",
        "city": "Kemer",
        "images": ["..."],
        "features": {}
      },
      "min_price": 187000,
      "min_price_nights": 7,
      "dates": {"2026-07-28": 187000},
      "pansion_prices": {"RO": 187000, "AI": 210000},
      "operators": [12, 34],
      "tour_id": "...",
      "availability": "...",
      "cancellation_policy": "..."
    }
  ],
  "hotels_count": 42,
  "currency_code": "RUB",
  "currency_symbol": "₽",
  "sort_by": "price",
  "search_type": "package"
}
```

Field notes:

- `hotels_count` — total matched hotels **before** truncation by `limit`.
- `hotel.link` — **relative** path starting with `/hotels/...`. Prefix with `https://level.travel` before use.
- `hotel.rating` — 0–10 scale (not stars, not 0–5).
- `pansion_prices` — keys are board codes: `RO` (room only), `BB` (bed & breakfast), `HB` (half board), `FB` (full board), `AI` (all inclusive), `UAI` (ultra all inclusive), etc. Pick the cheapest offer at the desired board level client-side.
- `min_price` / `dates` — useful for the cheapest date/price point without opening room details.

## Optional Deep-Dive Endpoints

### Room-level offers — `GET /search/hotel_rooms`

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/leveltravel/search/hotel_rooms" \
  --params '{"request_id":"<request_id>","hotel_id":"9136093"}'
```

Optional step when the user wants room details for one hotel (similar spirit to Travelata's per-tour actualization). Not part of the default list flow.

### Package details — `GET /packages/package_details`

Optional deeper look at one specific offer before presenting it as the final recommendation. Expect `request_id` (and likely offer identifiers) among the params. Exact param set is not fully listed here — if you need this step, confirm params with a trial GET rather than inventing a table. Use only when the user is narrowing to a final pick, not for every hotel in a shortlist.

### Status — `GET /search/status`

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/leveltravel/search/status" \
  --params '{"request_id":"<request_id>"}'
```

Per-operator status values include: `pending`, `performing`, `completed`, `no_results`, `failed`, `skipped`. Optional / debugging only.

## Reference Lookups

All GET, no async wait needed.

| Endpoint | Purpose | Params |
|----------|---------|--------|
| `GET /references/departures` | Valid departure cities | none |
| `GET /references/destinations` | Countries + cities | none |
| `GET /references/hotels` | Hotel info lookup | **`hotel_ids` OR `region_ids`** (at least one required; HTTP 400 if neither) |

- Departures: each item has `name_ru`, `name_en`, `iata`. Use **`name_en`** as `from_city` in enqueue.
- Destinations: each item has `name_ru`, `name_en`, `iso2`. Use **`iso2`** as `to_country`, **`name_en`** as `to_city`.

### Common departure cities (`from_city`)

| name_ru | name_en (`from_city`) |
|---------|------------------------|
| Москва | Moscow |
| Санкт-Петербург | Saint Petersburg |
| Екатеринбург | Ekaterinburg |
| Казань | Kazan |
| Новосибирск | Novosibirsk |
| Самара | Samara |
| Уфа | Ufa |
| Краснодар | Krasnodar |
| Ростов-на-Дону | Rostov-on-Don |
| Нижний Новгород | Nizhny Novgorod |
| Челябинск | Chelyabinsk |
| Пермь | Perm |
| Красноярск | Krasnoyarsk |
| Тюмень | Tyumen |
| Минеральные Воды | Mineralnye Vody |

For the full list or any city not in this table, call `GET /references/departures`.

## Booking Links

Build the user-facing hotel link from `hotel.link` (relative path) and query params:

```text
https://level.travel{hotel.link}?start_date=YYYY-MM-DD&nights=N&adults=N
```

Example:

```text
https://level.travel/hotels/9136093-Seyithan_Palace_Spa_Hotel?start_date=2026-07-28&nights=7&adults=2
```

**Remember:** site `start_date` is **YYYY-MM-DD**; enqueue used **DD.MM.YYYY**.

Shorten every such link via the link-shortening service before showing it:

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/short-link" \
  --params '{"url":"https://level.travel/hotels/9136093-Seyithan_Palace_Spa_Hotel?start_date=2026-07-28&nights=7&adults=2"}'
```

## Search Strategy

- On **any** tour request, start Level.Travel enqueue **and** Travelata `asyncSearch` in the same step. Wait once (use the longer wait if they differ), then fetch both result sets and merge. Label which source each hotel/tour came from.
- Prefer `start_date` + `nights` (e.g. `7..9`) over a single fixed night count.
- Use `flex_dates` or date-interval params when the user is flexible on dates.
- Kids are fully supported: pass `kids` + `kids_ages[]` whenever kids > 0.
- Any night count and any date horizon are valid — no hard 7–15 / near-term limits.
- `search_type=package` (default) for flight+hotel; `search_type=hotel` for hotel only.
- Meal/board filtering is client-side via `pansion_prices` keys (`AI`, `UAI`, etc.). There is no meal param on enqueue.
- Pass `limit=10..20` on `get_grouped_hotels`. If `hotels_count` is much larger than returned, say you showed the best subset and can expand.
- If the first fetch is thin (< ~5 hotels) and operators may still be working, wait 3–5 s and re-fetch with the same `request_id` before relaxing criteria.
- Sort and group client-side; present the cheapest strong hotels, not a raw dump.

## Error Handling

HTTP **400** responses include an `error` field describing what is wrong (e.g. missing required param). Fix the params and retry. Do not invent params that are not in this doc for enqueue / get_grouped_hotels; for `package_details`, confirm via a trial GET if needed.

## Presentation Notes

- Show hotel name, stars, region/city, rating (0–10), meal/board chosen from `pansion_prices`, check-in, nights, price, source label (`Level.Travel`), and short booking link.
- Prefer 5–8 hotels in the shortlist; group by hotel when comparing dates or board options.
- When merging with Travelata, keep source labels clear so the user can tell which site each offer opens.
