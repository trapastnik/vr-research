"""
Анализатор данных из Telegram-групп.
Читает JSON-файлы из output/ и создаёт:
- сводку по каждой группе (ключевые темы, активные ссылки)
- общий отчёт со всеми ссылками и упоминаниями технологий
- markdown-файл для интеграции в исследование

Использование:
    python analyze.py
    python analyze.py --keywords "VR,AR,AI,нейросеть,метавселенная"
"""

import json
import re
import sys
import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
REPORT_DIR = Path(__file__).parent / "reports"

# Ключевые слова для поиска релевантного контента
DEFAULT_KEYWORDS = [
    # VR/AR
    "vr", "ar", "xr", "mr", "виртуальная реальность", "дополненная реальность",
    "смешанная реальность", "метавселенная", "metaverse",
    "quest", "vision pro", "pico", "htc vive", "varjo",
    "иммерсивн", "шлем", "гарнитур", "headset",
    # AI
    "ai", "ии", "нейросет", "нейронн", "gpt", "llm", "генеративн",
    "машинное обучение", "machine learning", "deep learning",
    "stable diffusion", "midjourney", "dall-e", "sora",
    "claude", "gemini", "copilot",
    # 3D / графика
    "3d", "unreal", "unity", "godot", "blender",
    "рендеринг", "render", "nerf", "gaussian splat",
    "photogrammetry", "фотограмметрия", "lidar", "лидар",
    # Культура / музеи
    "музей", "museum", "выставк", "экспозиц", "культур",
    "наследие", "heritage", "галере", "арт-", "art ",
    "цифровизац", "digital twin", "цифровой двойник",
    # Технологии
    "spatial computing", "пространственн", "haptic", "тактильн",
    "eye tracking", "отслеживан", "контроллер", "жест",
    "webxr", "openxr", "volumetric", "волюметрич",
]


