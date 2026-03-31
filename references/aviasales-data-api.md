# Aviasales Data API Reference

**Base URL:** `https://api.botclaw.ru`

All responses: `{"success": true/false, "data": {...}, "error": null}`. Prices in RUB by default. Dates in ISO 8601 UTC.

---

## GET /aviasales/v3/prices_for_dates

Cheapest tickets for specific dates (last 48h cache). Preferred over `/v1/prices/cheap`, `/v1/prices/direct`, `/v2/prices/latest`.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| origin | string | — | IATA city/airport code (e.g. `MOW`) |
| destination | string | — | IATA city/airport code; required if no origin |
| departure_at | string | — | `YYYY-MM` or `YYYY-MM-DD` |
| return_at | string | — | Return date; omit for one-way |
| one_way | bool | true | true=one-way; false=round-trip (more results) |
| direct | bool | false | Non-stop only |
| currency | string | RUB | Price currency |
| sorting | string | price | `price` or `route` (by popularity) |
| unique | bool | false | Only unique routes (use with origin-only) |
| limit | int | 30 | Max 1000 |
| page | int | 1 | Pagination |
| market | string | ru | Data market (e.g. `us`, `ru`) |

**Example:**
```python
import requests
r = requests.get("https://api.botclaw.ru/aviasales/v3/prices_for_dates",
    params={"origin":"MOW","destination":"LED","departure_at":"2026-05","currency":"usd","limit":5})
print(r.json())
```

**Response:**
```json
{"success": true, "data": [
  {"origin":"MOW","destination":"LED","origin_airport":"SVO","destination_airport":"LED",
   "price":45,"airline":"SU","flight_number":"20","departure_at":"2026-05-10T07:00:00+03:00",
   "return_at":"","transfers":0,"return_transfers":0,"duration":90,"duration_to":90,
   "duration_back":0,"link":"/search/MOW1005LED1?t=..."}
]}
```

**Replaces legacy endpoints:**
- `/v1/prices/cheap` → `direct=false&sorting=price`
- `/v1/prices/direct` → `direct=true&sorting=price`
- `/v1/city-directions` → `sorting=route&unique=true` (origin only)

---

## GET /aviasales/v3/get_latest_prices

Cheapest tickets for a period of time.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| origin | string | — | IATA code |
| destination | string | — | IATA code |
| currency | string | RUB | Price currency |
| period_type | string | — | `year`, `month`, `day` |
| beginning_of_period | string | — | `YYYY` / `YYYY-MM-DD` depending on period_type |
| group_by | string | dates | `dates` or `directions` |
| one_way | bool | true | — |
| sorting | string | price | `price`, `route`, `distance_unit_price` |
| trip_duration | int | — | Stay duration in days |
| trip_class | int | 0 | 0=economy, 1=business, 2=first |
| page | int | 1 | — |
| market | string | ru | — |

**Example:**
```python
r = requests.get("https://api.botclaw.ru/aviasales/v3/get_latest_prices",
    params={"origin":"MOW","destination":"LED","currency":"usd","period_type":"month",
            "beginning_of_period":"2026-05-01","sorting":"price"})
```

**Response:**
```json
{"success": true, "data": [
  {"origin":"MOW","destination":"LED","depart_date":"2026-05-07","return_date":"2026-05-14",
   "number_of_changes":0,"value":55,"found_at":"2026-03-28T10:00:00+04:00","distance":633,"actual":true}
]}
```

---

## GET /aviasales/v3/grouped_prices

Cheapest tickets grouped by departure date or month. Replaces `/v1/prices/calendar` and `/v1/prices/monthly`.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| origin | string | — | IATA code |
| destination | string | — | IATA code |
| currency | string | RUB | — |
| group_by | string | departure_at | `departure_at` or `month` |
| departure_at | string | — | `YYYY-MM` or `YYYY-MM-DD` |
| return_at | string | — | Return date |
| direct | bool | false | Non-stop only |
| min_trip_duration | int | — | Min stay in days |
| max_trip_duration | int | — | Max stay in days |
| market | string | ru | — |

**Example:**
```python
r = requests.get("https://api.botclaw.ru/aviasales/v3/grouped_prices",
    params={"origin":"LON","destination":"BCN","group_by":"month","currency":"usd"})
```

