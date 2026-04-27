#!/usr/bin/env python3
"""
Build a word cloud image from Jira export “Excel” data (HTML or real spreadsheets).

Jira’s “Excel (current fields)” download is often HTML saved as .xls; this script
reads the Labels column (and falls back to <td class="labels"> on HTML exports).

Usage:
  pip install pandas lxml beautifulsoup4 matplotlib wordcloud openpyxl
  python jira_labels_wordcloud.py "/path/to/Jira....xls" -o jira_labels_wordcloud.png

Writes two PNGs: labels-feature.png and labels-field.png (only `feature_*` and `field_*`
labels; prefixes are stripped and the remainder is shown in camelCase).
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from collections import Counter
from pathlib import Path

import matplotlib
import matplotlib.colors as mcolors

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _find_labels_column(df):
    for c in df.columns:
        s = str(c).strip().lower()
        if s == "labels":
            return c
    return None


def _load_frame_from_excel(path: Path):
    print("Loading frame from Excel")
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
            return [str(x).strip() for x in df[col] if pd.notna(x) and str(x).strip()]

    return []


def split_jira_labels(cell: str) -> list[str]:
    """Jira stores multiple labels in one cell separated by commas."""
    parts = re.split(r",\s*", cell.strip())
    return [p.strip() for p in parts if p.strip()]


def to_title_case(s: str) -> str:
    s = s.replace("_", " ")
    s = re.sub(r"(?<!^)(?=[A-Z])", " ", s)
    return s.title()


def _strip_prefix_casefold(label: str, prefix: str) -> str | None:
    if label.casefold().startswith(prefix.casefold()):
        return label[len(prefix) :]
    return None


def build_feature_field_frequencies(
    cells: list[str],
) -> tuple[dict[str, int], dict[str, int]]:
    """Count only labels starting with feature_ or field_; keys are camelCase suffixes."""
    feature_c: Counter[str] = Counter()
    field_c: Counter[str] = Counter()
    feature_p, field_p = "feature_", "field_"
    for cell in cells:
        for label in split_jira_labels(cell):
            rest = _strip_prefix_casefold(label, feature_p)
            if rest is not None:
                key = to_title_case(rest)
                if key:
                    feature_c[key] += 1
                continue
            rest = _strip_prefix_casefold(label, field_p)
            if rest is not None:
                key = to_title_case(rest)
                if key:
                    field_c[key] += 1
    return dict(feature_c), dict(field_c)


def _print_occurrence_table(title: str, freqs: dict[str, int]) -> None:
    print()
    print(title)
    if not freqs:
        print("  (none)")
        return
    rows = sorted(freqs.items(), key=lambda kv: (-kv[1], kv[0].casefold()))
    label_w = max(len(label) for label, _ in rows)
    label_w = max(label_w, len("Label"))
    print(f"{'Label':<{label_w}}  Count")
    print(f"{'-' * label_w}  -----")
    for label, count in rows:
        print(f"{label:<{label_w}}  {count}")


WORDCLOUD_COLORS = (
    "#00A65C",
    "#006362",
    "#00293F",
    "#4A1828",
    "#A13829",
    "#E98709",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Word cloud from a Jira issue export.")
    parser.add_argument(
        "input_path",
        type=Path,
        help="Jira .xls (HTML) export, .xlsx, or CSV with a Labels column",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("wordcloud.png"),
        help="Base output PNG path; writes <stem>-feature<suffix> and <stem>-field<suffix>",
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
            "No labels found.",
            file=sys.stderr,
        )
        return 1

    freqs_feature, freqs_field = build_feature_field_frequencies(cells)
    if args.min_count > 1:
        freqs_feature = {k: v for k, v in freqs_feature.items() if v >= args.min_count}
        freqs_field = {k: v for k, v in freqs_field.items() if v >= args.min_count}

    if not freqs_feature and not freqs_field:
        print(
            "No feature_* or field_* labels found (or all filtered by --min-count).",
            file=sys.stderr,
        )
        return 1

    from wordcloud import WordCloud

    def write_cloud(freqs: dict[str, int], out_path: Path) -> None:
        wc = WordCloud(
            width=args.width,
            height=args.height,
            background_color=args.background,
            # colormap="viridis",
            colormap=mcolors.LinearSegmentedColormap.from_list(
                "custom_cmap", WORDCLOUD_COLORS
            ),
        ).generate_from_frequencies(freqs)
        plt.figure(figsize=(args.width / 100, args.height / 100), dpi=100)
        plt.imshow(wc, interpolation="bilinear")
        plt.axis("off")
        plt.tight_layout(pad=0)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_path, bbox_inches="tight", pad_inches=0.1)
        plt.close()
        print(
            f"Wrote {out_path} ({len(freqs)} distinct labels, {sum(freqs.values())} total label hits)."
        )

    base = args.output
    out_feature = base.with_name(f"{base.stem}-feature{base.suffix}")
    out_field = base.with_name(f"{base.stem}-field{base.suffix}")

    if freqs_feature:
        write_cloud(freqs_feature, out_feature)
    else:
        print("No feature_* labels; skipped feature word cloud.", file=sys.stderr)

    if freqs_field:
        write_cloud(freqs_field, out_field)
    else:
        print("No field_* labels; skipped field word cloud.", file=sys.stderr)

    _print_occurrence_table("Labels by Feature", freqs_feature)
    _print_occurrence_table("Labels by Field", freqs_field)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
