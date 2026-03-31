# Travelata API

Package tours: flight + hotel. Uses the official Travelata API via Travelpayouts.

## Search Endpoint

```text
https://api.botclaw.ru/travelata/statistic/cheapestTours
```

Returns **one cheapest tour per check-in date** with hotel names, ratings, and booking links directly in the response.

## How It Works

- The API returns the single cheapest tour for each day in the date range.
- Not every day will have a result — some dates may have no available tours.
- If the user asks for a specific date (e.g. "May 5"), always search a range of ±7 days around it (e.g. May 1–15) to find nearby options. Never search a single day — it often returns empty.
- The API does NOT support `touristGroup[kidsAges][]` — only the total count of kids. The age of children does not affect search results.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `countries[]` | yes | Country ID. Only ONE country per request |
| `departureCity` | yes | Departure city ID |
| `checkInDateRange[from]` | yes | Check-in date range start (YYYY-MM-DD) |
| `checkInDateRange[to]` | yes | Check-in date range end (YYYY-MM-DD). Max 30 days from `[from]` |
| `nightRange[from]` | yes | Minimum nights |
| `nightRange[to]` | yes | Maximum nights |
| `touristGroup[adults]` | yes | Adults count |
| `touristGroup[kids]` | yes | Children count (2-11 years) |
| `touristGroup[infants]` | yes | Infants count (under 2) |
| `resorts[]` | no | Resort IDs (array). Use for exact area filtering |
| `meals[]` | no | Meal type IDs (array) |
| `hotelCategories[]` | no | Hotel star/category IDs (array) |
| `ratingMin` | no | Minimum hotel rating |
| `ratingMax` | no | Maximum hotel rating |

## Example Request

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata/statistic/cheapestTours" \
  --params '{"countries[]":["92"],"departureCity":"2","nightRange[from]":"7","nightRange[to]":"10","touristGroup[adults]":"2","touristGroup[kids]":"0","touristGroup[infants]":"0","hotelCategories[]":["7","4"],"meals[]":["1","8"],"ratingMin":"4","checkInDateRange[from]":"2026-06-01","checkInDateRange[to]":"2026-06-30"}'
```

## Response Fields

| Field | Description |
|-------|-------------|
| `tourIdentity` | Tour identity (used in booking URL) |
| `price` | Total price in RUB |
| `checkinDate` | Check-in date |
| `nights` | Number of nights |
| `hotelId` | Hotel ID |
| `hotelName` | Hotel name (directly in response) |
| `hotelCategory` | Hotel category ID |
| `hotelCategoryName` | Hotel category as text (e.g. "5*") |
| `hotelRating` | Hotel rating |
| `hotelPreview` | Hotel image URL |
| `mealId` | Meal type ID |
| `resortId` | Resort ID |
| `tourPageUrl` | Direct booking URL (ready to use) |
| `searchPageUrl` | Search results page URL |
| `operatorId` | Tour operator ID |
| `expired` | Offer expiry time |

## Booking Links

`tourPageUrl` is returned directly in the response. Always convert it through `/short-link`:

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/short-link" \
  --params '{"url":"https://travelata.ru/hotel/107259/tourPage?identity=<tourIdentity from response>"}'
```

## Search Strategy

- **Always use a date range**, never a single day. If the user says "May 5", search `checkInDateRange[from]=2026-04-28` to `[to]=2026-05-12`.
- If user says **Turkey**, use `countries[]=92` without `resorts[]`.
- If user says **Antalya** in a tour context, start broad with `countries[]=92` unless they clearly mean only Antalya city.
- If exact area matters, add `resorts[]` with the appropriate resort IDs.
- Default quality filters: `hotelCategories[]` for 4-5 stars, `meals[]` for AI/UAI, `ratingMin=4`.
- Present the best options from the results. Since the API returns one tour per day, show the cheapest 3-5 across the date range and note which check-in dates are available.

If strict filters return 0 results:

1. Retry WITHOUT any filters (no `hotelCategories`, `meals`, `ratingMin`) but keep the same date range and tourist group
2. If still 0, widen the date range
3. Only then say no tours are available

## Key IDs

See [travelata-directories.md](travelata-directories.md) for full directory endpoints.

### Countries
- `92` Turkey, `34` Egypt, `87` Thailand, `69` UAE

### Departure Cities
- `2` Moscow, `1` Saint Petersburg, `3` Yekaterinburg, `4` Novosibirsk, `5` Kazan

### Hotel Categories
- `7` 5*, `8` 5*(HV-1), `4` 4*, `9` 4*(HV-2), `3` 3*, `2` 2*, `1` 1*

### Meals
- `8` UAI, `1` AI, `11` AI without alcohol, `3` FB, `5` HB, `2` BB, `7` RO

### Turkey Resorts
- `2161` Antalya, `3839` Kemer, `3835` Kemer: Beldibi, `2159` Alanya
- `2162` Belek, `3828` Side, `2178` Marmaris, `2163` Bodrum, `2190` Fethiye, `2185` Istanbul
