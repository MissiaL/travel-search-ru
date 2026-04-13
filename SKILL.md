---
name: travel-search-ru
description: Search for flights, tours, and excursions with real prices and booking links. Use when the user asks about travel, flights, airfare, hotels, tours, excursions, vacations, or trip planning.
metadata: {"author":"MissiaL","version":"1.0","keywords":["aviasales","travelata","sputnik8","tripster","flights","tours","excursions","travel","russia","turkey","egypt","booking"]}
---

# Travel Search

Search for flights, tours, and excursions with real prices and booking links.

## Available tools

Run the HTTP client to call APIs:

```bash
python scripts/api_call.py --method GET --url "<URL>" --params '<JSON>'
python scripts/api_call.py --method POST --url "<URL>" --body '<JSON>'
```

`--params`, `--body`, and `--headers` must be valid JSON objects. Do not pass query strings like `a=1&b=2`.

### 1. Flights (Aviasales)

Cached flight prices. Read [references/aviasales-data-api.md](references/aviasales-data-api.md) for all endpoints and parameters.

**Quick example — cheapest flights:**
```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/v1/prices/cheap" \
  --params '{"origin":"MOW","destination":"AYT","depart_date":"2026-06","currency":"rub"}'
```

After getting prices, create a booking link on aviasales.ru. See [references/aviasales-links.md](references/aviasales-links.md) for URL format, then get a short link:
```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/short-link" \
  --params '{"url":"https://www.aviasales.ru/search?origin_iata=MOW&destination_iata=AYT&depart_date=2026-06-01&return_date=2026-06-15&adults=1&children=0&infants=0&trip_class=0"}'
```

### 2. Tours (Travelata)

Package tours (flight + hotel). Real-time search with multiple tours per date, kids' ages, and search by specific hotel. Read [references/travelata-api.md](references/travelata-api.md) for the full flow and parameters. Use [references/travelata-directories.md](references/travelata-directories.md) only if you need to look up IDs.

**Two-step flow:** start an async search, wait ~2 seconds, then fetch tours. Use the **same criteria** in both calls.

**Step 1 — start search:**
```bash
python scripts/api_call.py --method POST \
  --url "https://api.botclaw.ru/travelata-partners/tours/asyncSearch" \
  --body '{"departureCity":2,"country":92,"checkInDateRange":{"from":"2026-06-08","to":"2026-06-22"},"nightRange":{"from":"7","to":"10"},"touristGroup":{"adults":2,"kids":1,"infants":0,"kidsAges":[8]},"hotelCategories":[4,7],"meals":[1,8]}'
```

**Step 2 — fetch tours** (same criteria; pass arrays as `key[]`):
```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata-partners/tours" \
  --params '{"departureCity":"2","country":"92","checkInDateRange[from]":"2026-06-08","checkInDateRange[to]":"2026-06-22","nightRange[from]":"7","nightRange[to]":"10","touristGroup[adults]":"2","touristGroup[kids]":"1","touristGroup[infants]":"0","touristGroup[kidsAges][]":["8"],"hotelCategories[]":["4","7"],"meals[]":["1","8"],"sections[]":["hotels","meals"],"limit":"30"}'
```

The response has `tours[]` with `id`, `price`, `checkInDate`, `hotel` (id), `meal` (id), `hotelCategory` (id). Resolve names via the `hotels` and `meals` sections in the same response.

**Build the booking URL** from `tour.hotel` and `tour.id`, then convert through `/short-link`:
```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/short-link" \
  --params '{"url":"https://travelata.ru/hotel/<tour.hotel>/tourPage?identity=<tour.id>"}'
```

**Important:** always pass `kidsAges` when `kids > 0`. Always search a date range, never a single day. If filters return 0 results, retry without filters first, then widen the date range.

### 3. Excursions (Sputnik8)

Read [references/sputnik8-api.md](references/sputnik8-api.md) for endpoints.

**Quick example — excursions in Kemer:**
```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/sputnik8/v1/products" \
  --params '{"city_id":"420","limit":"10","lang":"ru","currency":"rub","order":"rating","order_type":"desc"}'
```

### 4. Utilities

- **City/airport lookup:** [references/travelpayouts-utils.md](references/travelpayouts-utils.md) — autocomplete and IATA resolver
- **Short links:** `GET https://api.botclaw.ru/short-link?url=<URL>` — get a short booking link for any travel URL
- **Airline logos:** `http://pics.avs.io/{width}/{height}/{IATA}.png` (e.g. `http://pics.avs.io/200/200/SU.png`)
- **Currency rates to RUB:** `GET http://yasen.aviasales.ru/adaptors/currency.json`

## Workflow

1. **Resolve locations** — if user says city names, use the autocomplete or IATA resolver to get IATA codes (for flights). For tours, resolve the country first. Only narrow to a specific Travelata resort when the user explicitly asks for an exact area such as Kemer, Belek, Side, or Alanya. For package-tour requests like "Antalya", start broad with Turkey (`country=92`) because users often mean the Antalya coast, not only the exact municipality.
2. **Search** — call the appropriate API(s) based on user request
3. **Get short links** — convert result URLs via `api.botclaw.ru/short-link`
4. **Present results** — show prices, hotel names, ratings, and booking links

## Rules

- **ALWAYS** convert ALL URLs to short links via `/short-link` before showing to users — this applies to Aviasales, Travelata, AND Sputnik8 links. Never show raw URLs from API responses directly.
- For flights: show cached prices from Data API + link to full search on aviasales.ru
- For tours: default to 4-5 star, all-inclusive. Always search a date range (±7 days from requested date), never a single day. Show hotel name, stars, meal, price, check-in date, and booking link. Group multiple tours of the same hotel together — show the cheapest 5–10 hotels rather than 5–10 raw tours.
- For tours: anyone aged 2–17 goes into `touristGroup.kids` (not adults). Always pass `touristGroup.kidsAges[]` with the age of each child — without it the API silently defaults to age 11 and may return wrong room layouts. If the user gives count but not ages, pick a sensible default (e.g. 8) and tell the user you assumed it.
- For tours: if strict filters return 0, retry WITHOUT filters first (same dates and tourists), then widen the night range, then the date range. Only say "no tours" if the unfiltered search is also empty.
- For tours: search by specific hotel using `hotels[]` when the user names a hotel.
- For tours: if results are few (under 3) or none match the user's preferences well, recommend checking more options on these services:
  - [Яндекс Путешествия](https://yandex.tpm.lv/6B8T7GjP)
  - [Ostrovok](https://ostrovok.tpm.lv/LjsjLi2L)
  - [Level.travel](https://level.tpm.lv/NBoUxZ6p)
- For tours with a budget: if results exceed budget, present the cheapest options clearly marked as "above budget".
- For tours with an exact area request: pass `resorts[]` (array format). Verify the returned `resort` field in each tour matches the requested ID.
- For combined requests (flights + tours): search both and compare
- Prices from Data API are cached (2-7 days old) — mention this to users. If no data found for requested dates, the API automatically returns nearest available dates.
- When user asks for tours plus excursions, always search Sputnik8 too, even if tour results are empty or only slightly above budget.
- When showing flight or tour results, suggest searching for activities and excursions at the destination via Sputnik8 (e.g. "Want me to find excursions and things to do in Antalya?")
