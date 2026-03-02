"""
Годовая выгрузка Telegram-каналов для VR-исследования.

Собирает данные за 365 дней из наиболее релевантных каналов.
Фото не скачиваются (экономия времени и места).
Данные сохраняются в output_year/.

Использование:
    source venv/bin/activate
    python scrape_year.py
    python scrape_year.py --days 180          # за полгода
    python scrape_year.py --resume             # продолжить прерванный сбор
"""

import asyncio
import json
import os
import re
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time

try:
    from telethon import TelegramClient
    from telethon.errors import (
        SessionPasswordNeededError,
        FloodWaitError,
        ChatAdminRequiredError,
        ChannelPrivateError,
    )
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

# ─── Пути ────────────────────────────────────────────────────
CONFIG_FILE = Path(__file__).parent / "config.json"
OUTPUT_DIR = Path(__file__).parent / "output_year"
PROGRESS_FILE = OUTPUT_DIR / "_progress.json"
SESSION_FILE = str(Path(__file__).parent / "telegram_session")


def load_config():
    if not CONFIG_FILE.exists():
        print(f"Файл конфигурации не найден: {CONFIG_FILE}")
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed": [], "in_progress": None}


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def extract_urls(message):
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
    if not message.media:
        return None
    info = {"type": None, "file_name": None, "file_size": None}

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
            elif "image" in mime:
                info["type"] = "image"
            else:
                info["type"] = "document"
    elif isinstance(message.media, MessageMediaWebPage):
        wp = message.media.webpage
        if hasattr(wp, "url"):
            info["type"] = "webpage"
            info["url"] = getattr(wp, "url", None)
            info["title"] = getattr(wp, "title", None)
    return info


async def scrape_group_year(client, group_id, days_back=365):
    """Сканирует группу за длительный период с обработкой FloodWait."""
    print(f"\n{'='*60}")
    print(f"  Канал: {group_id}")
    print(f"  Период: {days_back} дней")
    print(f"{'='*60}")

    try:
        entity = await client.get_entity(group_id)
    except ChannelPrivateError:
        print(f"  ❌ Канал приватный или заблокирован: {group_id}")
        return None
    except ChatAdminRequiredError:
        print(f"  ❌ Нет доступа к каналу: {group_id}")
        return None
    except Exception as e:
        print(f"  ❌ Ошибка подключения: {e}")
        return None

    group_name = getattr(entity, "title", group_id)
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
    start_time = time.time()
    batch_save = 500  # промежуточное сохранение каждые 500 сообщений
    out_file = OUTPUT_DIR / f"{safe_name}.json"

    try:
        async for message in client.iter_messages(entity, offset_date=since_date, reverse=True):
            if message.date.replace(tzinfo=timezone.utc) < since_date:
                continue

            msg_data = {
                "id": message.id,
                "date": message.date.isoformat(),
                "sender_id": message.sender_id,
                "text": message.text or "",
                "urls": extract_urls(message),
                "media": get_media_info(message) if message.media else None,
                "reply_to": message.reply_to_msg_id if message.reply_to else None,
                "views": message.views,
                "forwards": message.forwards,
            }

            result["messages"].append(msg_data)
            count += 1

            if count % 100 == 0:
                elapsed = time.time() - start_time
                rate = count / elapsed if elapsed > 0 else 0
                print(f"  📥 {count} сообщений ({rate:.0f} msg/sec)...")

            # Промежуточное сохранение
            if count % batch_save == 0:
                result["total_messages"] = count
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"  💾 Промежуточное сохранение: {count} msg -> {out_file.name}")

    except FloodWaitError as e:
        wait_sec = e.seconds
        print(f"  ⏳ FloodWait: ждём {wait_sec} секунд...")
        await asyncio.sleep(wait_sec + 5)
        # Сохраняем то, что собрали
        result["total_messages"] = count
        result["interrupted"] = True
        result["interrupted_reason"] = f"FloodWait {wait_sec}s"

    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        result["total_messages"] = count
        result["interrupted"] = True
        result["interrupted_reason"] = str(e)

    # Финальное сохранение
    result["total_messages"] = count
    elapsed = time.time() - start_time
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  ✅ {group_name}: {count} сообщений за {elapsed:.0f} сек")
    print(f"  💾 Сохранено: {out_file}")
    return safe_name, count


