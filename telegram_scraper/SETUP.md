# Telegram Group Scraper — Инструкция

## Шаг 1: Получить API-ключи Telegram

1. Перейдите на https://my.telegram.org
2. Войдите с номером телефона вашего аккаунта Telegram
3. Нажмите "API development tools"
4. Создайте приложение (название и описание — любые)
5. Запишите **api_id** (число) и **api_hash** (строка)

## Шаг 2: Настроить конфиг

```bash
cd /Users/dvn/Desktop/WWWWW/VR/telegram_scraper
cp config.example.json config.json
```

Отредактируйте `config.json`:
```json
{
  "api_id": 12345678,
  "api_hash": "abcdef1234567890abcdef1234567890",
  "groups": [
    "@cgevent",
    "@alexkrol",
    "@theworldisnoteasy",
    "@Victor_Osyka",
    "@GreenNeuralRobots",
    "@svodkaai_ai",
    "@aioftheday",
    "@tsingular",
    "@boris_again",
    "@vskobelev",
    "@vskobelev",
    "@gonzo_ML"
  ]
}
```

Форматы указания групп:
- `https://t.me/group_name` — публичная ссылка
- `@group_name` — username группы
- `https://t.me/+ABC123` — invite-ссылка (вы должны быть участником)

## Шаг 3: Установить зависимости

```bash
pip install -r requirements.txt
```

## Шаг 4: Запустить сканирование

```bash
# Сканировать все группы за последние 30 дней
python scraper.py

# За последние 7 дней
python scraper.py --days 7

# За 90 дней, без скачивания фото
python scraper.py --days 90 --no-photos

# Только определённые группы
python scraper.py --groups "@group1,@group2"
```

При первом запуске Telethon попросит ввести номер телефона и код из Telegram. Сессия сохранится в файл — повторная авторизация не потребуется.

## Шаг 5: Анализ данных

```bash
# Анализ с встроенными ключевыми словами (VR, AR, AI, музеи и т.д.)
python analyze.py

# С кастомными ключевыми словами
python analyze.py --keywords "VR,нейросеть,метавселенная,музей"
```

## Структура результатов

```
telegram_scraper/
├── output/
│   ├── Group_Name_1.json      # данные по каждой группе
│   ├── Group_Name_2.json
│   ├── summary.json            # сводка
│   └── media/
│       ├── Group_Name_1/       # скачанные фото
│       │   ├── photo_123.jpg
│       │   └── photo_456.jpg
│       └── Group_Name_2/
├── reports/
│   ├── telegram_analysis_*.md  # markdown-отчёт
│   └── analysis_raw.json       # сырые данные анализа
```

## Интеграция с исследованием

После анализа отчёт `reports/telegram_analysis_*.md` можно:
1. Передать Claude для дополнения глав исследования
2. Использовать найденные ссылки как источники
3. Извлечь кейсы и примеры из обсуждений

## Ограничения и советы

- Telegram API rate limits: не сканируйте больше ~5-10 групп подряд
- Большие группы (10k+ сообщений) могут занять несколько минут
- Фото скачиваются в сжатом качестве (как в Telegram)
- Видео и документы НЕ скачиваются — сохраняются только метаданные
