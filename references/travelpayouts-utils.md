# Travelpayouts Utility APIs

No authentication required for any of these endpoints.

## Autocomplete (cities, airports, countries)

Find IATA codes and city names by text search.

**Endpoint:** `GET https://autocomplete.travelpayouts.com/places2`

**Parameters:**
- `term` (required) — search text (city name, airport name, etc.)
- `locale` — language code: `en`, `ru`, `de`, `fr`, etc. Default: `en`
- `types[]` — filter by type: `city`, `airport`, `country`. Can specify multiple.

**Example:**
```bash
python scripts/api_call.py --method GET \
  --url "https://autocomplete.travelpayouts.com/places2" \
  --params '{"term":"Antalya","locale":"en","types[]":"city"}'
```

**Response:** Array of objects:
```json
[{
  "type": "city",
  "code": "AYT",
  "name": "Antalya",
  "country_code": "TR",
  "country_name": "Turkey",
  "city_code": "AYT",
  "city_name": "Antalya",
  "state_code": null,
  "coordinates": {"lon": 30.7133, "lat": 36.8969},
  "weight": 12345
}]
```

Key fields: `code` (IATA), `name`, `country_code`, `country_name`, `city_code`, `type` (`city`/`airport`/`country`), `weight` (popularity), `coordinates`.

## IATA Resolver (natural language)

Parse natural language travel queries into origin/destination IATA codes. **Russian language only.**

**Endpoint:** `GET https://www.travelpayouts.com/widgets_suggest_params`

**Parameters:**
- `q` — natural language query in Russian (e.g., "из Москвы в Анталью")

**Example:**
```bash
python scripts/api_call.py --method GET \
  --url "https://www.travelpayouts.com/widgets_suggest_params" \
  --params '{"q":"из Москвы в Анталью"}'
```

**Response:**
```json
{"origin": {"iata": "MOW", "name": "Moscow"}, "destination": {"iata": "AYT", "name": "Antalya"}}
```

## Geolocation by IP

Determine the nearest city and airport from an IP address.

**Endpoint:** `GET https://www.travelpayouts.com/whereami`

**Parameters:**
- `locale` — language: `en`, `ru`, etc.
- `ip` — IPv4 or IPv6 address

**Example:**
```bash
python scripts/api_call.py --method GET \
  --url "https://www.travelpayouts.com/whereami" \
  --params '{"locale":"en","ip":"8.8.8.8"}'
```

**Response:** IATA code, city name, country name, coordinates.