async def main(args):
    config = load_config()
    api_id = config["api_id"]
    api_hash = config["api_hash"]

    # Используем groups_year из конфига
    groups = config.get("groups_year", config.get("groups", []))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Загрузка прогресса для режима --resume
    progress = load_progress() if args.resume else {"completed": [], "in_progress": None}

    if args.resume and progress["completed"]:
        print(f"Возобновление: уже собрано {len(progress['completed'])} каналов")
        print(f"  Завершены: {', '.join(progress['completed'])}")
        remaining = [g for g in groups if g not in progress["completed"]]
        groups = remaining

    if not groups:
        print("Все каналы уже обработаны!")
        return

    print(f"\n{'#'*60}")
    print(f"  ГОДОВАЯ ВЫГРУЗКА TELEGRAM-КАНАЛОВ")
    print(f"  Каналов: {len(groups)}")
    print(f"  Период: {args.days} дней")
    print(f"  Выходная папка: {OUTPUT_DIR}")
    print(f"  Фото: НЕ скачиваются (--no-photos по умолчанию)")
    print(f"{'#'*60}\n")

    client = TelegramClient(
        SESSION_FILE, api_id, api_hash,
        connection_retries=5,
        retry_delay=2,
    )
    await client.connect()

    if not await client.is_user_authorized():
        phone = input("Введите номер телефона (например +79XXXXXXXXX): ").strip()
        try:
            await client.send_code_request(phone)
        except Exception as e:
            print(f"Ошибка отправки кода: {e}")
            await client.disconnect()
            return

        code = input("Введите код из Telegram: ").strip()
        try:
            await client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            password = input("Введите 2FA пароль: ").strip()
            try:
                await client.sign_in(password=password)
            except Exception as e:
                print(f"Ошибка 2FA: {e}")
                await client.disconnect()
                return
        except Exception as e:
            print(f"Ошибка авторизации: {e}")
            await client.disconnect()
            return

    print("✅ Авторизация OK\n")

    total_messages = 0
    total_start = time.time()
    results_summary = {}

    for i, group in enumerate(groups, 1):
        print(f"\n[{i}/{len(groups)}] Обработка {group}...")
        progress["in_progress"] = group
        save_progress(progress)

        result = await scrape_group_year(client, group, days_back=args.days)

        if result:
            safe_name, msg_count = result
            results_summary[safe_name] = msg_count
            total_messages += msg_count
            progress["completed"].append(group)
            progress["in_progress"] = None
            save_progress(progress)

        # Пауза между каналами (5 сек — чтобы не получить FloodWait)
        if i < len(groups):
            pause = 5
            print(f"\n  ⏸  Пауза {pause} сек перед следующим каналом...")
            await asyncio.sleep(pause)

    # Итоговая сводка
    total_elapsed = time.time() - total_start

    summary = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "days_back": args.days,
        "total_groups": len(results_summary),
        "total_messages": total_messages,
        "elapsed_seconds": round(total_elapsed),
        "groups": results_summary,
    }
    summary_file = OUTPUT_DIR / "summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n{'#'*60}")
    print(f"  ГОТОВО!")
    print(f"  Каналов обработано: {len(results_summary)}")
    print(f"  Всего сообщений: {total_messages}")
    print(f"  Время: {total_elapsed:.0f} сек ({total_elapsed/60:.1f} мин)")
    print(f"  Результаты: {OUTPUT_DIR}")
    print(f"  Сводка: {summary_file}")
    print(f"{'#'*60}")

    await client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Годовая выгрузка Telegram-каналов для VR-исследования")
    parser.add_argument("--days", type=int, default=365, help="За сколько дней собирать (по умолчанию 365)")
    parser.add_argument("--resume", action="store_true", help="Продолжить прерванный сбор")
    args = parser.parse_args()

    asyncio.run(main(args))
