# Travelata Directories

Load this file only when you need to look up IDs for countries, resorts, meals, or hotel categories.

Note: hotel names and categories are returned directly in search results — no need to resolve them separately.

## Countries

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata/directory/countries"
```

Response: `{"data": [{"id": 92, "name": "Турция", "popular": 1}, ...]}`. Use `id` as `countries[]` in search.

## Resorts

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata/directory/resorts"
```

Response includes `countryId` field — filter locally to find resorts for a specific country. Use `id` as `resorts[]` in search.

## Departure Cities

Available in [assets/departure-cities.json](../assets/departure-cities.json).

## Hotel Categories

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata/directory/hotelCategories"
```

Response: `{"data": [{"id": 7, "name": "5*"}, ...]}`. Use `id` as `hotelCategories[]` in search.

## Meals

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata/directory/meals"
```

Response: `{"data": [{"id": 1, "name": "Всё включено"}, ...]}`. Use `id` as `meals[]` in search.