**Response:**
```json
{"success": true, "data": {
  "2026-05-01": {"origin":"LON","destination":"BCN","price":120,"airline":"IB",
    "departure_at":"2026-05-03T10:00:00+01:00","transfers":0,"link":"/search/..."}
}}
```

---

## GET /aviasales/v3/get_special_offers

Abnormally low prices (flash deals).

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| origin | string | — | IATA code (auto-detected from IP if omitted) |
| destination | string | — | IATA code |
| currency | string | RUB | — |
| locale | string | — | Response language (e.g. `en`, `ru`) |
| airline | string | — | Filter by airline IATA code |
| market | string | ru | — |

**Example:**
```python
r = requests.get("https://api.botclaw.ru/aviasales/v3/get_special_offers",
    params={"origin":"MOW","currency":"usd","locale":"en"})
```

**Response:**
```json
{"success": true, "currency":"usd", "data": [
  {"airline":"SU","airline_title":"Aeroflot","origin":"MOW","destination":"LED",
   "price":28,"departure_at":"2026-04-15T08:00:00+03:00","duration":90,
   "flight_number":"20","link":"/search/MOW1504LED1?t=...","title":"Deals from Moscow"}
]}
```

---

## GET /aviasales/v3/get_popular_directions

Most popular destinations to a given city (based on user searches).

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| destination | string | — | IATA code (required) |
| currency | string | RUB | — |
| locale | string | — | Response language |
| limit | int | 30 | 1–30 |
| page | int | 1 | — |

**Example:**
```python
r = requests.get("https://api.botclaw.ru/aviasales/v3/get_popular_directions",
    params={"destination":"CDG","currency":"usd","locale":"en","limit":10})
```

**Response:**
```json
{"success": true, "currency":"usd", "data": {
  "destination":{"city_name":"Paris","country_name":"France"},
  "origin":[
    {"city_name":"New York City","city_iata":"JFK","departure_at":"2026-05-10","price":420}
  ]
}}
```

---

## GET /aviasales/v3/search_by_price_range

Tickets within a specific price band.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| origin | string | — | IATA code |
| destination | string | — | IATA code (use `-` for all) |
| value_min | number | — | Minimum price |
| value_max | number | — | Maximum price |
| currency | string | RUB | — |
| one_way | bool | — | true=one-way, false=round-trip |
| direct | bool | false | Non-stop only |
| locale | string | — | Response language |
| market | string | ru | — |
| limit | int | 30 | Results per page |
| page | int | 1 | — |

**Example:**
```python
r = requests.get("https://api.botclaw.ru/aviasales/v3/search_by_price_range",
    params={"origin":"LON","destination":"BCN","value_min":50,"value_max":200,
            "currency":"usd","one_way":"true","direct":"false"})
```

**Response:**
```json
{"success": true, "currency":"usd", "data": [
  {"origin_code":"LON","origin_airport":"LHR","origin_name":"London",
   "destination_code":"BCN","destination_airport":"BCN","destination_name":"Barcelona",
   "departure_at":"2026-05-03","price":88,"transfers":0,"duration":120,"link":"/search/..."}
]}
```

---

## GET /v2/prices/month-matrix

Prices for each day of a month, grouped by number of transfers.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| origin | string | — | IATA city or country code (2–3 chars) |
| destination | string | — | IATA city or country code |
| currency | string | RUB | — |
| month | string | — | `YYYY-MM-DD` (first day of month) |
| one_way | bool | true | — |
| trip_duration | int | — | Stay length in weeks |
| show_to_affiliates | bool | true | true=verified prices only (recommended) |
| limit | int | 30 | Set 31 for 31-day months |
| market | string | ru | — |

**Example:**
```python
r = requests.get("https://api.botclaw.ru/v2/prices/month-matrix",
    params={"origin":"MOW","destination":"LED","month":"2026-05-01","currency":"usd"})
```

**Response:**
```json
{"success": true, "data": [
  {"origin":"MOW","destination":"LED","depart_date":"2026-05-01","return_date":"",
   "trip_class":0,"number_of_changes":0,"value":45,"found_at":"2026-03-28T00:00:00+04:00",
   "distance":633,"actual":true}
]}
```

---

## GET /v2/prices/week-matrix

