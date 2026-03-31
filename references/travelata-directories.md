# Travelata Directories

Load this file only when you need to look up IDs for countries, resorts, meals, or hotel categories.

Note: hotel names and categories are returned directly in search results — no need to resolve them separately.

## Countries

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata/directory/countries"
```

Common values: `92` Turkey, `34` Egypt, `87` Thailand, `69` UAE

## Resorts

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata/directory/resorts"
```

Filter locally by the `countryId` field. Use returned IDs as `resorts[]` in search.

Common Turkey resort IDs:

- `2161` Antalya, `3839` Kemer, `3835` Kemer: Beldibi, `2159` Alanya
- `2162` Belek, `3828` Side, `2178` Marmaris, `2163` Bodrum, `2190` Fethiye, `2185` Istanbul

## Departure Cities

| id | City |
|----|------|
| 1 | Saint Petersburg |
| 2 | Moscow |
| 3 | Yekaterinburg |
| 4 | Novosibirsk |
| 5 | Kazan |

## Hotel Categories

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata/directory/hotelCategories"
```

Common values: `7` 5*, `8` 5*(HV-1), `4` 4*, `9` 4*(HV-2), `3` 3*, `2` 2*, `1` 1*, `5` Apartments, `6` Villa, `22` Boutique hotel

## Meals

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/travelata/directory/meals"
```

Common values: `8` UAI, `1` AI, `11` AI without alcohol, `3` FB, `5` HB, `2` BB, `7` RO