def load_group_data(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_relevant_messages(messages, keywords):
    """Находит сообщения, содержащие ключевые слова."""
    relevant = []
    for msg in messages:
        text = (msg.get("text") or "").lower()
        if not text:
            continue
        matched_keywords = []
        for kw in keywords:
            if kw.lower() in text:
                matched_keywords.append(kw)
        if matched_keywords:
            relevant.append({**msg, "_matched_keywords": matched_keywords})
    return relevant


def extract_all_urls(messages):
    """Собирает все уникальные URL из сообщений."""
    urls = Counter()
    for msg in messages:
        for url in msg.get("urls", []):
            urls[url] += 1
        media = msg.get("media")
        if media and media.get("type") == "webpage":
            url = media.get("url")
            if url:
                urls[url] += 1
    return urls


def analyze_group(data, keywords):
    """Анализирует данные одной группы."""
    messages = data.get("messages", [])
    relevant = find_relevant_messages(messages, keywords)
    all_urls = extract_all_urls(messages)

    # Статистика по ключевым словам
    keyword_counts = Counter()
    for msg in relevant:
        for kw in msg["_matched_keywords"]:
            keyword_counts[kw] += 1

    # Сообщения с наибольшим числом просмотров
    top_viewed = sorted(
        [m for m in messages if m.get("views")],
        key=lambda m: m.get("views", 0),
        reverse=True,
    )[:10]

    # Медиа-статистика
    media_counts = Counter()
    for msg in messages:
        media = msg.get("media")
        if media:
            media_counts[media.get("type", "unknown")] += 1

    return {
        "group_name": data["group_name"],
        "total_messages": len(messages),
        "relevant_messages": len(relevant),
        "relevant_data": relevant[:50],  # топ-50 релевантных
        "top_keywords": keyword_counts.most_common(20),
        "all_urls": all_urls.most_common(50),
        "top_viewed": top_viewed,
        "media_stats": dict(media_counts),
    }


def generate_markdown_report(analyses):
    """Генерирует markdown-отчёт."""
    lines = []
    lines.append("# Анализ Telegram-групп")
    lines.append(f"\nДата анализа: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Общая сводка
    lines.append("## Общая сводка\n")
    lines.append("| Группа | Сообщений | Релевантных | Фото | Видео |")
    lines.append("|--------|-----------|-------------|------|-------|")

    total_msgs = 0
    total_relevant = 0
    all_urls_combined = Counter()
    all_keywords_combined = Counter()

    for a in analyses:
        photos = a["media_stats"].get("photo", 0)
        videos = a["media_stats"].get("video", 0)
        lines.append(
            f"| {a['group_name']} | {a['total_messages']} | "
            f"{a['relevant_messages']} | {photos} | {videos} |"
        )
        total_msgs += a["total_messages"]
        total_relevant += a["relevant_messages"]
        for url, count in a["all_urls"]:
            all_urls_combined[url] += count
        for kw, count in a["top_keywords"]:
            all_keywords_combined[kw] += count

    lines.append(f"\n**Всего сообщений:** {total_msgs}")
    lines.append(f"**Релевантных:** {total_relevant}\n")

    # Топ ключевые слова
    lines.append("## Топ ключевые слова (по всем группам)\n")
    for kw, count in all_keywords_combined.most_common(30):
        lines.append(f"- **{kw}**: {count} упоминаний")

    # Топ ссылки
    lines.append("\n## Наиболее часто упоминаемые ссылки\n")
    for url, count in all_urls_combined.most_common(30):
        lines.append(f"- [{url}]({url}) ({count}x)")

    # Детали по каждой группе
    for a in analyses:
        lines.append(f"\n---\n## {a['group_name']}\n")

        if a["top_keywords"]:
            lines.append("### Ключевые темы\n")
            for kw, count in a["top_keywords"][:10]:
                lines.append(f"- {kw}: {count}")

        if a["top_viewed"]:
            lines.append("\n### Популярные сообщения\n")
            for msg in a["top_viewed"][:5]:
                text = (msg.get("text") or "")[:200]
                views = msg.get("views", 0)
                date = msg.get("date", "")[:10]
                lines.append(f"- [{date}] ({views} просмотров) {text}")

        # Релевантные сообщения
        if a["relevant_data"]:
            lines.append("\n### Ключевые сообщения\n")
            for msg in a["relevant_data"][:15]:
                text = (msg.get("text") or "")[:300]
                date = msg.get("date", "")[:10]
                kws = ", ".join(msg.get("_matched_keywords", [])[:3])
                lines.append(f"- [{date}] `[{kws}]` {text}\n")

    return "\n".join(lines)


def main(args):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Собираем ключевые слова
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",")]
    else:
        keywords = DEFAULT_KEYWORDS

    # Находим JSON-файлы
    json_files = sorted(OUTPUT_DIR.glob("*.json"))
    json_files = [f for f in json_files if f.name != "summary.json"]

    if not json_files:
        print(f"JSON-файлы не найдены в {OUTPUT_DIR}")
        print("Сначала запустите scraper.py для сбора данных.")
        sys.exit(1)

    print(f"Найдено {len(json_files)} файлов для анализа")
    print(f"Ключевых слов: {len(keywords)}\n")

    analyses = []
    for f in json_files:
        print(f"Анализ: {f.name}...")
        data = load_group_data(f)
        analysis = analyze_group(data, keywords)
        analyses.append(analysis)
        print(f"  {analysis['total_messages']} сообщений, {analysis['relevant_messages']} релевантных")

    # Генерируем отчёт
    report_md = generate_markdown_report(analyses)
    report_file = REPORT_DIR / f"telegram_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"\nОтчёт сохранён: {report_file}")

    # Сохраняем сырые данные анализа
    raw_file = REPORT_DIR / "analysis_raw.json"
    # Убираем несериализуемые данные
    for a in analyses:
        for msg in a.get("relevant_data", []):
            msg.pop("_matched_keywords", None)
    with open(raw_file, "w", encoding="utf-8") as f:
        json.dump(analyses, f, ensure_ascii=False, indent=2, default=str)
    print(f"Сырые данные: {raw_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telegram Data Analyzer")
    parser.add_argument(
        "--keywords",
        type=str,
        help="Ключевые слова через запятую (переопределяет встроенный список)",
    )
    args = parser.parse_args()
    main(args)
