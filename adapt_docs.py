#!/usr/bin/env python3
"""
Адаптирует markdown-файлы из research/ для MkDocs wiki.
- Копирует файлы с латинскими именами
- Удаляет ручные оглавления
- Конвертирует предупреждения в admonitions
- Добавляет кросс-ссылки
- Встраивает визуализации
- Добавляет навигацию между главами
"""

import re
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent
RESEARCH = BASE / "research"
DOCS = BASE / "docs"

# Mapping: source filename -> (target filename, nav title, chapter number)
FILE_MAP = {
    "00_executive_summary.md": ("index.md", "Резюме для руководства", 0),
    "01_глобальный_рынок_vr_ar.md": ("01-global-market.md", "Гл.1. Глобальный рынок VR/AR", 1),
    "02_российский_рынок_vr_ar.md": ("02-russian-market.md", "Гл.2. Российский рынок VR/AR", 2),
    "03_vr_в_культуре_мировой_опыт.md": ("03-culture-world.md", "Гл.3. VR в культуре: мировой опыт", 3),
    "04_государственные_vr_экосистемы.md": ("04-government-ecosystems.md", "Гл.4. Государственные VR-экосистемы", 4),
    "05_технологический_стек_2025.md": ("05-tech-stack.md", "Гл.5. Технологический стек", 5),
    "06_ai_генеративные_технологии.md": ("06-ai-generative.md", "Гл.6. AI и генеративные технологии", 6),
    "07_платформы_дистрибуции.md": ("07-distribution.md", "Гл.7. Платформы дистрибуции", 7),
    "08_доступность_и_инклюзия.md": ("08-accessibility.md", "Гл.8. Доступность и инклюзия", 8),
    "09_кадры_и_компетенции.md": ("09-workforce.md", "Гл.9. Кадры и компетенции", 9),
    "10_правовое_регулирование.md": ("10-legal.md", "Гл.10. Правовое регулирование", 10),
    "11_финансовые_модели.md": ("11-financial-models.md", "Гл.11. Финансовые модели", 11),
    "12_риски_и_рекомендации.md": ("12-risks.md", "Гл.12. Риски и рекомендации", 12),
    "13_дорожная_карта.md": ("13-roadmap.md", "Гл.13. Дорожная карта", 13),
}

# Chapter number -> filename mapping for cross-references
CHAPTER_FILES = {
    0: "index.md",
    1: "01-global-market.md",
    2: "02-russian-market.md",
    3: "03-culture-world.md",
    4: "04-government-ecosystems.md",
    5: "05-tech-stack.md",
    6: "06-ai-generative.md",
    7: "07-distribution.md",
    8: "08-accessibility.md",
    9: "09-workforce.md",
    10: "10-legal.md",
    11: "11-financial-models.md",
    12: "12-risks.md",
    13: "13-roadmap.md",
}

CHAPTER_TITLES = {
    0: "Резюме",
    1: "Глобальный рынок VR/AR",
    2: "Российский рынок VR/AR",
    3: "VR в культуре",
    4: "Государственные экосистемы",
    5: "Технологический стек",
    6: "AI и генеративные технологии",
    7: "Платформы дистрибуции",
    8: "Доступность и инклюзия",
    9: "Кадры и компетенции",
    10: "Правовое регулирование",
    11: "Финансовые модели",
    12: "Риски и рекомендации",
    13: "Дорожная карта",
}

# Visualizations mapping: viz file -> chapter number
VIZ_MAP = {
    1: [("01_market_global.html", 800)],
    2: [("02_market_russia.html", 800)],
    5: [("06_technology.html", 700)],
    9: [("08_team_growth.html", 600)],
    11: [("03_financial_model.html", 700), ("09_content_costs.html", 600),
         ("10_benchmarks.html", 600), ("12_revenue_mix.html", 600)],
    12: [("05_risk_matrix.html", 700)],
    13: [("04_budget.html", 600), ("07_roadmap.html", 700), ("11_kpi_dashboard.html", 600)],
}


def remove_manual_toc(text):
    """Remove manual table of contents sections."""
    # Pattern: lines starting with "## Содержание" or "## Оглавление" followed by list items
    # Also catch "---" separated TOC blocks
    lines = text.split('\n')
    result = []
    skip_toc = False
    toc_headers = ['## содержание', '## оглавление', '## содержание главы']

    i = 0
    while i < len(lines):
        line = lines[i]
        lower_line = line.strip().lower()

        # Detect TOC section start
        if any(lower_line.startswith(h) for h in toc_headers):
            skip_toc = True
            i += 1
            continue

        if skip_toc:
            stripped = line.strip()
            # TOC items are typically: "- [Section Name](#anchor)" or empty lines
            if stripped.startswith('- [') or stripped.startswith('  - [') or stripped == '' or stripped.startswith('---'):
                if stripped.startswith('---'):
                    skip_toc = False
                    # Don't add the --- line itself
                i += 1
                continue
            else:
                skip_toc = False
                # Continue to add this non-TOC line

        result.append(line)
        i += 1

    return '\n'.join(result)


