# Travelata API

Package tours: flight + hotel. Real-time search via the Travelata live tour API.

## Endpoints

```text
POST  https://api.botclaw.ru/travelata-partners/tours/asyncSearch
GET   https://api.botclaw.ru/travelata-partners/tours/asyncSearch/{id}
GET   https://api.botclaw.ru/travelata-partners/tours
GET   https://api.botclaw.ru/travelata-partners/tours/{tourId}
PATCH https://api.botclaw.ru/travelata-partners/tours/{tourId}
```

Results are live, not cached. Supports many tours per date, filtering by specific hotels, and kids' ages.

## Search Flow

1. **Start async search** with `POST /tours/asyncSearch` — returns a search `id`.
2. **Wait** before fetching:
   - Close destinations (Turkey, Egypt, UAE, Cyprus, Greece): ~3 seconds
   - Far destinations (Vietnam, Thailand, Indonesia/Bali, Cuba, Dominican Republic, Maldives, Mexico): ~5 seconds
   - When in doubt, use 5 seconds — operators take longer for long-haul tours
3. **Fetch tours** with `GET /tours` using the same criteria.
4. **If you got fewer than ~30 tours,** wait another 3 seconds and re-fetch with the same parameters. The first fetch may have arrived before all tour operators responded — results from later operators show up on subsequent fetches without restarting the search. This is "soft polling": cheaper than the dedicated polling endpoint, and it gives the operators time to finish.

Only after a second fetch returns the same low/empty result should you start relaxing filters — see "Search Strategy" below.

Do not use the dedicated `GET /tours/asyncSearch/{id}` polling endpoint in normal flow — it eats rate limit without giving you the tours, and a re-fetch of `GET /tours` already does the job.

### Step 1 — start search

```bash
python scripts/api_call.py --method POST \
  --url "https://api.botclaw.ru/travelata-partners/tours/asyncSearch" \
  --body '{"departureCity":2,"country":92,"checkInDateRange":{"from":"2026-04-20","to":"2026-04-30"},"nightRange":{"from":"7","to":"10"},"touristGroup":{"adults":4,"kids":1,"infants":0,"kidsAges":[8]},"resorts":[2162]}'
```

Returns: `{"success":true,"result":{"id":"smartsearch_..."}}`. You can ignore the id if you don't poll.

### Step 2 — fetch tours

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata-partners/tours" \
  --params '{"departureCity":"2","country":"92","checkInDateRange[from]":"2026-04-20","checkInDateRange[to]":"2026-04-30","nightRange[from]":"7","nightRange[to]":"10","touristGroup[adults]":"4","touristGroup[kids]":"1","touristGroup[infants]":"0","touristGroup[kidsAges][]":["8"],"resorts[]":["2162"],"sections[]":["hotels","meals"],"limit":"30"}'
```

**Use the same criteria in asyncSearch and GET /tours** — otherwise results may be empty or partial.

## Search Parameters (POST asyncSearch and GET /tours)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `departureCity` | int | yes | Departure city ID (e.g. Moscow = 2) |
| `country` | int | yes | Country ID. One country per request |
| `checkInDateRange.from` | string | yes | Check-in range start (YYYY-MM-DD) |
| `checkInDateRange.to` | string | yes | Check-in range end (YYYY-MM-DD) |
| `nightRange.from` | int | yes | Minimum nights |
| `nightRange.to` | int | yes | Maximum nights |
| `touristGroup.adults` | int | yes | Adults (18+ years). Supports 4+ in a single search |
| `touristGroup.kids` | int | yes | Children — anyone aged 2 through 17 inclusive (NOT just 2–11) |
| `touristGroup.infants` | int | yes | Infants (under 2 years old at tour end) |
| `touristGroup.kidsAges` | int array | **always when kids > 0** | Age of each child at tour end. Critical: omitting this defaults every child to 11, which breaks room placement and extra-bed pricing |
| `priceRange.from` | int | no | Minimum price (RUB) |
| `priceRange.to` | int | no | Maximum price (RUB) |
| `resorts[]` | int array | no | Resort IDs |
| `hotels[]` | int array | no | Hotel IDs — search a specific hotel or set of hotels |
| `meals[]` | int array | no | Meal type IDs |
| `hotelCategories[]` | int array | no | Hotel category (star) IDs |
| `operators[]` | int array | no | Tour operator IDs |
| `sections[]` | string array | GET only | Extra lookups in response — pass the names you need |
| `limit` | int | GET only | Max tours in response. Default 500, max 3000 |

### How to pass arrays via api_call.py

For GET: use bracketed keys with array values — `api_call.py` uses `doseq=True`.

```json
{
  "resorts[]": ["2162"],
  "hotels[]": ["47624","105637"],
  "touristGroup[kidsAges][]": ["8","5"],
  "sections[]": ["hotels","meals"]
}
```

For POST (body is JSON), use native arrays:

```json
{
  "resorts": [2162],
  "hotels": [47624, 105637],
  "touristGroup": {"adults": 4, "kids": 1, "infants": 0, "kidsAges": [8]}
}
```

### Useful `sections` values

- `hotels` — names, photos, ratings, stars, beach distance, description
- `meals` — meal type names
- `hotelCategories` — category names ("5*", "4*", etc.)
- `operators` — tour operator names
- `routes`, `airlines`, `airports`, `rooms` — flight legs, room details

Include only the sections you actually need — smaller sections = faster response.

## Response Shape

`GET /tours` returns `{"success":true,"result":{"tours":[...], "hotels":[...], "meals":[...]}}`.

Each element of `tours` has:

| Field | Description |
|-------|-------------|
| `id` | Tour ID (used to build the booking URL) |
| `price` | Price in RUB |
| `oilTax` | Fuel surcharge (added to `price`) |
| `nights.hotel` | Nights in hotel |
| `nights.tour` | Total tour nights (incl. flight) |
| `checkInDate` | Check-in date |
| `hotel` | Hotel ID — resolve via `sections[]=hotels` |
| `hotelCategory` | Hotel category (star) ID |
| `meal` | Meal type ID |
| `resort` | Resort ID |
| `operator` | Tour operator ID |
| `room` | Room name (string) |
| `transfer` | `none`, `group`, or `individual` — see caveat below |
| `flightType` | `regular` or `charter` |
| `medicalInsurance` | Whether basic insurance is included |

**Transfer caveat:** for some operators (notably the one with `operator=26`) the `transfer` value at the search stage is a prediction based on historical data, not the operator's real answer. The real value only arrives after a `PATCH /tours/{id}` actualization. Don't promise a specific transfer type to the user before actualization — phrase it as "usually included" or "typically group transfer".

The `hotels` section (when requested) gives you `id → {name, rating, cover, distances.beach, description, ...}`.

## Booking Links

The API does NOT return a ready URL. Construct it yourself from `tour.hotel` and `tour.id`:

```text
https://travelata.ru/hotel/{hotel}/tourPage?identity={tour.id}
```

Always convert through `/short-link`:

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/short-link" \
  --params '{"url":"https://travelata.ru/hotel/47624/tourPage?identity=<tour.id>"}'
```

