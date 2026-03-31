# Sputnik8 API

Search and browse excursions, tours, tickets, and transfers via the Sputnik8 API. Base URL: `https://api.botclaw.ru/sputnik8`.

Authentication is handled by the proxy — no credentials needed.

---

## Endpoints

### List products (excursions)

`GET /sputnik8/v1/products`

Returns a paginated array of available excursions, tours, tickets, and transfers.

**Parameters:**

| Parameter | Description |
|-----------|-------------|
| `lang` | Language: `ru`, `en` (default: `ru`) |
| `page` | Page number (default: `1`) |
| `limit` | Items per page (default: `50`, max: `100`) |
| `city_id` | Filter by city ID |
| `country_id` | Filter by country ID |
| `region_id` | Filter by region ID |
| `category_id` | Filter by category ID |
| `category_slug` | Filter by category slug |
| `currency` | Currency: `rub`, `usd`, `eur`, `uah` |
| `order` | Sort by: `product_id`, `rating` |
| `order_type` | Sort direction: `asc`, `desc` |

**Example:**

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/sputnik8/v1/products" \
  --params '{"city_id":"420","limit":"10","lang":"ru","currency":"rub","order":"rating","order_type":"desc"}'
```

**Key response fields per product:**

| Field | Description |
|-------|-------------|
| `id` | Product ID |
| `title` | Product name |
| `activity_type` | Type: `tour`, `entry_ticket`, `transfer`, `composite_activity` |
| `price` | Formatted price string (e.g. `"39.00 $"`) |
| `netto_price` | Net price string |
| `currency` | Currency code |
| `customers_review_rating` | Average rating (0–5) |
| `reviews` | Total review count |
| `reviews_with_text` | Reviews with text count |
| `url` | Sputnik8 page URL (convert via `/short-link` before showing to user) |
| `available_for_booking` | `true` if accepting bookings |
| `geo.city.name` | City name |
| `geo.country.name` | Country name |
| `host.name` | Guide/company name |
| `photos` | Array of photo objects |

---

### Get product details

`GET /sputnik8/v1/products/{id}`

Returns extended information about a single product.

**Parameters:** `lang`, `currency`

**Additional response fields:**

| Field | Description |
|-------|-------------|
| `description` | Full description |
| `duration` | Duration object (`value`, `type`, `name`) |
| `begin_place` | Meeting point address |
| `finish_point` | End point |
| `pay_type` | Payment type: `post_pay`, `deposit`, `full_pay` |
| `schedule_type` | Schedule type |
| `order_options` | Array of ticket types with pricing |
| `order_options[].order_lines[].price` | Numeric price |
| `order_options[].order_lines[].all_prices` | Prices in all currencies (RUB, USD, EUR, etc.) |
| `order_options[].order_lines[].price_per` | Price unit (e.g. `"за человека"`) |
| `order_options[].duration` | Duration for this option |
| `order_options[].schedule` | Schedule info |
| `last_events` | Upcoming dates with capacity |

**Example:**

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/sputnik8/v1/products/36404" \
  --params '{"lang":"ru","currency":"rub"}'
```

---

### Unavailable products

`GET /sputnik8/v1/products/not_available`

Returns array of product IDs that are currently unavailable for booking.

**Parameters:** `lang`

---

### List countries

`GET /sputnik8/v1/countries`

Returns array of countries with available products.

**Parameters:** `lang`, `page`, `limit`

**Response fields:** `id`, `name`, `alpha2`, `products` (count)

---

### List cities

`GET /sputnik8/v1/cities`

Returns array of cities with available products.

**Parameters:**

| Parameter | Description |
|-----------|-------------|
| `lang` | Language (default: `ru`) |
| `page` | Page number |
| `limit` | Items per page (max: `100`) |
| `country_id` | Filter by country ID |

**Response fields:** `id`, `name`, `country_id`, `region_id`

---

### List categories

`GET /sputnik8/v1/cities/{city_id}/categories`

Returns categories for a specific city.

**Parameters:** `lang`, `page`, `limit`

**Response fields:** `id`, `name`, `short_name`, `description`, `sub_categories`, `products`

---

### List reviews

`GET /sputnik8/v1/products/{product_id}/reviews`

Returns reviews for a specific product.

**Parameters:** `lang`, `page`, `limit`

---

### List sights

`GET /sputnik8/v1/sights`

Returns list of sights/attractions.

**Parameters:** `lang`, `page`, `limit`

---

## Key country/city IDs

**Turkey (country_id=4):**

| City | ID |
|------|----|
| Анталья | 367 |
| Кемер | 420 |
| Аланья | 463 |
| Мармарис | 464 |
| Бодрум | 465 |
| Фетхие | 466 |
| Белек | 467 |
| Сиде | 468 |
| Каппадокия | 444 |
| Стамбул | 9 |

**Other popular:**

| City | ID |
|------|----|
| Москва | 1 |
| Санкт-Петербург | 2 |

Use the cities endpoint with `country_id` to discover city IDs for other countries.

---

## Getting short booking links

Always convert Sputnik8 product URLs to short links before showing them to users:

```bash
python scripts/api_call.py --method GET \
  --url "https://api.botclaw.ru/short-link" \
  --params '{"url":"https://www.sputnik8.com/ru/kemer/activities/36404-demre-mira-kekova"}'
```

Response: `{"url": "https://sputnik8.tpm.lv/XXXXXXXX"}` — give this link to the user.

---

## Usage notes

- All requests go through `api.botclaw.ru/sputnik8/` — credentials are injected automatically.
- Maximum **100 products per request** (`limit=100`).
- Use `city_id` to filter excursions by city — works reliably for all cities.
- Use `order=rating&order_type=desc` to surface highest-rated excursions first.
- The `price` field in list responses is a formatted string (e.g. `"39.00 $"`). For arithmetic, use `order_options[].order_lines[].all_prices` from the detail endpoint.