Prices for a 7-day window (±3–4 days) around specified departure/return dates.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| origin | string | — | IATA code |
| destination | string | — | IATA code |
| currency | string | RUB | — |
| depart_date | string | — | `YYYY-MM-DD` or `YYYY-MM` |
| return_date | string | — | `YYYY-MM-DD` or `YYYY-MM` |
| show_to_affiliates | bool | true | — |
| market | string | ru | — |

**Example:**
```python
r = requests.get("https://api.botclaw.ru/v2/prices/week-matrix",
    params={"origin":"MOW","destination":"LED","depart_date":"2026-05-10",
            "return_date":"2026-05-17","currency":"usd"})
```

**Response:**
```json
{"success": true, "data": [
  {"origin":"MOW","destination":"LED","depart_date":"2026-05-08","return_date":"2026-05-15",
   "trip_class":0,"number_of_changes":0,"value":52,"distance":633,"actual":true}
]}
```

---

## GET /v2/prices/nearest-places-matrix

Prices including nearby airports for origin and destination.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| origin | string | — | IATA code |
| destination | string | — | IATA code |
| currency | string | RUB | — |
| limit | int | — | Variants 1–20 (1=exact route only) |
| depart_date | string | — | `YYYY-MM` (optional) |
| return_date | string | — | `YYYY-MM` (optional) |
| flexibility | int | 0 | Date range ±days (0–7) |
| distance | int | — | Search radius in km |
| show_to_affiliates | bool | true | — |
| market | string | ru | — |

**Example:**
```python
r = requests.get("https://api.botclaw.ru/v2/prices/nearest-places-matrix",
    params={"origin":"MOW","destination":"LED","currency":"usd","limit":5})
```

**Response:**
```json
{"prices":[
  {"origin":"MOW","destination":"LED","value":48,"trip_class":0,"depart_date":"2026-05-10",
   "return_date":"2026-05-17","number_of_changes":0,"found_at":"2026-03-28T10:00:00Z","actual":true}
], "origins":["MOW"], "destinations":["LED"]}
```

---

## GET /v2/prices/latest

Latest known prices (general cache lookup).

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| origin | string | — | IATA code |
| destination | string | — | IATA code |
| currency | string | RUB | — |
| period_type | string | — | `year`, `month`, `day` |
| one_way | bool | true | — |
| page | int | 1 | — |
| limit | int | 30 | — |
| sorting | string | price | `price`, `route` |
| market | string | ru | — |

**Example:**
```python
r = requests.get("https://api.botclaw.ru/v2/prices/latest",
    params={"origin":"MOW","destination":"LED","currency":"usd","limit":10})
```

---

## GET /v1/prices/cheap

Cheapest tickets (0, 1, 2 stops) grouped by destination.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| origin | string | — | IATA code |
| destination | string | — | IATA code (omit for all) |
| currency | string | RUB | — |
| depart_date | string | — | `YYYY-MM` |
| return_date | string | — | `YYYY-MM` |
| page | int | 1 | — |
| market | string | ru | — |

**Example:**
```python
r = requests.get("https://api.botclaw.ru/v1/prices/cheap",
    params={"origin":"LON","destination":"HKT","currency":"usd","depart_date":"2026-11"})
```

**Response:**
```json
{"success": true, "data": {
  "HKT": {
    "0": {"price":350,"airline":"FD","flight_number":571,
          "departure_at":"2026-11-09T21:20:00Z","return_at":"2026-12-15T12:40:00Z","expires_at":"2026-04-08T18:30:40Z"},
    "1": {"price":280,"airline":"CX","flight_number":204,
          "departure_at":"2026-11-05T16:40:00Z","return_at":"2026-11-22T12:00:00Z","expires_at":"2026-04-08T18:38:45Z"}
  }
}}
```
Keys `0`, `1`, `2` = number of stops.

---

## GET /v1/prices/direct

Cheapest non-stop tickets only.

**Parameters:** Same as `/v1/prices/cheap` (origin, destination, currency, depart_date, return_date, market).

**Example:**
```python
r = requests.get("https://api.botclaw.ru/v1/prices/direct",
    params={"origin":"LON","destination":"BCN","currency":"usd","depart_date":"2026-11"})
```

**Response:** Same structure as `/v1/prices/cheap`, only key `"0"` (direct).

---

## GET /v1/prices/calendar