def convert_blockquote_warnings(text):
    """Convert > ⚠️ ... blockquotes to Material admonitions."""
    lines = text.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Detect warning blockquote: > **⚠️ ... or > ⚠️ ...
        if re.match(r'^>\s*\*?\*?⚠️', line):
            # Extract title from this line
            title_match = re.match(r'^>\s*\*?\*?⚠️\s*(.+?)\.?\*?\*?\s*$', line)
            title = title_match.group(1).strip().rstrip('*').strip() if title_match else "Внимание"
            title = title.rstrip('.')

            # Collect all subsequent blockquote lines
            body_lines = []
            i += 1
            while i < len(lines) and lines[i].startswith('>'):
                content = lines[i].lstrip('>').strip()
                if content:
                    body_lines.append(content)
                i += 1

            # Build admonition
            result.append(f'!!! warning "{title}"')
            for bline in body_lines:
                result.append(f'    {bline}')
            result.append('')
            continue

        # Detect info/update blockquotes: > **Обновление... or > **Примечание...
        if re.match(r'^>\s*\*\*(?:Обновление|Примечание|Важно|Дополнение)', line):
            title_match = re.match(r'^>\s*\*\*(.+?)\.\*\*\s*(.*)?$', line)
            if title_match:
                title = title_match.group(1).strip()
                first_content = title_match.group(2).strip() if title_match.group(2) else ""

                body_lines = []
                if first_content:
                    body_lines.append(first_content)
                i += 1
                while i < len(lines) and lines[i].startswith('>'):
                    content = lines[i].lstrip('>').strip()
                    if content:
                        body_lines.append(content)
                    i += 1

                adm_type = "info"
                if "обновлен" in title.lower():
                    adm_type = "tip"
                elif "важно" in title.lower():
                    adm_type = "warning"

                result.append(f'!!! {adm_type} "{title}"')
                for bline in body_lines:
                    result.append(f'    {bline}')
                result.append('')
                continue

        result.append(line)
        i += 1

    return '\n'.join(result)


def add_cross_references(text, current_chapter):
    """Replace textual chapter references with markdown links."""

    # Pattern: "глав[уеа] X" -> link
    # Handle: главу 5, главе 3, глава 1, Глава 12
    def replace_single_chapter(match):
        prefix = match.group(1)  # глав[уеа] or Глав[уеа]
        num = int(match.group(2))
        if num in CHAPTER_FILES and num != current_chapter:
            return f'[{prefix} {num}]({CHAPTER_FILES[num]})'
        return match.group(0)

    text = re.sub(r'((?:Г|г)лав[уеаы])\s+(\d{1,2})(?!\d)(?![\-–])', replace_single_chapter, text)

    # Pattern: "главы X-Y" or "главы X–Y"
    def replace_chapter_range(match):
        prefix = match.group(1)
        num1 = int(match.group(2))
        sep = match.group(3)
        num2 = int(match.group(4))
        parts = []
        if num1 in CHAPTER_FILES and num1 != current_chapter:
            parts.append(f'[{num1}]({CHAPTER_FILES[num1]})')
        else:
            parts.append(str(num1))
        if num2 in CHAPTER_FILES and num2 != current_chapter:
            parts.append(f'[{num2}]({CHAPTER_FILES[num2]})')
        else:
            parts.append(str(num2))
        return f'{prefix} {parts[0]}–{parts[1]}'

    text = re.sub(r'((?:Г|г)лав[ыа])\s+(\d{1,2})[\-–](\s*)(\d{1,2})', replace_chapter_range, text)

    # Pattern: in tables "| X, Y |" where X and Y are chapter numbers in "Глава" column
    # Handle: "| 2, 4 |" -> "| [2](02-russian-market.md), [4](04-government-ecosystems.md) |"
    # This is tricky, let's handle the executive summary table format: "| X, Y |" at end of row
    def replace_table_chapters(match):
        nums_str = match.group(1)
        nums = re.findall(r'\d+', nums_str)
        parts = []
        for n_str in nums:
            n = int(n_str)
            if n in CHAPTER_FILES:
                parts.append(f'[{n}]({CHAPTER_FILES[n]})')
            else:
                parts.append(n_str)
        return '| ' + ', '.join(parts) + ' |'

    # Only for executive summary (index.md)
    if current_chapter == 0:
        text = re.sub(r'\|\s*([\d,\s]+)\s*\|$', replace_table_chapters, text, flags=re.MULTILINE)

    return text


