# xtrem-word-cloud

Generate word cloud images from Jira issue exports by reading the **Labels** column.

## What it does

`jira_labels_wordcloud.py` reads a Jira export (spreadsheet or HTML) and counts labels that start with `feature_` or `field_`. It then:

- Builds two PNG word clouds:
  - **Feature** — only labels prefixed with `feature_`. The prefix is removed; the rest is shown in title case (camelCase-friendly).
  - **Field** — same for labels prefixed with `field_`.

- Prints two **occurrence tables** to stdout (`Labels by Feature`, `Labels by Field`): label and count, sorted by frequency then name.

If one category has no labels after filtering, that PNG is skipped and a short message is printed to stderr.

**Supported inputs**

- Jira **“Excel (current fields)”** downloads that are actually **HTML** saved as `.xls` — the script detects HTML and parses the issue table (`id="issuetable"`) or falls back to `td.labels` cells.
- Real **Excel** (`.xlsx` / `.xls`) via pandas (tries engines `openpyxl`, `calamine`, `xlrd` in order).
- **CSV** with a `Labels` column.

The script looks for a column named **Labels** (case-insensitive). Jira cells can contain several labels separated by commas; those are split and counted individually.

## Requirements

Install dependencies with **pip**:

```bash
python3 -m pip install -r requirements.txt
```

Or install the packages the script needs directly:

```bash
python3 -m pip install pandas lxml beautifulsoup4 matplotlib wordcloud openpyxl
```

Optional Excel readers used by pandas when present: `python-calamine`, `xlrd`.

## Running the script

```bash
python3 jira_labels_wordcloud.py /path/to/Jira-export.xls -o wordcloud.png
```

### Command-line options

| Option           | Default         | Description                                                                                                                                                                                            |
| ---------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `input_path`     | —               | Path to the Jira export (`.xls` HTML, `.xlsx`, `.csv`, etc.) with a **Labels** column.                                                                                                                 |
| `-o`, `--output` | `wordcloud.png` | **Base** path for PNG output. Two files are written: `<stem>-feature<suffix>` and `<stem>-field<suffix>`. Example: `-o out/wordcloud.png` → `out/wordcloud-feature.png` and `out/wordcloud-field.png`. |
| `--width`        | `1200`          | Image width in pixels.                                                                                                                                                                                 |
| `--height`       | `800`           | Image height in pixels.                                                                                                                                                                                |
| `--min-count`    | `1`             | Drop labels whose count is strictly below this value (applied separately to feature and field frequencies).                                                                                            |
| `--background`   | `white`         | Word cloud background color (any color matplotlib accepts).                                                                                                                                            |

Exit code `1` is used if the file is missing, no labels were found, or no `feature_*` / `field_*` labels remain (or all were removed by `--min-count`).

## Makefile (PyInstaller builds)

The `Makefile` builds a **single-file native binary** of the script with PyInstaller. There is **no cross-compilation**: run `make macos` on macOS and `make windows` on Windows (or use CI for both).

### Targets

| Target         | Description                                                                                             |
| -------------- | ------------------------------------------------------------------------------------------------------- |
| `make help`    | Print a short summary of targets (same text as in the comments at the top of the Makefile).             |
| `make macos`   | One-file app for **macOS only** → `dist/jira-labels-wordcloud`. Fails if not run on Darwin.             |
| `make windows` | One-file **Windows** `.exe` → `dist/jira-labels-wordcloud.exe`. Fails if not run on Windows.            |
| `make build`   | Runs `make macos` on macOS or `make windows` on Windows. **Fails** on Linux or other unsupported hosts. |
| `make clean`   | Removes PyInstaller `build/`, `dist/`, and `jira-labels-wordcloud.spec`.                                |

### Variables

| Variable      | Default                    | Description                                                                                                   |
| ------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `PYTHON`      | `python3`                  | Interpreter used for `python -m PyInstaller`. Override to use a venv, e.g. `export PYTHON=.venv/bin/python3`. |
| `SCRIPT`      | `jira_labels_wordcloud.py` | Entry script passed to PyInstaller.                                                                           |
| `APP_NAME`    | `jira-labels-wordcloud`    | PyInstaller `--name` and artifact base name.                                                                  |
| `PYINSTALLER` | `$(PYTHON) -m PyInstaller` | How PyInstaller is invoked.                                                                                   |

**Prerequisites for `make`:** install dependencies and PyInstaller, for example:

```bash
python3 -m pip install -r requirements.txt
```

(or at least the runtime packages above plus `pyinstaller`).

The bundled app configures matplotlib’s cache under `~/.cache/jira-labels-wordcloud/matplotlib` when running the frozen binary so font/config paths stay stable between runs.
