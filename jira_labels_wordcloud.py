#!/usr/bin/env python3
"""
Build a word cloud image from Jira export “Excel” data (HTML or real spreadsheets).

Jira’s “Excel (current fields)” download is often HTML saved as .xls; this script
reads the Labels column (and falls back to <td class="labels"> on HTML exports).

Usage:
  pip install pandas lxml beautifulsoup4 matplotlib wordcloud openpyxl
  python tools/jira_labels_wordcloud.py "/path/to/Jira....xls" -o labels.png
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _find_labels_column(df):
    for c in df.columns:
        s = str(c).strip().lower()
        if s == "labels":
            return c
    for c in df.columns:
        if "label" in str(c).lower():
            return c
    return None


def _load_frame_from_excel(path: Path):
    import pandas as pd  # noqa: PLC0415

    for engine in ("openpyxl", "calamine", "xlrd"):
        try:
            return pd.read_excel(path, engine=engine)
        except (ValueError, ImportError, Exception):
            continue
    return None


def load_label_strings(path: Path) -> list[str]:
    import pandas as pd

    raw = path.read_bytes()
    head = raw[:2048].lstrip()

    # Jira HTML export disguised as .xls / .xls
    if head.startswith(b"<") or b"issuetable" in raw[:8192]:
        text = raw.decode("utf-8", errors="replace")

        try:
            dfs = pd.read_html(io.StringIO(text), attrs={"id": "issuetable"})
            if dfs:
                df = dfs[0]
                col = _find_labels_column(df)
                if col is not None:
                    return [
                        str(x).strip()
                        for x in df[col]
                        if pd.notna(x) and str(x).strip()
                    ]
        except (ValueError, ImportError):
            pass

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(text, "lxml")
            cells = [td.get_text(" ", strip=True) for td in soup.select("td.labels")]
            return [c for c in cells if c]
        except ImportError:
            pass

    # Real Excel / CSV
    df = _load_frame_from_excel(path)
    if df is not None:
        col = _find_labels_column(df)
        if col is not None:
            return [str(x).strip() for x in df[col] if pd.notna(x) and str(x).strip()]

    if path.suffix.lower() == ".csv":
        import pandas as pd

        df = pd.read_csv(path)
        col = _find_labels_column(df)
        if col is not None:
            return [
                str(x).strip()
                for x in df[col]
                if pd.notna(x) and str(x).strip()
            ]

    return []


def split_jira_labels(cell: str) -> list[str]:
    """Jira stores multiple labels in one cell separated by commas."""
    parts = re.split(r",\s*", cell.strip())
    return [p.strip() for p in parts if p.strip()]


def build_frequencies(cells: list[str]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for cell in cells:
        for label in split_jira_labels(cell):
            c[label] += 1
    return dict(c)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Word cloud from a Jira issue export’s Labels column."
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Jira .xls (HTML) export, .xlsx, or CSV with a Labels column",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("labels_wordcloud.png"),
        help="Output PNG path (default: labels_wordcloud.png)",
    )
    parser.add_argument("--width", type=int, default=1200, help="Image width in px")
    parser.add_argument("--height", type=int, default=800, help="Image height in px")
    parser.add_argument(
        "--min-count",
        type=int,
        default=1,
        help="Drop labels with frequency below this (default: 1)",
    )
    parser.add_argument(
        "--background",
        default="white",
        help="Word cloud background color (default: white)",
    )
    args = parser.parse_args()

    if not args.input_path.is_file():
        print(f"File not found: {args.input_path}", file=sys.stderr)
        return 1

    cells = load_label_strings(args.input_path)
    if not cells:
        print(
            "No label text found. For HTML exports, install: pandas lxml beautifulsoup4",
            file=sys.stderr,
        )
        return 1

    freqs = build_frequencies(cells)
    if args.min_count > 1:
        freqs = {k: v for k, v in freqs.items() if v >= args.min_count}

    if not freqs:
        print("No label tokens after parsing (empty column or all filtered).", file=sys.stderr)
        return 1

    from wordcloud import WordCloud

    wc = WordCloud(
        width=args.width,
        height=args.height,
        background_color=args.background,
        colormap="viridis",
        prefer_horizontal=0.7,
    ).generate_from_frequencies(freqs)

    plt.figure(figsize=(args.width / 100, args.height / 100), dpi=100)
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout(pad=0)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(args.output, bbox_inches="tight", pad_inches=0.1)
    plt.close()
    print(
        f"Wrote {args.output} ({len(freqs)} distinct labels, {sum(freqs.values())} total label hits)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
