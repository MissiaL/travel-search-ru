# Travel Search RU

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![agentskills.io](https://img.shields.io/badge/agentskills.io-compatible-purple.svg)](https://agentskills.io)
[![ClawHub](https://img.shields.io/badge/ClawHub-travel--search--ru-blue.svg)](https://clawhub.ai/skills/travel-search-ru)

Навык для AI-агентов: поиск авиабилетов, пакетных туров и экскурсий с реальными ценами и ссылками на бронирование.

## Демо

![Travel search demo](https://github.com/MissiaL/travel-search-ru/releases/download/v1.0/book.gif)

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
| **Travelata** | Пакетные туры | Поиск в реальном времени: перелёт + отель, варианты «всё включено» |
| **Sputnik8** | Экскурсии | Экскурсии, билеты, трансферы в 900+ городах мира |

## Как это работает

```
Пользователь: «Найди авиабилеты из Москвы в Анталью в июне на 2 взрослых и ребёнка»
  │
  ▼
Агент читает SKILL.md → вызывает API → форматирует результаты
  │
  ├─ Aviasales Data API → кэшированные цены на перелёты
  ├─ Travelata API → пакетные туры
  ├─ Sputnik8 API → экскурсии на месте
  │
  ▼
Пользователь получает цены, даты, авиакомпании, отели и ссылки на бронирование
```

## Установка

```bash
git clone https://github.com/MissiaL/travel-search-ru.git travel-search-ru
```

Имя директории должно совпадать с именем навыка: `travel-search-ru`.

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

### Экскурсии (Sputnik8)
- Поиск экскурсий по городу
- Детали и цены
- Справочники городов и стран
- Категории и отзывы

## Лицензия

MIT
