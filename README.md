# Travel Search RU

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![agentskills.io](https://img.shields.io/badge/agentskills.io-compatible-purple.svg)](https://agentskills.io)
[![ClawHub](https://img.shields.io/badge/ClawHub-travel--search--ru-blue.svg)](https://clawhub.ai/skills/travel-search-ru)

Поисковый слой для планирования путешествий с популярными туристическими сервисами: **Aviasales**, **Travelata**, **Level.Travel**, **Tutu.ru**, **Tripster** и **Sputnik8**.

Агент может составить маршрут своими обычными инструментами, а навык найдёт для него авиабилеты, поезда, пакетные туры, отели и экскурсии. В ответе будут цены, ключевые параметры и короткие ссылки на выдачу. Навык работает в Claude Code, Cursor, Gemini CLI, GitHub Copilot и других AI-агентах.

| Сервис | Что доступно |
|--------|--------------|
| **Aviasales** | Авиабилеты и календарь цен |
| **Travelata** | Пакетные туры |
| **Level.Travel** | Пакетные туры и отели без перелёта |
| **Tutu.ru** | Кэшированное расписание поездов и ориентировочные цены |
| **Tripster** | Экскурсии и активности |
| **Sputnik8** | Экскурсии, билеты и активности |

**Два способа подключения:** [Agent Skill](#установка) или [удалённый MCP-сервер](#mcp-сервер).

## Демо

### Codex: семейный отпуск в Кемере

![Codex ищет тур и экскурсии в Кемере](https://github.com/MissiaL/travel-search-ru/releases/download/v2.1.0/codex-kemer-agent-log.gif)

Анимация собрана из результатов живого MCP-запроса от 22 июля 2026 года; это не запись экрана. Перед бронированием уточняйте цену и доступность.

![Travel search demo](https://github.com/MissiaL/travel-search-ru/releases/download/v1.0/book_small.gif)

<details>
<summary>Пример ответа</summary>

![Запрос](https://github.com/MissiaL/travel-search-ru/releases/download/v1.0/request.webp)
![Ответ часть 1](https://github.com/MissiaL/travel-search-ru/releases/download/v1.0/response1.webp)
![Ответ часть 2](https://github.com/MissiaL/travel-search-ru/releases/download/v1.0/response2.webp)

</details>

## Совместимые агенты

Работает с любым AI-агентом, который поддерживает [agentskills.io](https://agentskills.io):

**Claude Code** · **Cursor** · **Gemini CLI** · **GitHub Copilot** · **Windsurf** · **Junie** · **OpenCode** · **Goose** · **Aider** · **Cline** · **Roo Code** · **Amp** · **VS Code Agent** и 30+ других

## Как это устроено

```
Пользователь спрашивает про туры / отели / авиа / поезда / экскурсии
  │
  ▼
Агент читает SKILL.md → запускает scripts/travel_search.py → оформляет ответ
  │
  ▼
MCP https://mcp.botclaw.ru/travel (Streamable HTTP)
```

| Команда CLI | Назначение |
|-------------|------------|
| `search-tours` | Пакетные туры (перелёт + отель) |
| `search-hotels` | Отели без перелёта |
| `get-tour-details` | Актуальные детали тура перед бронированием |
| `search-flights` | Варианты перелётов |
| `flight-calendar` | Календарь цен на авиабилеты |
| `search-trains` | Поезда Tutu.ru и ориентировочные цены |
| `search-activities` | Экскурсии и активности |
| `list-destinations` | Справочник направлений |

## Установка

```bash
git clone https://github.com/MissiaL/travel-search-ru.git travel-search-ru
```

Имя каталога должно совпадать с именем навыка: `travel-search-ru`.

## CLI

Только стандартная библиотека Python 3.8+ (без pip-пакетов).

```bash
python scripts/travel_search.py list-tools
python scripts/travel_search.py describe search-tours
python scripts/travel_search.py search-tours --input '{"departure_city":"Москва","country":"Турция","date_from":"2026-09-10","date_to":"2026-09-20","adults":2}'
```

Актуальные схемы полей — через `describe`, см. [references/usage.md](references/usage.md).

Особенности поиска:

- `search-trains` возвращает кэшированное расписание Tutu.ru и ориентировочные цены. Дата используется в ссылке на выдачу; наличие поезда, мест и итоговую цену нужно проверить перед бронированием.
- У `search-activities` поля `date_from` и `date_to` необязательны, а `persons` принимает значения от 1 до 100.

## MCP-сервер

Тот же поиск доступен как удалённый MCP-сервер для агентов с поддержкой MCP, но без Agent Skills.

**Эндпоинт:** `https://mcp.botclaw.ru/travel` (Streamable HTTP, без авторизации, только чтение)

```bash
claude mcp add --transport http travel-search-ru https://mcp.botclaw.ru/travel
```

Или в конфигурации агента:

```json
{
  "mcpServers": {
    "travel-search-ru": {
      "url": "https://mcp.botclaw.ru/travel"
    }
  }
}
```

## Язык и каталог

Навык оптимизирован под **русскоязычные запросы** и **русскоязычный каталог** (имена направлений и городов в upstream-справочнике на русском — отсюда русские примеры CLI). Это не принуждение к русскому диалогу: **язык ответа** по возможности совпадает с языком пользователя. Запросы **не на русском** тоже обрабатываются; для MCP при необходимости используются русские значения каталога.

## Данные и удалённый сервис

Единственный удалённый эндпоинт: `https://mcp.botclaw.ru/travel` (HTTPS, только чтение).

На сервис уходят **только переданные критерии поиска** (города, даты, состав путешественников и т.п.). Для поездов дата используется в ссылке Tutu.ru, но само расписание API по дате не фильтрует. Учётные данные не передаются; доступ к почте/календарю не используется; бронирование и долговременное хранение не выполняются.

## Требования

- Python 3.8+ (только стандартная библиотека)
- Сетевой доступ к MCP-эндпоинту

## Примеры запросов

- «Спланируй поездку в Турцию на неделю с актуальными ценами»
- «Найди туры в Турцию на двоих, 7 ночей в мае»
- «Отель в Стамбуле без перелёта на 5 ночей»
- «Дешёвые билеты из Москвы в Анталью в июне»
- «Найди поезд из Москвы в Сочи на 15 сентября»
- «Экскурсии в Кемере»

## Лицензия

MIT
