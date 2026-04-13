# Level.Travel API

Package tours from a cached snapshot source. Use it in parallel with Travelata
only when the user's query fits Level.Travel's hard scope limits.

Level.Travel is a minimum-price snapshot refreshed every few hours. It is not a
live search API. Responses come back quickly because they read from a prepared
index. When you show Level.Travel results, mention `feed_age_hours` so the user
understands how fresh the snapshot is.

## Scope

Level.Travel accepts:

- Exactly 2 adults, 0 kids, 0 infants
- 7 to 15 nights inclusive
- Check-in within roughly the next 30 days
- Any supported departure key from `assets/leveltravel-departure-cities.json`

Level.Travel does not support:

- Families with kids or infants
- Solo travelers
- 3 or more adults
- Trips shorter than 7 nights or longer than 15 nights
- Far-future dates
- Strict meal-plan filtering, because the feed has no meal field

When a query does not fit this scope, skip Level.Travel silently and use
Travelata only. Do not explain tool-selection logic to the user.

## Decision Table

| User query | Level.Travel | Travelata |
|---|---|---|
| 2 adults, 7-14 nights, next month | Yes, in parallel | Yes, in parallel |
| 2 adults and 1 child | No | Yes |
| 1 adult | No | Yes |
| 3+ adults | No | Yes |
| Strict all-inclusive only | No, feed has no meal field | Yes |
| Tour shorter than 7 nights | No | Yes |
| Tour for 5+ months out | No | Yes |
| Specific hotel by name | Yes, with `hotel_name` | Yes, with `hotels[]` |
| Ski tours in Russia | Yes, use `departure_key=ski` | Yes, but inventory may differ |

## Endpoint

```text
GET https://api.botclaw.ru/leveltravel/tours
```

| Param | Type | Required | Example | Notes |
|---|---|---|---|---|
| `departure_key` | string | yes | `moscow` | Must exist in `assets/leveltravel-departure-cities.json` |
| `country_iso2` | string | no | `TR` | Destination country ISO2 |
| `region` | string | no | `Кемер` | Exact match on Russian region name |
| `departure_city` | string | no | `Москва` | Mainly for `departure_key=ski` |
| `date_from` | ISO date | no | `2026-05-01` | Lower bound on check-in |
| `date_to` | ISO date | no | `2026-05-15` | Upper bound on check-in |
| `nights_min` | int | no | `7` | Must be in 7..15 |
| `nights_max` | int | no | `10` | Must be in 7..15 |
| `stars_min` | int | no | `4` | 1..5, excludes unknown stars |
| `price_max` | int | no | `250000` | Rubles |
| `hotel_name` | string | no | `Rixos` | Case-insensitive substring search |
| `beach_line` | int | no | `1` | `1` means first line |
| `limit` | int | no | `20` | 1..100, default 20 |
| `sort` | enum | no | `price` | `price`, `cashback`, or `check_in` |

Do not send `adults`, `kids`, `infants`, or other family-composition params. If
the request needs those, use Travelata instead.

## Response Shape

```json
{
  "source": "leveltravel",
  "feed_synced_at": "2026-04-13T16:40:00Z",
  "feed_age_hours": 3,
  "total_matched": 127,
  "returned": 20,
  "note": "Level.Travel prices come from a cached snapshot; meal info is not available.",
  "results": [
    {
      "hotel": { "name": "Malibu Garden Resort", "stars": 3 },
      "location": { "country_iso2": "TR", "country_ru": "Турция", "region_ru": "Кемер" },
      "departure": { "key": "moscow", "city_ru": "Москва" },
      "tour": {
        "check_in": "2026-05-16",
        "nights": 8,
        "price_rub": 250524,
        "cashback_rub": 5010,
        "operator": "Level.Travel"
      },
      "features": {
        "beach_type": "PUBLIC",
        "beach_surface": "PEBBLE",
        "beach_line": 1,
        "airport_distance_m": 56000,
        "ski_lift_distance_m": null,
        "has_wifi": true,
        "has_parking": true
      },
      "hotel_url": "https://level.travel/hotels/9206953-Malibu_Garden_Resort?..."
    }
  ]
}
```

If `feed_age_hours` is greater than 12, say explicitly that the Level.Travel
snapshot is stale. If `total_matched` is much larger than `returned`, tell the
user you showed the best subset and can expand it.

## Parallel Call Pattern

Start the Travelata async search and the Level.Travel query at the same time.
Level.Travel returns quickly; Travelata needs its usual wait before `GET /tours`.

```bash
python scripts/api_call.py --method POST \
  --url "https://api.botclaw.ru/travelata-partners/tours/asyncSearch" \
  --body '{"departureCity":2,"country":92,"checkInDateRange":{"from":"2026-05-01","to":"2026-05-15"},"nightRange":{"from":"7","to":"10"},"touristGroup":{"adults":2,"kids":0,"infants":0}}'

python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/leveltravel/tours" \
  --params '{"departure_key":"moscow","country_iso2":"TR","date_from":"2026-05-01","date_to":"2026-05-15","nights_min":"7","nights_max":"10","stars_min":"4","limit":"20"}'
```

Merge both result sets in the final answer and label the source of each tour.
If the query falls outside Level.Travel scope, do not make the second call.

## URL Shortening

Every `hotel_url` from Level.Travel must go through `/short-link` before you show
it to the user.

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/short-link" \
  --params '{"url":"https://level.travel/hotels/9206953-Malibu_Garden_Resort?..."}'
```

## Departure Keys

See `assets/leveltravel-departure-cities.json` for the full list of supported
departure keys. The file currently contains 63 entries aligned with the current
`leveltravel_feed.FEEDS` list.

`ski` is a special slice, not a city. It contains Russian ski-resort offers from
many departure cities. For a query like "горнолыжка из Москвы", use
`departure_key=ski&departure_city=Москва`.
