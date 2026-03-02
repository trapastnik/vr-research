"""
Telegram Group Scraper
Сканирует группы Telegram и сохраняет:
- текст сообщений
- ссылки (из текста и entities)
- фото (скачивает в папку media/)
- ссылки на видео, документы и прочие медиа

Использование:
    python scraper.py
    python scraper.py --days 30
    python scraper.py --groups "group1,group2"
"""

import asyncio
import json
import os
import re
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError
    from telethon.tl.types import (
        MessageMediaPhoto,
        MessageMediaDocument,
        MessageMediaWebPage,
        MessageEntityUrl,
        MessageEntityTextUrl,
    )
except ImportError:
    print("Telethon не установлен. Выполните:")
    print("  pip install telethon")
    sys.exit(1)

# ─── Конфигурация ───────────────────────────────────────────────
CONFIG_FILE = Path(__file__).parent / "config.json"
OUTPUT_DIR = Path(__file__).parent / "output"
MEDIA_DIR = OUTPUT_DIR / "media"


def load_config():
    if not CONFIG_FILE.exists():
        print(f"Файл конфигурации не найден: {CONFIG_FILE}")
        print("Скопируйте config.example.json в config.json и заполните данные.")
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_urls_from_message(message):
    """Извлекает все URL из сообщения (из текста и entities)."""
    urls = []

    if message.entities:
        for entity in message.entities:
            if isinstance(entity, MessageEntityUrl):
                url = message.text[entity.offset : entity.offset + entity.length]
                urls.append(url)
            elif isinstance(entity, MessageEntityTextUrl):
                urls.append(entity.url)

    if message.text:
        found = re.findall(r"https?://[^\s<>\"']+", message.text)
        for u in found:
            if u not in urls:
                urls.append(u)

    return urls


def get_media_info(message):
    """Получает информацию о медиа в сообщении."""
    if not message.media:
        return None

    info = {"type": None, "file_name": None, "file_size": None, "local_path": None}

    if isinstance(message.media, MessageMediaPhoto):
        info["type"] = "photo"

    elif isinstance(message.media, MessageMediaDocument):
        doc = message.media.document
        if doc:
            info["file_size"] = doc.size
            for attr in doc.attributes:
                if hasattr(attr, "file_name"):
                    info["file_name"] = attr.file_name

            mime = doc.mime_type or ""
            if "video" in mime:
                info["type"] = "video"
            elif "audio" in mime:
                info["type"] = "audio"
            elif "image" in mime or "sticker" in mime:
                info["type"] = "image"
            else:
                info["type"] = "document"
                if not info["file_name"]:
                    info["file_name"] = f"doc_{message.id}"

    elif isinstance(message.media, MessageMediaWebPage):
        wp = message.media.webpage
        if hasattr(wp, "url"):
            info["type"] = "webpage"
            info["url"] = wp.url
            info["title"] = getattr(wp, "title", None)
            info["description"] = getattr(wp, "description", None)

    return info


async def download_photo(client, message, group_name):
    """Скачивает фото из сообщения."""
    group_media_dir = MEDIA_DIR / group_name
    group_media_dir.mkdir(parents=True, exist_ok=True)

    file_path = group_media_dir / f"photo_{message.id}.jpg"
    if file_path.exists():
        return str(file_path.relative_to(OUTPUT_DIR))

    try:
        await client.download_media(message, file=str(file_path))
        return str(file_path.relative_to(OUTPUT_DIR))
    except Exception as e:
        print(f"    Ошибка скачивания фото {message.id}: {e}")
        return None


async def scrape_group(client, group_identifier, days_back=30, download_photos=True):
    """Сканирует одну группу."""
    print(f"\n{'='*60}")
    print(f"Сканирование: {group_identifier}")
    print(f"{'='*60}")

    try:
        entity = await client.get_entity(group_identifier)
    except Exception as e:
        print(f"  Ошибка подключения к группе: {e}")
        return None

    group_name = getattr(entity, "title", group_identifier)
    group_username = getattr(entity, "username", None)
    safe_name = re.sub(r"[^\w\-]", "_", group_name)

    since_date = datetime.now(timezone.utc) - timedelta(days=days_back)

    result = {
        "group_name": group_name,
        "group_username": group_username,
        "group_id": entity.id,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "days_back": days_back,
        "messages": [],
    }

    count = 0
    photo_count = 0

    async for message in client.iter_messages(entity, offset_date=since_date, reverse=True):
        if message.date.replace(tzinfo=timezone.utc) < since_date:
            continue

        msg_data = {
            "id": message.id,
            "date": message.date.isoformat(),
            "sender_id": message.sender_id,
            "text": message.text or "",
            "urls": extract_urls_from_message(message),
            "media": None,
            "reply_to": message.reply_to_msg_id if message.reply_to else None,
            "views": message.views,
            "forwards": message.forwards,
        }

        # Обработка медиа
        if message.media:
            media_info = get_media_info(message)
            if media_info:
                # Скачиваем фото
                if media_info["type"] == "photo" and download_photos:
                    local_path = await download_photo(client, message, safe_name)
                    if local_path:
                        media_info["local_path"] = local_path
                        photo_count += 1

                msg_data["media"] = media_info

        result["messages"].append(msg_data)
        count += 1

        if count % 100 == 0:
            print(f"  Обработано {count} сообщений...")

    result["total_messages"] = count
    result["total_photos"] = photo_count

    print(f"  Готово: {count} сообщений, {photo_count} фото")
    return result, safe_name


