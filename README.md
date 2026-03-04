# VR-экосистема культурного наследия Санкт-Петербурга

Аналитическое исследование рынка VR для создания межведомственной культурной экосистемы.
13 глав, 170+ источников, 15+ стран, 50+ кейсов.

**Сайт:** [vr.ostrov-vezeniya.ru](https://vr.ostrov-vezeniya.ru/)

---

## Структура проекта

```
research/           <- Исходные тексты глав (source of truth)
  00_executive_summary.md
  01_глобальный_рынок_vr_ar.md
  ...
  13_дорожная_карта.md
  viz/              <- Интерактивные визуализации (ECharts)
  build_epub.sh     <- Сборка EPUB-книги

adapt_docs.py       <- Конвертер research/ -> docs/
docs/               <- Частично генерируемая, частично ручная
  *.md              <- Генерируются adapt_docs.py (не в git)
  monitoring.md     <- Страница мониторинга (ручная, в git)
  monitoring-viz/   <- Визуализации мониторинга (в git)
  viz/              <- Визуализации глав (в git)
  assets/           <- CSS (в git)

telegram_scraper/   <- Скрейпер Telegram-каналов
  scraper.py        <- Сбор за 30 дней
  scrape_year.py    <- Годовой сбор (365 дней)
  analyze.py        <- Анализ месячных данных
  analyze_year.py   <- Анализ годовых данных
  reports/          <- Сгенерированные отчёты
  config.json       <- Список каналов (без ключей)
  .env              <- API-ключи Telegram (не в git)

mkdocs.yml          <- Конфигурация MkDocs Material
Dockerfile          <- Multi-stage: python -> mkdocs -> nginx
docker-compose.prod.yml  <- Продакшн с Traefik
Makefile            <- Все команды проекта
```

---

## Быстрый старт

```bash
# Установка
make setup

# Локальный сервер (http://localhost:8000)
make serve

# Сборка сайта
make build
```

---

## Два рабочих процесса

### Процесс 1: Обновление контента

```
1. Редактируешь файлы в research/
2. make adapt          # research/ -> docs/
3. make build          # Проверяешь локально
4. git add && commit && push   # Деплой автоматический
```

**Telegram-мониторинг:**
```
1. make scrape-year    # Собрать данные из каналов
2. make analyze-year   # Сгенерировать отчёт
3. Обновить docs/monitoring.md вручную
4. git add && commit && push
```

### Процесс 2: Изменение веб-проекта

```
1. Редактируешь mkdocs.yml / CSS / Dockerfile / nginx.conf
2. make build          # Проверяешь локально
3. git push            # CI/CD деплоит на VPS
```

---

## Makefile-команды

| Команда | Описание |
|---------|----------|
| `make help` | Показать все команды |
| `make setup` | Установить зависимости MkDocs |
| `make setup-scraper` | Установить зависимости скрейпера |
| `make adapt` | Конвертировать research/ -> docs/ |
| `make build` | Собрать сайт (включает adapt) |
| `make serve` | Локальный dev-сервер |
| `make scrape` | Скрейпинг Telegram (30 дней) |
| `make scrape-year` | Скрейпинг Telegram (год) |
| `make analyze` | Анализ месячных данных |
| `make analyze-year` | Анализ годовых данных |
| `make epub` | Собрать EPUB-книгу |
| `make clean` | Удалить build-артефакты |

---

## Деплой

**Автоматический** через GitHub Actions при пуше в `main`.
Триггеры: изменения в `research/`, `docs/`, `mkdocs.yml`, `Dockerfile`, `requirements.txt`.

**Ручной запуск:**
```bash
gh workflow run 'Deploy VR Research'
```

**Что происходит при деплое:**
1. GitHub Actions подключается к VPS по SSH
2. `git pull` обновляет код
3. Docker собирает образ: `adapt_docs.py` + `mkdocs build` + nginx
4. Контейнер перезапускается

---

## Telegram-скрейпер

### Настройка
1. Получить API-ключи: [my.telegram.org](https://my.telegram.org)
2. Создать `telegram_scraper/.env`:
   ```
   TG_API_ID=your_id
   TG_API_HASH=your_hash
   ```
3. `make setup-scraper`

### Использование
```bash
make scrape-year     # Собрать данные
make analyze-year    # Получить отчёт в reports/
```

Отчёт используется для обновления `docs/monitoring.md` и глав исследования.

---

## Технологии

- **MkDocs Material** — генератор статического сайта
- **Docker + nginx** — хостинг
- **Traefik** — reverse proxy + SSL
- **GitHub Actions** — CI/CD
- **Telethon** — Telegram API
- **ECharts** — интерактивные визуализации
- **Pandoc** — сборка EPUB
