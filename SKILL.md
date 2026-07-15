---
name: travel-search-ru
description: Search package tours, hotels, flights, and activities via the travel MCP endpoint with real prices and booking links. Use when the user asks about travel, flights, airfare, hotels, tours, excursions, vacations, or trip planning.
metadata: {"author":"MissiaL","version":"2.0.0","keywords":["travel","flights","tours","hotels","excursions","mcp","russia","turkey","egypt","booking"]}
---

# Travel Search

Search tours, hotels, flights, and activities through a single MCP-backed CLI.

## CLI

```bash
python scripts/travel_search.py <command> --input '<JSON object>'
python scripts/travel_search.py describe <command>
python scripts/travel_search.py list-tools
```

Commands: `search-tours`, `search-hotels`, `get-tour-details`, `search-flights`, `flight-calendar`, `search-activities`, `list-destinations`.

Current tool schemas change over time. **Always** run `describe <command>` before a new parameter shape; do not invent fields from memory. See [references/usage.md](references/usage.md).

## Examples

```bash
python scripts/travel_search.py search-tours --input '{"departure_city":"Москва","country":"Турция","date_from":"2026-09-10","date_to":"2026-09-20","adults":2}'
python scripts/travel_search.py search-flights --input '{"origin":"MOW","destination":"AYT","depart_date":"2026-09-15","adults":1}'
python scripts/travel_search.py search-activities --input '{"city":"Анталья","limit":5}'
```

## Scope

- Finds package tours, hotel-only stays, flights, activities, and destination directories; returns prices and booking links when the server provides them.
- Does **not** make bookings, store personal travel data, access email/calendar, or keep a long-term travel workspace.
- Exact geography stays fixed unless the user explicitly agrees to broaden it.

## Hard constraints

Treat these as non-negotiable filters — do not silently relax them:

- Geography (country, resort, city, hotel when named)
- Dates and night range
- Traveler composition (adults, children, infants)
- Budget when stated

If children are in the party and ages are unknown, **ask for ages** before presenting bookable family prices. Do not invent ages for pricing.

**Budget:** never auto-show offers that break a hard budget. Alternatives outside any hard constraint may appear only after **explicit user consent**, and only in a **separate labeled section**.

## When to use which command

| Need | Command |
|------|---------|
| Package tour (flight + hotel) | `search-tours` |
| Hotel only (no flight) | `search-hotels` |
| Fresh price/availability before booking a tour | `get-tour-details` |
| Flight options | `search-flights` |
| Flight price calendar / flexible dates | `flight-calendar` |
| Excursions and activities | `search-activities` |
| Resolve destinations / directories | `list-destinations` |

## Workflow

1. Clarify hard constraints (place, dates/nights, travelers, budget).
2. Resolve ambiguous places with `list-destinations` when needed.
3. `describe` the command you will call; build `--input` as one JSON object.
4. Call the command; preserve partial multi-provider results as success.
5. For a specific tour offer, refresh with `get-tour-details` before booking guidance.
6. Present a short shortlist with prices, key facts, and links the server returned.

## Rules

- **Hotel-only** requests use `search-hotels`, not package `search-tours`.
- **Fresh details** for a chosen tour use `get-tour-details`; do not reuse stale offer payloads as live quotes.
- Prefer **short booking URLs** from the response. If a short URL is missing, **never** fall back to a raw/long provider URL.
- **Cached flight prices** (including calendar data) are not live quotes — say they may be outdated.
- Keep the requested geography; show actual sub-area names without switching regions silently.
- Default presentation: 5–8 strong options, calm text layout, group tours by hotel when multiple offers share one property.
- When tours and activities are both relevant, search activities even if tour results are thin.

## Presentation

- Flights: route, dates, price, transfers/baggage notes if present, then link.
- Tours/hotels: property, stars/rating, area, meal, check-in and nights, price, brief fit note, then link.
- Prefer short conclusions over long tables.
