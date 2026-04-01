# Travel Search Skill

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![agentskills.io](https://img.shields.io/badge/agentskills.io-compatible-purple.svg)](https://agentskills.io)
[![ClawHub](https://img.shields.io/badge/ClawHub-travel--search--ru-blue.svg)](https://clawhub.ai/skills/travel-search-ru)

AI agent skill for searching flights, package tours, and excursions with real prices and direct booking links.

## Demo

![Travel search demo](https://github.com/MissiaL/travel-search-ru/releases/download/v1.0/book.gif)

<details>
<summary>Example response</summary>

![Request](https://github.com/MissiaL/travel-search-ru/releases/download/v1.0/request.webp)
![Response part 1](https://github.com/MissiaL/travel-search-ru/releases/download/v1.0/response1.webp)
![Response part 2](https://github.com/MissiaL/travel-search-ru/releases/download/v1.0/response2.webp)

</details>

## Compatible agents

Works with any [agentskills.io](https://agentskills.io)-compatible AI agent:

**Claude Code** · **Cursor** · **Gemini CLI** · **GitHub Copilot** · **Windsurf** · **Junie** · **OpenCode** · **Goose** · **Aider** · **Cline** · **Roo Code** · **Amp** · **VS Code Agent** and 30+ others

## Supported providers

| Provider | What | Data |
|----------|------|------|
| **Aviasales** | Flights | Cached prices from user searches (updated daily), all airlines |
| **Travelata** | Package tours | Real-time search: flight + hotel, all-inclusive options |
| **Sputnik8** | Excursions & activities | Tours, tickets, transfers in 900+ cities worldwide |

## How it works

```
User: "Find flights from Moscow to Antalya in June for 2 adults and a child"
  │
  ▼
Agent reads SKILL.md → calls APIs → formats results
  │
  ├─ Aviasales Data API → cached flight prices
  ├─ Travelata API → package tour options
  ├─ Sputnik8 API → excursions at destination
  │
  ▼
User gets prices, dates, airlines, hotels, and booking links
```

## Installation

```bash
git clone https://github.com/MissiaL/travel-search-ru.git travel-search
```

The directory name must be `travel-search` to match the skill name.

## Requirements

- Python 3.8+ (stdlib only, no pip packages needed)
- Internet access

## Usage examples

Once installed, ask your AI agent anything about travel:

**Flights**
- "Find cheap flights from Moscow to Antalya in June"
- "Compare flight prices to Istanbul for next month"
- "Cheapest direct flights from Saint Petersburg to Dubai"

**Package tours**
- "Search tours to Turkey for 2 adults and 2 kids, 7 nights in May"
- "Find all-inclusive tours to Egypt under 100,000 RUB"

**Excursions**
- "What excursions are available in Kemer?"
- "Find top-rated activities in Istanbul"
- "Best boat tours near Antalya"

**Combined**
- "Plan a trip to Turkey: flights, hotel options, and things to do"

## API coverage

### Flights (Aviasales)
- Cheapest tickets for specific dates
- Price calendar (day-by-day)
- Price trends and special offers
- Popular destinations
- Search by price range
- Nearby airports matrix

### Tours (Travelata)
- Tour search with filters (dates, nights, guests, meals, hotel rating)
- Country, resort, and hotel directories

### Excursions (Sputnik8)
- Excursion search by city
- Product details with pricing
- City and country directories
- Categories and reviews

## License

MIT