async def main(args):
    config = load_config()

    api_id = config["api_id"]
    api_hash = config["api_hash"]
    session_file = str(Path(__file__).parent / "telegram_session")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    # Определяем список групп
    if args.groups:
        groups = [g.strip() for g in args.groups.split(",")]
    else:
        groups = config.get("groups", [])

    if not groups:
        print("Список групп пуст. Добавьте группы в config.json или укажите через --groups")
        sys.exit(1)

    print(f"Групп для сканирования: {len(groups)}")
    print(f"Период: последние {args.days} дней")
    print(f"Скачивать фото: {'да' if not args.no_photos else 'нет'}")

    client = TelegramClient(
        session_file, api_id, api_hash,
        connection_retries=5,
        retry_delay=2,
    )
    await client.connect()

    async def send_code(phone, force_sms=False):
        try:
            suffix = " (SMS)" if force_sms else ""
            print(f"Запрашиваю код подтверждения{suffix}...")
            sent = await client.send_code_request(phone, force_sms=force_sms)
            code_type = getattr(sent, "type", None)
            code_type_name = code_type.__class__.__name__ if code_type else "Unknown"
            print(f"Код отправлен. Тип: {code_type_name}. Проверьте Telegram/SMS.")
            return True
        except Exception as e:
            print(f"Не удалось отправить код: {e}")
            return False

    if not await client.is_user_authorized():
        phone = input("Введите номер телефона (например +79XXXXXXXXX): ").strip()
        if not await send_code(phone, force_sms=False):
            await client.disconnect()
            return

        for attempt in range(3):
            code = input("Введите код из Telegram (или 'resend' / 'sms' / 'exit'): ").strip()

            if code.lower() in {"resend", "r"}:
                await send_code(phone, force_sms=False)
                continue
            if code.lower() in {"sms", "s"}:
                await send_code(phone, force_sms=True)
                continue
            if code.lower() in {"exit", "quit", "q"}:
                print("Отмена авторизации.")
                await client.disconnect()
                return

            try:
                await client.sign_in(phone=phone, code=code)
                break
            except SessionPasswordNeededError:
                print("\n2FA включена. Нужен ваш пароль двухфакторной аутентификации.")
                print("(Это НЕ код из SMS, а пароль, который вы задавали в настройках Telegram)")
                for pwd_attempt in range(3):
                    password = input("Введите 2FA пароль: ").strip()
                    try:
                        await client.sign_in(password=password)
                        print("Авторизация успешна!")
                        break
                    except Exception as e:
                        print(f"Неверный пароль: {e}")
                        if pwd_attempt == 2:
                            print("Превышено число попыток. Проверьте пароль в Telegram:")
                            print("  Settings → Privacy and Security → Two-Step Verification")
                            await client.disconnect()
                            return
                break
            except Exception as e:
                print(f"Неверный код или ошибка авторизации: {e}")
                if attempt == 2:
                    print("Превышено число попыток. Перезапустите скрипт.")
                    await client.disconnect()
                    return

    print("Авторизация OK. Начинаю сканирование...\n")

    all_results = {}

    for group in groups:
        try:
            result = await scrape_group(
                client,
                group,
                days_back=args.days,
                download_photos=not args.no_photos,
            )
            if result:
                data, safe_name = result
                all_results[safe_name] = data

                # Сохраняем результат для каждой группы отдельно
                group_file = OUTPUT_DIR / f"{safe_name}.json"
                with open(group_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"  Сохранено: {group_file}")

        except Exception as e:
            print(f"  Ошибка при сканировании {group}: {e}")

        # Пауза между группами (rate limiting)
        await asyncio.sleep(2)

    # Сохраняем сводный файл
    summary_file = OUTPUT_DIR / "summary.json"
    summary = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "total_groups": len(all_results),
        "groups": {
            name: {
                "group_name": data["group_name"],
                "total_messages": data["total_messages"],
                "total_photos": data["total_photos"],
            }
            for name, data in all_results.items()
        },
    }
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Сканирование завершено!")
    print(f"Групп обработано: {len(all_results)}")
    print(f"Результаты: {OUTPUT_DIR}")
    print(f"Сводка: {summary_file}")

    await client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telegram Group Scraper")
    parser.add_argument("--days", type=int, default=30, help="За сколько дней собирать (по умолчанию 30)")
    parser.add_argument("--groups", type=str, help="Группы через запятую (переопределяет config.json)")
    parser.add_argument("--no-photos", action="store_true", help="Не скачивать фото")
    args = parser.parse_args()

    asyncio.run(main(args))
