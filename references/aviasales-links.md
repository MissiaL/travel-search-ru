# Aviasales Search Links

How to form Aviasales search URLs for booking links.

## URL format

```
https://www.aviasales.ru/search?origin_iata={ORIGIN}&destination_iata={DEST}&depart_date={YYYY-MM-DD}&return_date={YYYY-MM-DD}&adults={N}&children={N}&infants={N}&trip_class=0
```

**Parameters:**

| Parameter | Description | Example |
|-----------|-------------|---------|
| `origin_iata` | Departure city IATA code | `MOW` |
| `destination_iata` | Arrival city IATA code | `AYT` |
| `depart_date` | Departure date (YYYY-MM-DD) | `2026-04-25` |
| `return_date` | Return date (YYYY-MM-DD), omit for one-way | `2026-05-02` |
| `adults` | Number of adults (over 12), 1-9 | `2` |
| `children` | Number of children (2-12), 0-6 | `2` |
| `infants` | Number of infants (under 2), 0-6 | `0` |
| `trip_class` | 0=Economy, 1=Business, 2=First | `0` |
| `oneway` | One-way flag: `1` or `0` | `0` |
| `currency` | Currency: RUB, USD, EUR, UAH, CNY, KZT, AZN, BYN, THB, KGS, UZS | `RUB` |

> Up to 9 seat-occupying passengers (adults + children). Infants travel on laps; their count cannot exceed adults count.

### Examples

**1 adult, one-way:**
```
https://www.aviasales.ru/search?origin_iata=MOW&destination_iata=AYT&depart_date=2026-04-10&adults=1&children=0&infants=0&trip_class=0&oneway=1
```

**2 adults + 2 children, round-trip:**
```
https://www.aviasales.ru/search?origin_iata=MOW&destination_iata=AYT&depart_date=2026-04-25&return_date=2026-05-02&adults=2&children=2&infants=0&trip_class=0
```

## Getting a short booking link

After forming the URL, always get a short link:

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/short-link" \
  --params '{"url":"https://www.aviasales.ru/search?origin_iata=MOW&destination_iata=AYT&depart_date=2026-04-25&return_date=2026-05-02&adults=2&children=2&infants=0&trip_class=0"}'
```

Response: `{"url": "https://aviasales.tpm.lv/XXXXXXXX"}` — give this link to the user.

## Important

- **Always use `www.aviasales.ru/search?...` format** — this is the only format that returns HTTP 200 and correctly preserves all query parameters through the short link service.
- Do NOT use `aviasales.com/searches/new` — it returns HTTP 404.
- Do NOT use `search.aviasales.com/flights/` — short links to that domain lose query parameters.
- Do NOT use the old slug format (`aviasales.ru/search/MOW1004AYT1`) — it does not support children/infants.