def convert_metadata_header(text):
    """Convert metadata block at start of chapter to admonition."""
    lines = text.split('\n')

    # Look for metadata patterns near the top (lines 2-15)
    meta_lines = []
    meta_start = -1
    meta_end = -1

    for i in range(min(20, len(lines))):
        line = lines[i].strip()
        # Typical metadata: **Agent Type:** ..., **Дата:** ..., **Версия:** ...
        if re.match(r'^\*\*(?:Agent Type|Дата|Версия|Для|Объём|Горизонт).*?\*\*', line):
            if meta_start == -1:
                meta_start = i
            meta_lines.append(line)
            meta_end = i

    if meta_lines and meta_start > 0:
        # Build admonition
        adm = ['', '!!! info "Метаданные"']
        for ml in meta_lines:
            adm.append(f'    {ml}')
        adm.append('')

        # Replace the metadata lines
        new_lines = lines[:meta_start] + adm + lines[meta_end + 1:]
        return '\n'.join(new_lines)

    return text


def add_viz_embeds(text, chapter_num):
    """Add visualization iframes at the end of the chapter, before sources."""
    if chapter_num not in VIZ_MAP:
        return text

    viz_list = VIZ_MAP[chapter_num]

    viz_block = ['\n---\n', '## Интерактивные визуализации\n']

    for viz_file, height in viz_list:
        # Nice title from filename
        viz_name = viz_file.replace('.html', '').replace('_', ' ').title()
        viz_block.append(f'<div class="viz-container" markdown="0">')
        viz_block.append(f'  <iframe src="viz/{viz_file}" width="100%" height="{height}" frameborder="0"></iframe>')
        viz_block.append(f'</div>\n')
        viz_block.append(f'[Открыть в полном окне](viz/{viz_file}){{target=_blank}}\n')

    # Insert before "## Источники" or at end
    source_match = re.search(r'\n## (?:Источники|Список источников|Литература)\b', text)
    if source_match:
        insert_pos = source_match.start()
        return text[:insert_pos] + '\n'.join(viz_block) + '\n' + text[insert_pos:]
    else:
        return text + '\n'.join(viz_block)


def add_chapter_navigation(text, chapter_num):
    """Add prev/next chapter navigation footer."""
    nav_parts = []

    if chapter_num > 0:
        prev_num = chapter_num - 1
        if prev_num == 0:
            nav_parts.append(f'[← Резюме](index.md)')
        else:
            prev_file = CHAPTER_FILES[prev_num]
            prev_title = CHAPTER_TITLES[prev_num]
            nav_parts.append(f'[← Гл.{prev_num}. {prev_title}]({prev_file})')

    if chapter_num < 13:
        next_num = chapter_num + 1
        next_file = CHAPTER_FILES[next_num]
        next_title = CHAPTER_TITLES[next_num]
        nav_parts.append(f'[Гл.{next_num}. {next_title} →]({next_file})')

    if nav_parts:
        nav_line = ' | '.join(nav_parts)
        text = text.rstrip() + f'\n\n---\n\n<div class="chapter-nav" markdown="0">\n{nav_line}\n</div>\n'

    return text


def process_file(src_name, target_name, chapter_num):
    """Process a single research file for MkDocs."""
    src_path = RESEARCH / src_name
    target_path = DOCS / target_name

    print(f"  {src_name} → {target_name}")

    text = src_path.read_text(encoding='utf-8')

    # Step 1: Remove manual TOC
    text = remove_manual_toc(text)

    # Step 2: Convert blockquote warnings to admonitions
    text = convert_blockquote_warnings(text)

    # Step 3: Convert metadata header (skip for executive summary - has different format)
    if chapter_num > 0:
        text = convert_metadata_header(text)

    # Step 4: Add cross-references
    text = add_cross_references(text, chapter_num)

    # Step 5: Add visualization embeds
    text = add_viz_embeds(text, chapter_num)

    # Step 6: Add chapter navigation
    text = add_chapter_navigation(text, chapter_num)

    target_path.write_text(text, encoding='utf-8')


def main():
    print("=== Адаптация markdown-файлов для MkDocs ===\n")

    for src_name, (target_name, nav_title, chapter_num) in FILE_MAP.items():
        src_path = RESEARCH / src_name
        if src_path.exists():
            process_file(src_name, target_name, chapter_num)
        else:
            print(f"  ⚠️ НЕ НАЙДЕН: {src_name}")

    print(f"\n✅ Обработано файлов: {len(FILE_MAP)}")
    print(f"📁 Результат: {DOCS}/")


if __name__ == "__main__":
    main()
