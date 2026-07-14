---
name: travel-search-ru
description: Search flights via Aviasales, tours via Travelata + Level.Travel, and excursions via Sputnik8 with real prices and booking links. Use when the user asks about travel, flights, airfare, hotels, tours, excursions, vacations, or trip planning.
metadata: {"author":"MissiaL","version":"1.3.0","keywords":["aviasales","travelata","leveltravel","sputnik8","tripster","flights","tours","excursions","travel","russia","turkey","egypt","booking"]}
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

## Scope

- This skill finds flights, tours, and excursions, compares options, and returns booking links.
- This skill does **not** make bookings, store personal travel data, access email/calendar, or maintain a long-term travel workspace.
- For exact-area tour requests, keep the requested geography unless the user explicitly agrees to broaden it.

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

### 2. Tours (Travelata + Level.Travel)

Package tours (flight + hotel). Real-time search from **both** Travelata and Level.Travel — same tier, every tour request. Multiple tours per date, kids' ages, meal filters (Travelata server-side; Level.Travel via `pansion_prices` in results), and search by specific hotel. Read [references/travelata-api.md](references/travelata-api.md) and [references/leveltravel-api.md](references/leveltravel-api.md) for full flows and parameters. Use [references/travelata-directories.md](references/travelata-directories.md) only if you need to look up Travelata IDs. Use [references/tour-selection-playbook.md](references/tour-selection-playbook.md) when you need to rank, group, and present a shortlist cleanly.

**On any tour request, start both async searches in one step**, wait once, then fetch both result sets and merge. Label which source each hotel/tour came from.

**Two-step flow (Travelata):** start an async search, wait, then fetch tours. Use the **same criteria** in both calls.

- **Wait 3 seconds** for nearby destinations (Turkey, Egypt, UAE, Cyprus, Greece)
- **Wait 5 seconds** for far destinations (Vietnam, Thailand, Bali/Indonesia, Cuba, Dominican Republic, Maldives, Mexico) — operators take longer
- **If the first fetch returns fewer than ~30 tours, wait another 3 seconds and re-fetch with the SAME parameters** before trying anything else. Operators stream results into the same search; the second fetch usually picks up the rest. This is the most important fix for empty results on far destinations.

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

**Important:** always pass `kidsAges` when `kids > 0`. Always search a date range, never a single day. If filters return 0 results, the first thing to try is **re-fetching `GET /tours` with the same parameters after another 3-second wait** — most empty results on far destinations are caused by operators not having responded yet, NOT by overly strict filters. Only after the second fetch is still empty should you drop filters or widen dates.

#### Level.Travel

Full live async tour search (flight+hotel or hotel-only). Same tier as Travelata: on **any** tour request, start Level.Travel enqueue **together with** Travelata `asyncSearch`, wait once (use the longer wait if they differ — Level.Travel needs ~7 s nearby / ~10 s far), then fetch both result sets and merge. Label each option with its source.

See [references/leveltravel-api.md](references/leveltravel-api.md) for endpoints, parameters, response shape, departure cities, and link construction.

**Quick example — enqueue, then fetch hotels:**
```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/leveltravel/search/enqueue" \
  --params '{"from_city":"Moscow","to_country":"TR","adults":"2","start_date":"28.07.2026","nights":"7..9","kids":"0"}'
```
```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/leveltravel/search/get_grouped_hotels" \
  --params '{"request_id":"<request_id>","limit":"15"}'
```

**Notes:** enqueue `start_date` is **DD.MM.YYYY**; site booking links use **YYYY-MM-DD** for `start_date`. Always pass `kids` + `kids_ages[]` when kids > 0. Pass `limit=10..20` on `get_grouped_hotels`. Meal/board is chosen client-side from each hotel's `pansion_prices` keys (no meal param on enqueue). Build `https://level.travel{hotel.link}?start_date=YYYY-MM-DD&nights=N&adults=N`, then convert every link through `/short-link` before showing it.

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

- **ALWAYS** convert ALL URLs to short links via `/short-link` before showing to users — this applies to Aviasales, Travelata, Level.Travel, AND Sputnik8 links. Never show raw URLs from API responses directly.
- For flights: show cached prices from Data API + link to full search on aviasales.ru
- For tours: default to 4-5 star, all-inclusive. Always search a date range (±7 days from requested date), never a single day. Show hotel name, stars, meal, price, check-in date, and booking link. Group multiple tours of the same hotel together — show the cheapest 5–10 hotels rather than 5–10 raw tours.
- For tours: anyone aged 2–17 goes into `touristGroup.kids` (not adults). Always pass `touristGroup.kidsAges[]` with the age of each child — without it the API silently defaults to age 11 and may return wrong room layouts. If the user gives count but not ages, pick a sensible default (e.g. 8) and tell the user you assumed it.
- For tours: if a search returns 0 (or under ~30 results for popular routes), the FIRST retry must be a second `GET /tours` with the same parameters after waiting another 3 seconds — operators may not have answered yet, especially for Vietnam, Cuba, Dominican Republic, Bali, Maldives. Only AFTER that second fetch is still empty should you drop filters, then widen night range, then widen date range. Do not blast through retries — each is a separate API call.
- For tours: search by specific hotel using `hotels[]` when the user names a hotel.
- For tours: if results are few (under 3) or none match the user's preferences well, recommend checking more options on these services:
  - [Яндекс Путешествия](https://yandex.tpm.lv/6B8T7GjP)
  - [Ostrovok](https://ostrovok.tpm.lv/LjsjLi2L)
- For tours with a budget: if results exceed budget, present the cheapest options clearly marked as "above budget".
- For tours with an exact area request: pass `resorts[]` (array format). Treat the returned tours as valid area matches even when the API returns a more specific child resort/subzone inside that area. Show the actual subzone in the response, but do **not** silently broaden to a different resort cluster or region unless the user agrees.
- For combined requests (flights + tours): search both and compare
- Prices from Data API are cached (2-7 days old) — mention this to users. If no data found for requested dates, the API automatically returns nearest available dates.
- When user asks for tours plus excursions, always search Sputnik8 too, even if tour results are empty or only slightly above budget.
- When showing flight or tour results, suggest searching for activities and excursions at the destination via Sputnik8 (e.g. "Want me to find excursions and things to do in Antalya?")
- For tours: always start both Travelata (`POST asyncSearch`) and Level.Travel (`GET search/enqueue`) on any tour request, wait once (longer of the two waits if they differ), then fetch both (`GET /tours` and `GET search/get_grouped_hotels`). Present merged results and label each hotel/tour with its source.

## Presentation Rules

- Keep answers compact and easy to scan: by default, show 5–8 strong options, then a short conclusion about which option fits best and why. Show more only if the user asks.
- Prefer a calm text layout over decorative formatting. Do not use a colorful emoji-heavy line-by-line style.
- For flights, show 5–8 options by default. Prefer this order inside each option: route, dates, price, baggage or fare notes if available, direct or with transfers, then booking link.
- For tours, show 5–8 hotels by default, not 5–8 raw duplicate offers. If the same hotel has multiple offers, show the cheapest relevant one unless the user asks to compare variants.
- For tours, prefer this order inside each option: hotel, stars, actual resort/subzone, rating, meal, check-in and nights, price, short "Why it's in the list" note, then booking link.
- If there is a clear geographic split, separate the answer into sections such as `Best options in Kemer` and `If you expand beyond Kemer`. Do not mix them into one flat list.