Cheapest ticket for each day of a month (0/1/2 stops).

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| origin | string | — | IATA code |
| destination | string | — | IATA code |
| currency | string | RUB | — |
| departure_date | string | — | `YYYY-MM` |
| return_date | string | — | `YYYY-MM` |
| calendar_type | string | — | `departure_date` or `return_date` |
| length | int | — | Stay duration in days |
| market | string | ru | — |

**Example:**
```python
r = requests.get("https://api.botclaw.ru/v1/prices/calendar",
    params={"origin":"LON","destination":"BCN","departure_date":"2026-11",
            "calendar_type":"departure_date","currency":"usd"})
```

**Response:**
```json
{"success": true, "data": {
  "2026-11-01": {"origin":"LON","destination":"BCN","price":120,"transfers":0,
                 "airline":"IB","departure_at":"2026-11-01T06:35:00Z","expires_at":"2026-04-07T12:34:14Z"},
  "2026-11-02": {"price":135,"transfers":1,"airline":"VY","departure_at":"2026-11-02T17:00:00Z"}
}}
```

---

## GET /v1/prices/monthly

Cheapest ticket per month for a route.

**Parameters:** origin, destination, currency, market (no date filters — returns all months).

**Example:**
```python
r = requests.get("https://api.botclaw.ru/v1/prices/monthly",
    params={"origin":"LON","destination":"BCN","currency":"usd"})
```

---

## Reference Data (Static JSON)

No parameters needed. Return arrays of objects.

```python
# Countries
r = requests.get("https://api.botclaw.ru/data/ru/countries.json")
# [{"name":"Russia","cases":{"ro":"России",...},"code":"RU","currency":"RUB","name_translations":{...}}]

# Cities
r = requests.get("https://api.botclaw.ru/data/ru/cities.json")
# [{"name":"Moscow","code":"MOW","time_zone":"Europe/Moscow","country_code":"RU",
#   "coordinates":{"lon":37.617,"lat":55.755}}]

# Airports
r = requests.get("https://api.botclaw.ru/data/ru/airports.json")
# [{"name":"Sheremetyevo","code":"SVO","city_code":"MOW","country_code":"RU",
#   "coordinates":{"lon":37.414,"lat":55.972}}]

# Airlines
r = requests.get("https://api.botclaw.ru/data/ru/airlines.json")
# [{"name":"Aeroflot","alias":"","iata":"SU","icao":"AFL","callsign":"AEROFLOT","country":"Russia"}]
```

---

## Building booking links from Data API responses

Many endpoints return a `link` field (e.g. `/search/MOW1005LED1?t=...`). To create a booking URL:

1. Prepend `https://www.aviasales.com` to the `link` value
2. Convert to a short link via `/short-link`:

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/short-link" \
  --params '{"url":"https://www.aviasales.com/search/MOW1005LED1?t=..."}'
```

If the response has no `link` field (e.g. `/v1/prices/cheap`), build a search URL manually — see [aviasales-links.md](aviasales-links.md).

---

## Notes

- **Market:** Controls which data cache is used. `ru` = aviasales.ru users. Use `us` for US-based searches. Defaults to origin city's market.
- **Currency:** Use 3-letter ISO codes: `usd`, `eur`, `rub`, etc.
- **Caching:** Data is cached for 7 days from user searches. Use for static pages, not real-time pricing.
- **Rate limits (per minute):**

| Endpoint | Limit |
|----------|-------|
| `/aviasales/v3/prices_for_dates` | 600 |
| `/aviasales/v3/grouped_prices` | 600 |
| `/aviasales/v3/get_special_offers` | 600 |
| `/aviasales/v3/get_popular_directions` | 600 |
| `/aviasales/v3/search_by_price_range` | 600 |
| `/aviasales/v3/get_latest_prices` | 300 |
| `/v1/prices/cheap` | 300 |
| `/v1/prices/direct` | 180 |
| `/v1/prices/calendar` | 300 |
| `/v1/prices/monthly` | 60 |
| `/v2/prices/month-matrix` | 300 |
| `/v2/prices/week-matrix` | 60 |
| `/v2/prices/nearest-places-matrix` | 60 |
| `/v2/prices/latest` | 300 |
| `/data/*.json` | 600 |

Response headers `X-Rate-Limit`, `X-Rate-Limit-Remaining`, `X-Rate-Limit-Reset` show current usage. Error 429 if exceeded.
