# Travel Search RU

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![agentskills.io](https://img.shields.io/badge/agentskills.io-compatible-purple.svg)](https://agentskills.io)
[![ClawHub](https://img.shields.io/badge/ClawHub-travel--search--ru-blue.svg)](https://clawhub.ai/skills/travel-search-ru)

Навык для AI-агентов: поиск авиабилетов через Aviasales, туров через Travelata + Level.Travel и экскурсий через Sputnik8, с реальными ценами и ссылками на бронирование.

## Демо

![Travel search demo](https://github.com/MissiaL/travel-search-ru/releases/download/v1.0/book_small.gif)

<details>
<summary>Пример ответа</summary>

![Запрос](https://github.com/MissiaL/travel-search-ru/releases/download/v1.0/request.webp)
![Ответ часть 1](https://github.com/MissiaL/travel-search-ru/releases/download/v1.0/response1.webp)
![Ответ часть 2](https://github.com/MissiaL/travel-search-ru/releases/download/v1.0/response2.webp)

</details>

## Совместимые агенты

Работает с любым AI-агентом, поддерживающим [agentskills.io](https://agentskills.io):

**Claude Code** · **Cursor** · **Gemini CLI** · **GitHub Copilot** · **Windsurf** · **Junie** · **OpenCode** · **Goose** · **Aider** · **Cline** · **Roo Code** · **Amp** · **VS Code Agent** и 30+ других

## Провайдеры

| Провайдер | Что ищет | Данные |
|-----------|----------|--------|
| **Aviasales** | Авиабилеты | Кэшированные цены из поисков пользователей (обновляются ежедневно), все авиакомпании |
| **Travelata** | Пакетные туры | Поиск в реальном времени: перелёт + отель, семьи с детьми, фильтры по питанию и отелю |
| **Level.Travel** | Пакетные туры | Live async-поиск: перелёт + отель или только отель, любой состав группы (включая детей), любые даты и число ночей |
| **Sputnik8** | Экскурсии | Экскурсии, билеты, трансферы в 900+ городах мира |

## Как это работает

```
Пользователь: «Найди авиабилеты из Москвы в Анталью в июне на 2 взрослых и ребёнка»
  │
  ▼
Агент читает SKILL.md → вызывает API → форматирует результаты
  │
  ├─ Aviasales Data API → кэшированные цены на перелёты
  ├─ Travelata API → live-поиск пакетных туров
  ├─ Level.Travel → live async-поиск пакетных туров (наравне с Travelata)
  ├─ Sputnik8 API → экскурсии на месте
  │
  ▼
Пользователь получает цены, даты, авиакомпании, отели и ссылки на бронирование
```

## Что агент делает хорошо

- Держит точную географию запроса по турам и не уводит молча в другой курорт или регион
- Группирует туры по отелям, а не показывает сырой поток одинаковых вариантов
- Показывает короткий shortlist лучших вариантов вместо перегруженной выдачи
- Может сразу дополнить туры экскурсиями через Sputnik8

## Установка

```bash
git clone https://github.com/MissiaL/travel-search-ru.git travel-search-ru
```

Имя директории должно совпадать с именем навыка: `travel-search-ru`.

## MCP-сервер

Тот же поиск доступен через удалённый MCP-сервер. Навык и ключи не нужны.
Это вариант для агентов, которые поддерживают MCP, но не Agent Skills.

**Endpoint:** `https://mcp.botclaw.ru/travel` (Streamable HTTP, без авторизации, только чтение)

```bash
claude mcp add --transport http travel-search-ru https://mcp.botclaw.ru/travel
```

Или в конфиге агента:

```json
{
  "mcpServers": {
    "travel-search-ru": {
      "url": "https://mcp.botclaw.ru/travel"
    }
  }
}
```

**Тулы:** `search_tours` (пакетные туры), `search_hotels` (отели без перелёта),
`get_tour_details` (актуализация тура перед бронированием), `search_flights`,
`get_flight_price_calendar`, `search_activities`, `list_destinations`.

Навык и MCP — два способа пользоваться одним и тем же поиском: навык даёт агенту
инструкции и ходит в API сам, MCP отдаёт готовые тулы.

## Требования

- Python 3.8+ (только стандартная библиотека, pip-пакеты не нужны)
- Доступ в интернет

## Примеры запросов

После установки просто спросите AI-агента о путешествиях:

**Авиабилеты**
- «Найди дешёвые билеты из Москвы в Анталью в июне»
- «Сравни цены на перелёт в Стамбул на следующий месяц»
- «Самые дешёвые прямые рейсы из Питера в Дубай»

**Пакетные туры**
- «Найди туры в Турцию на двоих с двумя детьми, 7 ночей в мае»
- «Туры в Египет всё включено до 100 000 руб.»

**Экскурсии**
- «Какие экскурсии есть в Кемере?»
- «Лучшие экскурсии в Стамбуле»
- «Морские прогулки рядом с Антальей»

**Комбинированные**
- «Спланируй поездку в Турцию: перелёт, варианты отелей и что посмотреть»

## Покрытие API

### Авиабилеты (Aviasales)
- Самые дешёвые билеты на конкретные даты
- Календарь цен (по дням)
- Тренды цен и спецпредложения
- Популярные направления
- Поиск по диапазону цен
- Матрица ближайших аэропортов

### Туры (Travelata)
- Поиск туров с фильтрами (даты, ночи, туристы, питание, рейтинг отеля)
- Справочники стран, курортов и отелей

### Туры (Level.Travel)
- Live async-поиск туров: перелёт + отель или только отель
- Любой состав группы (включая детей), любое число ночей, любой горизонт дат
- Наравне с Travelata: оба источника запускаются на каждый запрос туров, результаты объединяются

### Экскурсии (Sputnik8)
- Поиск экскурсий по городу
- Детали и цены
- Справочники городов и стран
- Категории и отзывы

## Лицензия

MIT
