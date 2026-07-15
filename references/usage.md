# Travel Search CLI usage

The skill talks only to the production MCP endpoint over Streamable HTTP. There is no public `--url` flag and no environment-based endpoint override.

## Commands

```bash
python scripts/travel_search.py list-tools
python scripts/travel_search.py describe <command>
python scripts/travel_search.py <command> --input '<JSON object>'
```

| CLI command | MCP tool |
|-------------|----------|
| `search-tours` | `search_tours` |
| `search-hotels` | `search_hotels` |
| `get-tour-details` | `get_tour_details` |
| `search-flights` | `search_flights` |
| `flight-calendar` | `get_flight_price_calendar` |
| `search-activities` | `search_activities` |
| `list-destinations` | `list_destinations` |

## Input

`--input` must be a single JSON **object**. Arrays, strings, numbers, `null`, and `true`/`false` are rejected.

```bash
python scripts/travel_search.py search-tours --input '{"departure_city":"Москва","country":"Турция","date_from":"2026-09-10","date_to":"2026-09-20","adults":2}'
python scripts/travel_search.py search-flights --input '{"origin":"MOW","destination":"AYT","depart_date":"2026-09-15","adults":1}'
python scripts/travel_search.py search-activities --input '{"city":"Анталья","limit":5}'
```

## Discover schemas

Do not hard-code provider field lists. Ask the live server:

```bash
python scripts/travel_search.py describe search-tours
```

Response shape:

```json
{
  "name": "search_tours",
  "description": "...",
  "inputSchema": { "type": "object", "properties": {} }
}
```

`list-tools` returns all seven CLI names with mapped MCP names and live descriptions.

## Output and exit codes

Every invocation prints exactly one JSON document to stdout (including `-h` / `--help`).

| Code | Meaning |
|------|---------|
| 0 | Success (including useful partial multi-provider results; also help) |
| 2 | Usage or input error |
| 1 | MCP / transport failure |

On failure, stdout is a small JSON object with `error`, `category`, and `message`. Stderr may contain only a short category token. Raw tool-error content is never echoed.

## Result normalization

For tool calls the CLI preserves normalized MCP data:

1. If the tool result has `isError` exactly `true`, fail with a safe error (exit 1) — do not surface `content` / `structuredContent`.
2. Prefer `structuredContent` when present.
3. Else, if the first text content item is a JSON document, decode and return it.
4. Else return the MCP result/content object without inventing fields.

Useful partial multi-provider payloads without `isError: true` remain success (exit 0).

## Agent checklist

- Exact geography, dates, nights, traveler composition, and **budget** are hard constraints.
- Do **not** auto-show above-budget offers. Alternatives outside a hard constraint only after **explicit user consent**, in a **separate labeled section**.
- Unknown child ages → clarify before bookable family prices.
- Hotel-only → `search-hotels`.
- Refresh a chosen tour → `get-tour-details`.
- Missing short booking URL → do not substitute a raw URL.
- Flight prices from search/calendar may be cached — not live tickets.
