"""
Анализатор годовых данных Telegram для VR-исследования.

Читает JSON из output_year/, фильтрует по VR/3D/AR тематике,
группирует по темам и генерирует отчёт для интеграции в исследование.

Использование:
    source venv/bin/activate
    python analyze_year.py
"""

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

INPUT_DIR = Path(__file__).parent / "output_year"
REPORT_DIR = Path(__file__).parent / "reports"

# ─── Тематические категории с ключевыми словами ────────────────

CATEGORIES = {
    "Gaussian Splatting / NeRF": [
        "gaussian", "splat", "гауссиан", "nerf", "radiance field",
        "3dgs", "4dgs", "ppisp", "gsplat", "splatfacto", "nerfstudio",
        "splat world", "vr-splat", "vrsplat",
    ],
    "3D генерация (Text/Image/Video-to-3D)": [
        "text-to-3d", "image-to-3d", "video-to-3d", "text to 3d",
        "hunyuan3d", "hunyuan 3d", "actionmesh", "action mesh",
        "instantmesh", "instant mesh", "meshy", "tripo3d", "tripo 3d",
        "wonder3d", "trellis", "shap-e", "point-e", "dreamfusion",
        "3d генерац", "генерация 3d", "3d модел",
    ],
    "VR/AR шлемы и устройства": [
        "quest 3", "quest 4", "quest pro", "meta quest",
        "pico 4", "pico 5", "pico ultra", "pico g3",
        "vision pro", "apple vision", "apple glass", "smart glass",
        "умные очки", "ar очки", "ar-очки",
        "htc vive", "xreal", "varjo", "dpvr",
        "openxr", "webxr", "passthrough", "eye tracking",
        "headset", "шлем vr", "vr шлем", "vr-шлем",
        "ai pendant", "ai кулон", "airpods камер",
    ],
    "Генеративное видео": [
        "sora", "veo ", "veo2", "veo 2", "veo3", "veo 3",
        "seedance", "kling", "runway", "pika",
        "minimax", "hailuo", "wan ", "wan2",
        "генератив видео", "генерация видео", "video generat",
        "text-to-video", "image-to-video",
    ],
    "Генеративная музыка и аудио": [
        "ace-step", "acestep", "ace step",
        "suno", "udio", "musicgen", "music gen",
        "stable audio", "генерация музыки", "music generat",
        "spatial audio", "пространственн звук", "амбисони",
    ],
    "Unity / Unreal / Движки": [
        "unity 6", "unity ai", "unity muse", "unity author",
        "unreal engine", "unreal 5", "ue5", "ue6",
        "nanite", "lumen", "metahuman", "meta human",
        "godot", "webgpu", "webgl",
    ],
    "Аватары и Motion Capture": [
        "avatar", "аватар", "mocap", "motion capture",
        "meshcapade", "smpl", "body model",
        "lip sync", "lipsync", "audio2face",
        "deepfake", "дипфейк", "face swap",
        "digital human", "цифровой человек",
    ],
    "Генерация интерактивных миров": [
        "genie 2", "genie 3", "genie2", "genie3", "project genie",
        "world model", "world generat",
        "waymo world", "world sim",
        "интерактивн мир", "генерация мир",
    ],
    "Метавселенная / VR общее": [
        "метаверс", "metavers", "виртуальн реальн", "virtual reality",
        "дополненн реальн", "augmented reality",
        "иммерсив", "immersive", "xr ", "mixed reality",
        "смешанн реальн", "spatial comput",
    ],
    "Volumetric Capture": [
        "volumetric", "волюметрич", "объёмн захват", "объемн захват",
        "4d capture", "4d video", "arcturus",
        "depthkit", "light stage",
    ],
    "Робототехника / Embodied AI": [
        "robot", "робот", "humanoid", "гуманоид",
        "embodied", "манипулятор", "boston dynamics",
        "figure ", "figure0", "optimus",
    ],
    "Культура / Музеи / Наследие": [
        "музей", "museum", "культур", "наследи", "heritage",
        "выставк", "экспозиц", "gallery", "галере",
        "реставрац", "архитектур", "памятник",
        "библиотек", "library", "театр", "спектакл", "балет",
        "концерт", "оркестр", "филармон",
    ],
    "LiDAR / Фотограмметрия / Сканирование": [
        "lidar", "лидар", "photogrammetry", "фотограмметри",
        "сканирован", "3d scan", "point cloud", "облако точек",
        "reality capture", "polycam", "matterport",
    ],
}