## Search Strategy

- **Always search a date range**, never a single day. If the user says "May 5", use `checkInDateRange[from]=2026-04-28` to `[to]=2026-05-12`.
- **Country first, resort second.** If the user says "Turkey", use `country=92` without `resorts[]`. Add `resorts[]` only when the user explicitly names a resort (Belek, Kemer, Side, Alanya).
- **Broaden night range** — `{"from":"7","to":"10"}` is more forgiving than a strict 7.
- **Default quality filters** for casual queries: `hotelCategories[]` for 4–5 stars, `meals[]` for all-inclusive or ultra-all-inclusive. Drop filters if empty.
- **Always pass `kidsAges`** when `kids > 0`. The API silently defaults missing ages to 11, which produces wrong room placements and extra-bed pricing. Anyone aged 2–17 goes into `kids` (not just 2–11). If the user says "two kids, 5 and 14", that is `kids=2, kidsAges=[5,14]`. If the user only gives the count, pick a sensible default (e.g. `[8]` for one child, `[8,5]` for two) and note it in the response: "I'm searching with kids aged 8 — if their actual ages are different, let me know and I'll re-search."
- **Sort by price client-side** — results come unordered; present the cheapest 5–10 to the user.
- **Group by hotel** when showing many tours — the same hotel often has multiple price points.

If a filtered search returns 0 results, do NOT immediately relax filters. The cause is often that operators haven't responded yet, especially for far destinations. Try in this order:

1. **Wait 3 more seconds and re-fetch `GET /tours` with the same criteria.** No new asyncSearch — operators stream results into the same search. This step alone fixes most empty-result cases for Vietnam, Cuba, Dominican Republic, Bali, etc.
2. If still empty: drop `hotelCategories`, `meals`, `priceRange` — keep dates and tourist group
3. Widen `nightRange` (e.g. 7–14 instead of 7–7)
4. Widen `checkInDateRange` (e.g. ±10 days instead of ±7)
5. Only after all of the above tell the user no tours are available

Each step also costs a request against the 30/min rate limit on the demo account, so be deliberate — don't blast through all 4 steps in 2 seconds.

## Searching a Specific Hotel

Pass `hotels[]` with the hotel ID:

```json
{
  "hotels[]": ["47624"],
  "departureCity": "2",
  "country": "92",
  "checkInDateRange[from]": "2026-04-20",
  "checkInDateRange[to]": "2026-04-30",
  "nightRange[from]": "7",
  "nightRange[to]": "14",
  "touristGroup[adults]": "4",
  "touristGroup[kids]": "1",
  "touristGroup[infants]": "0",
  "touristGroup[kidsAges][]": ["8"],
  "sections[]": ["hotels"]
}
```

Still do `POST asyncSearch` first with the same `hotels` filter, wait ~2 seconds, then `GET /tours`.

## Tour Actualization (before booking)

Before sending the user to a booking link, you can refresh price and flights via:

```bash
python scripts/api_call.py --method PATCH \
  --url "https://api.botclaw.ru/travelata-partners/tours/<tour.id>"
```

This can take up to 60 seconds — only use when the user is about to book, not during listing.

## Directory Lookups

See [travelata-directories.md](travelata-directories.md) for countries, resorts, meals, and hotel category IDs.
