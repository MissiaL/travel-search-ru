# Tour Selection Playbook

Use this only when you already have tour results and need to build a good shortlist.

## Ranking Order

1. Fit to the user's hard constraints: destination, exact area if requested, dates, nights, travelers, budget ceiling
2. Hotel quality: rating, stars, meal plan, beach distance, family fit
3. Price among otherwise similar options

Do not let a cheaper but worse-fit option outrank a clearly better match.

## Exact-Area Requests

- If the user asked for an exact area, search with `resorts[]`.
- Do not throw away tours just because the API returns a more specific child resort or subzone in the response.
- Show the actual subzone in the final answer.
- Do not silently expand to a different resort cluster or region. Ask first.

## Family and Group Shortlists

- Prefer hotels with strong ratings, easier beach access, and room layouts that make sense for the traveler mix.
- If the user asked for "family hotel", explain briefly why the hotel fits: beach, meals, family format, stronger reviews, calmer location.
- If nothing fits perfectly, show the best in-scope options first and then ask whether to widen filters or geography.

## Shortlist Size

- Default to 5–8 hotels, not a giant dump of raw offers.
- One hotel should usually appear only once in the main shortlist.
- Show more only when the user explicitly asks for a longer list or a deeper comparison.

## Compact Output Format

For tours, keep each option short and calm. Prefer sections over decorative markers:

```text
Best options in Kemer

1. Hotel Name, 4*, Kemer / Goynuk
Rating: 4.7
Meal: Ultra all inclusive
Dates: 25 April, 7 nights
Price: from 187 000 RUB
Why it's in the list: strong family reviews, close to beach
Link: <short link>
```
