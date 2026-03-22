# caste_enrichment.py – Voter Data Enrichment & Analysis

This script takes a master voter CSV (with columns `Name`, `Father_Husband`, `Booth`, `House`, etc.) and enriches it with:

- **Religion** – using the `pranaam` library (Muslim / non‑Muslim)
- **Caste** – via a surname‑lookup CSV and propagation (intra‑house, neighbourhood, booth‑level)
- **Household ID** – created automatically for analysis
- **Comprehensive statistics** – saved as a text report

It handles OCR artifacts (e.g., trailing ‘a’ in names) with fuzzy matching and parallel processing for speed.

---

## Features

- **Robust CSV loading** – skips malformed rows, falls back to line‑by‑line parsing.
- **Parallel initial caste assignment** – uses all CPU cores for speed.
- **Fuzzy surname matching** – handles transliteration variations.
- **Caste propagation** – fills missing castes using:
  - Intra‑house consensus
  - Neighbourhood windows (adjustable size & passes)
  - Booth‑level majority (last resort)
- **Religion prediction** – via Pranaam (Muslim / Hindu).
- **Automatic report** – generates `summary_stats.txt` with:
  - Category, religion, gender, age distributions
  - Household size statistics
  - Top surnames per category
  - Numeric summaries and correlation matrix
  - EPIC data quality
- **All rows preserved** – no deletion of missing data.

---

## Requirements

- Python 3.8 or higher
- Dependencies (install via `pip install -r requirements.txt`):
  ```
  pandas numpy rapidfuzz pranaam
  ```
- System libraries for `pranaam` (see [pranaam docs](https://github.com/appeler/pranaam) for Tesseract/poppler if needed – not strictly required for this script).

---

## Installation

1. Clone or download the script.
2. Install Python packages:
   ```bash
   pip install pandas numpy rapidfuzz pranaam
   ```
3. Place your **master voter CSV** and **caste lookup CSV** in accessible paths.

---

## Configuration

Edit the top of the script to set your file paths and parameters:

```python
MASTER_CSV = "/path/to/master_final.csv"
LOOKUP_CSV = "/path/to/caste_lookup.csv"
OUTPUT_CSV = "/path/to/master_enriched.csv"

MAX_WORKERS = os.cpu_count()      # number of parallel processes
FUZZY_THRESHOLD = 60              # 0–100; lower = more matches
NEIGHBOR_WINDOW = 5               # rows to consider left/right
NEIGHBOR_PASSES = 3               # number of propagation passes
ANALYSIS_OUTPUT_TXT = "summary_stats.txt"
```

**Caste Lookup CSV format** – must have columns: `surname`, `caste`, `category` (e.g., `yadav, Yadav, OBC`). All surnames should be lowercase.

---

## Usage

Run the script from the command line:

```bash
python caste_enrichment.py
```

It will:

1. Load the master CSV.
2. Predict religion using Pranaam.
3. Load the caste lookup.
4. Assign initial caste (parallel, with fuzzy matching).
5. Propagate caste within houses, then neighbourhood (multiple passes), then by booth.
6. Replace any remaining `Unknown` with `Other`.
7. Save the enriched CSV.
8. Run a detailed analysis and write `summary_stats.txt`.

---

## Output

### Enriched CSV (`OUTPUT_CSV`)
All original columns plus:
- `religion` – `Muslim` / `Hindu`
- `religion_prob` – probability of being Muslim
- `caste` – specific caste name (e.g., `Yadav`, `Brahmin`)
- `category` – `SC`, `ST`, `OBC`, `General`, `Other`

### Analysis Report (`summary_stats.txt`)
- Category, religion, gender, age group distributions
- Cross‑tabulation of category vs. religion
- Household counts and size distribution
- Top 10 surnames per category
- Numeric summary of any numeric columns
- Correlation matrix (if multiple numeric columns)
- EPIC missing/duplicate statistics

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'pranaam'` | Install Pranaam: `pip install pranaam` |
| `FileNotFoundError: LOOKUP_CSV` | Check the path to your caste lookup CSV. |
| CSV rows are being skipped | The script automatically skips malformed rows; check the console for messages. |
| Too many `Unknown` castes after propagation | Increase `NEIGHBOR_WINDOW` or `NEIGHBOR_PASSES`. You can also adjust `FUZZY_THRESHOLD` to get more matches. |
| Muslims being assigned SC/ST | This is handled automatically in the final cleanup; the script sets all Muslims to `Other` if misclassified. If you need Muslims to remain in OBC/General, comment out that section. |

---

