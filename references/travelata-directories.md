# Travelata Directories

Load this file only when you need to look up IDs for countries, resorts, meals, or hotel categories.

All directory endpoints return `{"success": true, "result": [...]}`.

Note: hotel names, ratings, and categories are returned inside search responses (via `sections[]=hotels`) — no need to resolve them separately.

## Countries

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata-partners/directory/countries" \
  --params '{"disabled":"0"}'
```

Each item: `{"id": 92, "name": "Турция", "disabled": false}`. Use `id` as `country` (integer, not array) in search.

Common country IDs:
- Турция: 92
- Египет: 40
- ОАЭ: 47
- Таиланд: 88

## Popular destination countries

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata-partners/directory/destinationCountries"
```

Returns currently popular destinations sorted by `position`.

## Resorts

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata-partners/directory/resorts" \
  --params '{"country[]":["92"],"disabled":"0","limit":"1000"}'
```

Each item: `{"id": 2162, "name": "Белек", "country": 92, "isPopular": true, "disabled": false}`. Use `id` as `resorts[]` in search.

Common Turkey resort IDs:
- Белек: 2162
- Кемер: 3839
- Сиде: 3828
- Аланья: 2159

## Hotels

The public API does not expose standalone hotel search or hotel directory routes.
Hotel names and IDs arrive in `GET /tours` when you pass `sections[]=hotels`.
If the user names a hotel but its ID is unknown, search the requested country/resort,
match the name in that `hotels` section, and then repeat the search with `hotels[]`.

## Departure Cities

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata-partners/directory/departureCities" \
  --params '{"disabled":"0"}'
```

Each item: `{"id": 2, "name": "Москва", "disabled": false}`. Use `id` as `departureCity` (integer) in search. Common: Москва=2, Санкт-Петербург=1.

A static snapshot is also available in [assets/departure-cities.json](../assets/departure-cities.json).

## Hotel Categories

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata-partners/directory/hotelCategories"
```

Each item: `{"id": 7, "name": "5*"}`. Use `id` as `hotelCategories[]` in search.

## Meals

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata-partners/directory/meals"
```

Each item: `{"id": 1, "code": "AI", "name": "Всё включено"}`. Use `id` as `meals[]` in search.

## Operators

There is no standalone operator directory route in the public API. Request
`sections[]=operators` with `GET /tours` to resolve operator IDs returned by search.