# Минимальное количество символов в сообщении для включения
MIN_TEXT_LENGTH = 50


def categorize_message(text):
    """Определяет категории сообщения."""
    text_lower = text.lower()
    matched = []
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in text_lower:
                matched.append(cat)
                break
    return matched


def analyze_yearly_data():
    """Анализирует годовые данные."""
    json_files = sorted(INPUT_DIR.glob("*.json"))
    json_files = [f for f in json_files if f.name not in ("summary.json", "_progress.json")]

    if not json_files:
        print(f"JSON-файлы не найдены в {INPUT_DIR}")
        sys.exit(1)

    print(f"Файлов: {len(json_files)}")

    # Собираем все сообщения
    all_messages = []
    channel_stats = {}

    for fpath in json_files:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        group_name = data.get("group_name", fpath.stem)
        messages = data.get("messages", [])
        channel_stats[group_name] = {"total": len(messages), "relevant": 0}

        for msg in messages:
            text = msg.get("text", "") or ""
            if len(text) < MIN_TEXT_LENGTH:
                continue

            cats = categorize_message(text)
            if cats:
                all_messages.append({
                    "text": text,
                    "date": msg.get("date", "")[:10],
                    "channel": group_name,
                    "views": msg.get("views") or 0,
                    "forwards": msg.get("forwards") or 0,
                    "urls": msg.get("urls", []),
                    "categories": cats,
                    "id": msg.get("id"),
                })
                channel_stats[group_name]["relevant"] += 1

    print(f"Всего сообщений: {sum(s['total'] for s in channel_stats.values())}")
    print(f"Релевантных VR/AI: {len(all_messages)}")

    # Группируем по категориям
    by_category = defaultdict(list)
    for msg in all_messages:
        for cat in msg["categories"]:
            by_category[cat].append(msg)

    # Сортируем в каждой категории по views
    for cat in by_category:
        by_category[cat].sort(key=lambda m: m["views"], reverse=True)

    # Временная динамика по месяцам
    monthly = defaultdict(lambda: defaultdict(int))
    for msg in all_messages:
        month = msg["date"][:7]  # YYYY-MM
        for cat in msg["categories"]:
            monthly[month][cat] += 1

    return all_messages, by_category, channel_stats, monthly


def generate_report(all_messages, by_category, channel_stats, monthly):
    """Генерирует markdown-отчёт."""
    lines = []
    lines.append("# Годовой анализ Telegram-каналов: VR/AR/AI для культурного наследия")
    lines.append(f"\n**Дата анализа:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Период:** 365 дней (до {datetime.now().strftime('%Y-%m-%d')})")
    lines.append(f"**Каналов:** {len(channel_stats)}")
    lines.append(f"**Всего сообщений:** {sum(s['total'] for s in channel_stats.values()):,}")
    lines.append(f"**Релевантных VR/AI:** {len(all_messages):,}")

    # Статистика каналов
    lines.append("\n---\n## 1. Статистика по каналам\n")
    lines.append("| Канал | Всего | Релевантных | % |")
    lines.append("|-------|-------|-------------|---|")
    for name, stats in sorted(channel_stats.items(), key=lambda x: x[1]["relevant"], reverse=True):
        pct = round(stats["relevant"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0
        lines.append(f"| {name} | {stats['total']:,} | {stats['relevant']:,} | {pct}% |")

    # Размер категорий
    lines.append("\n---\n## 2. Тематический охват (количество сообщений по категориям)\n")
    lines.append("| Категория | Сообщений | Топ каналы |")
    lines.append("|-----------|-----------|------------|")
    for cat, msgs in sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True):
        # Топ каналы для этой категории
        ch_counts = Counter(m["channel"] for m in msgs)
        top_ch = ", ".join([f"{ch}({cnt})" for ch, cnt in ch_counts.most_common(3)])
        lines.append(f"| {cat} | {len(msgs)} | {top_ch} |")

    # Динамика по месяцам
    lines.append("\n---\n## 3. Динамика упоминаний по месяцам\n")
    months = sorted(monthly.keys())
    # Показываем топ-5 категорий
    top_cats = sorted(by_category.keys(), key=lambda c: len(by_category[c]), reverse=True)[:6]
    header = "| Месяц | " + " | ".join(top_cats) + " |"
    sep = "|-------|" + "|".join(["------"] * len(top_cats)) + "|"
    lines.append(header)
    lines.append(sep)
    for month in months:
        vals = " | ".join([str(monthly[month].get(cat, 0)) for cat in top_cats])
        lines.append(f"| {month} | {vals} |")

    # Детали по каждой категории
    lines.append("\n---\n## 4. Ключевые публикации по категориям\n")

    for cat in sorted(by_category.keys(), key=lambda c: len(by_category[c]), reverse=True):
        msgs = by_category[cat]
        lines.append(f"\n### {cat} ({len(msgs)} сообщений)\n")

        # Топ-15 самых просматриваемых
        shown = 0
        seen_texts = set()
        for msg in msgs:
            # Дедупликация по первым 100 символам
            text_key = msg["text"][:100].lower()
            if text_key in seen_texts:
                continue
            seen_texts.add(text_key)

            text = msg["text"][:400].replace("\n", " ").strip()
            date = msg["date"]
            channel = msg["channel"]
            views = msg["views"]
            urls = msg["urls"]

            lines.append(f"**[{date}]** ({channel}, {views:,} просм.)")
            lines.append(f"> {text}")
            if urls:
                for url in urls[:3]:
                    lines.append(f"> 🔗 {url}")
            lines.append("")

            shown += 1
            if shown >= 15:
                break

    # Все уникальные URL
    lines.append("\n---\n## 5. Уникальные ссылки (топ-100 по частоте упоминаний)\n")
    url_counter = Counter()
    for msg in all_messages:
        for url in msg.get("urls", []):
            # Чистим URL
            url = url.strip().rstrip("/").rstrip(")")
            if len(url) > 20 and not url.startswith("http://t.me"):
                url_counter[url] += 1

    for url, count in url_counter.most_common(100):
        lines.append(f"- ({count}x) {url}")

    return "\n".join(lines)


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("Анализ годовых данных Telegram...\n")
    all_messages, by_category, channel_stats, monthly = analyze_yearly_data()

    # Генерируем отчёт
    report = generate_report(all_messages, by_category, channel_stats, monthly)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    report_file = REPORT_DIR / f"year_analysis_{timestamp}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n📊 Отчёт: {report_file}")

    # Сохраняем сырые данные
    raw_file = REPORT_DIR / "year_analysis_raw.json"
    raw_data = {
        "generated_at": datetime.now().isoformat(),
        "channel_stats": channel_stats,
        "category_counts": {cat: len(msgs) for cat, msgs in by_category.items()},
        "monthly": {m: dict(cats) for m, cats in monthly.items()},
        "total_relevant": len(all_messages),
    }
    with open(raw_file, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)
    print(f"📦 Сырые данные: {raw_file}")

    # Краткая сводка
    print(f"\n{'='*60}")
    print("КРАТКАЯ СВОДКА:")
    print(f"{'='*60}")
    for cat, msgs in sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True):
        bar = "█" * min(len(msgs) // 10, 40)
        print(f"  {cat:<45} {len(msgs):>5} {bar}")


if __name__ == "__main__":
    main()
