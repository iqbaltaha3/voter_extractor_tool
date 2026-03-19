# Voter Extractor Tool

A modular, production‑ready tool to extract voter information from electoral roll PDFs. It converts PDF pages to images, performs OCR (Hindi + English), parses voter records, and outputs clean CSV files. The tool also supports merging all CSVs into a master file and transliterating Hindi fields to English (ITRANS).

---

## 📁 Repository Structure

```
voter_extractor_tool/           # Root folder (you can name it anything)
├── voter_tool/                  # The Python package (contains all code)
│   ├── __init__.py
│   ├── cli.py                   # Command-line interface
│   ├── config.py                 # Configuration handling
│   ├── utils.py                  # Shared helpers
│   ├── pdf_processor.py          # PDF → images
│   ├── ocr_engine.py             # OCR using Tesseract
│   ├── voter_parser.py           # Parse text into voter records
│   ├── csv_writer.py             # Write CSV + progress log
│   ├── master_merger.py          # Merge all CSVs
│   └── transliterator.py         # Hindi → English transliteration
├── requirements.txt              # Python dependencies
├── setup.py                      # (Optional) for installation
└── README.md                     # This file
```

---

## 🚀 Features

- ✅ **Parallel processing** – uses all CPU cores for fast batch processing  
- ✅ **Graceful shutdown** – press `Ctrl+C` to stop safely without corrupting data  
- ✅ **Progress logging** – resumes from where it left off if interrupted  
- ✅ **CSV output** – one CSV per booth, with fields: Booth, Name, Father/Husband, House, Age, Gender, EPIC  
- ✅ **Master merge** – combines all CSVs into a single master CSV  
- ✅ **Transliteration** – converts Hindi text to English (ITRANS) using `indic-transliteration`  
- ✅ **Configurable defaults** – set your preferred folders once via config file or environment variables  
- ✅ **Modular design** – easy to extend or reuse components  

---

## 📋 Prerequisites

- **Python 3.8 or higher** – [Download](https://www.python.org/downloads/)
- **Tesseract OCR** (with Hindi language data)
- **Poppler** (for PDF to image conversion)

---

## 🔧 Installation

### 1. Install System Dependencies

#### macOS (Homebrew)
```bash
brew install tesseract tesseract-lang  # includes Hindi language data
brew install poppler
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-hin poppler-utils
```

#### Windows
- Download Tesseract from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki) and install (check "Add to PATH").
- Download Poppler from [here](http://blog.alivate.com.au/poppler-windows/) and add its `bin` folder to PATH.

### 2. Clone the Repository

```bash
git clone https://github.com/yourusername/voter_extractor_tool.git
cd voter_extractor_tool
```

### 3. Install Python Dependencies

Inside the `voter_extractor_tool` folder, run:

```bash
pip install -r requirements.txt
```

*(Optional)* If you want to install the package so you can use the `voter-tool` command from anywhere:

```bash
pip install -e .
```

---

## 🎯 How to Use

### Important: Where to Run Commands

You must run all commands from the **root folder** (`voter_extractor_tool`), **not** from inside the `voter_tool` subfolder.

Example:
```bash
# ✅ Correct – from the root folder
cd /path/to/voter_extractor_tool
python -m voter_tool.cli --help

# ❌ Wrong – from inside voter_tool
cd voter_tool
python -m voter_tool.cli --help   # This will fail!
```

### Step 1: Set Default Folders (Recommended)

Run the interactive setup to tell the tool where your PDFs are and where to save results:

```bash
python -m voter_tool.cli init
```

You will be asked:

- **Default PDF folder path** – the full path to the folder **containing your PDF files**.  
  Example: `/Users/yourname/Documents/electoral_rolls`  
  (This folder should contain `.pdf` files, not the PDFs themselves.)

- **Default CSV output folder** – the folder where individual CSV files will be saved.  
  Example: `/Users/yourname/Documents/voter_output`

- **Default master CSV output path** – (optional) full path for the merged master CSV file.  
  If you leave it blank, it will be saved as `master.csv` inside the output folder.  
  If you provide a value, it must be a **file path**, not a folder:  
  ✅ `/Users/yourname/Documents/voter_output/master.csv`  
  ❌ `/Users/yourname/Documents/voter_output/` (this will cause an error)

- **Default transliterated CSV output path** – (optional) full path for the English version.  
  Leave blank for default (`master_english.csv` inside output folder), or provide a full file path.

After this, your settings are saved in `~/.voter_tool/config.yaml`. You can edit this file later if needed.

### Step 2: Run the Full Pipeline (Extract → Merge → Transliterate)

Once defaults are set, simply run:

```bash
python -m voter_tool.cli run
```

This will:
1. Scan the default PDF folder for all `.pdf` files.
2. Process them in parallel, extracting voter data.
3. Save one CSV per booth in the output folder.
4. Create a progress log (`processed.log`) to allow resuming after an interruption.
5. Merge all CSVs into `master.csv` (or your custom path).
6. Transliterate the master CSV to English (saved as `master_english.csv` or your custom path).

You will see live progress in the terminal. Press `Ctrl+C` anytime to stop gracefully – already processed PDFs are marked as done and will be skipped next time.

### Step 3: Check the Results

Navigate to your output folder and you'll find:
- Individual CSV files named after the booth (e.g., `Booth_Name.csv`)
- `processed.log` – list of successfully processed PDFs
- `master.csv` – all voters combined
- `master_english.csv` – transliterated version (if enabled)

---

## 🧩 Running Individual Steps

If you prefer to run each step separately, use these commands:

### Extract Only
```bash
python -m voter_tool.cli extract --folder /path/to/pdfs --output /path/to/csvs
```
- `--folder` : folder containing PDFs (required if not set in config)
- `--output` : folder for CSV output (required if not set in config)

### Merge Only
```bash
python -m voter_tool.cli merge --folder /path/to/csvs --output /path/to/master.csv
```
- `--folder` : folder containing the individual CSV files
- `--output` : full path for the merged master CSV file

### Transliterate Only
```bash
python -m voter_tool.cli transliterate --input /path/to/master.csv --output /path/to/english.csv
```
- `--input` : path to the master CSV file
- `--output` : path for the transliterated CSV file

If you have set defaults via `init`, you can omit the arguments and the tool will use your saved paths.

---

## ⚙️ Configuration Details

The tool looks for settings in this order (highest priority first):

1. **Command‑line arguments** (e.g., `--folder`, `--output`)
2. **Environment variables** (see table below)
3. **Configuration file** (`~/.voter_tool/config.yaml`)
4. **Interactive prompt** (if not in `--non-interactive` mode)

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `VOTER_PDF_FOLDER` | Default folder containing PDFs |
| `VOTER_CSV_OUTPUT` | Default folder for individual CSV files |
| `VOTER_MASTER_OUTPUT` | Default path for master CSV (must be a file path) |
| `VOTER_ENGLISH_OUTPUT` | Default path for transliterated CSV (must be a file path) |

### Configuration File (`~/.voter_tool/config.yaml`)

Example:
```yaml
pdf_folder: /Users/username/Documents/pdfs
csv_output: /Users/username/Documents/csvs
master_output: /Users/username/Documents/csvs/master.csv
english_output: /Users/username/Documents/csvs/master_english.csv
```

You can edit this file directly to change defaults.

---

## ❗ Troubleshooting

| Problem | Solution |
|---------|----------|
| **`ModuleNotFoundError: No module named 'voter_tool'`** | You are running the command from inside the `voter_tool` folder. Go up one level to the root folder (`voter_extractor_tool`) and try again. |
| **`IsADirectoryError: [Errno 21] Is a directory`** | You provided a **folder path** where a **file path** was expected. Check your `master_output` or `english_output` settings – they must be full file paths (e.g., `/path/to/master.csv`), not directories. |
| **Tesseract not found** | Install Tesseract OCR (see installation section). On macOS, run `brew install tesseract`. |
| **PDF conversion fails** | Install Poppler. On macOS, run `brew install poppler`. On Ubuntu, `sudo apt install poppler-utils`. |
| **OCR quality is poor** | Try increasing the DPI by adding `--dpi 600` to the extract command. Default is 400. |
| **The tool stops on one PDF error** | Errors in one PDF do not stop the whole batch. The failed PDF is logged and skipped; processing continues. |
| **I want to resume after interruption** | The tool automatically uses `processed.log` to skip already processed PDFs. Just run the same command again. |
| **I forgot what defaults I set** | Run `python -m voter_tool.cli init` again to see or change them. |

---

## 🧪 Testing with a Few PDFs

1. Create a test folder, e.g., `~/test_pdfs`, and copy 2–3 sample PDFs into it.
2. Run `init` to set that folder as your default:
   ```bash
   python -m voter_tool.cli init
   ```
   - PDF folder: `~/test_pdfs`
   - CSV output: `~/test_output`
   - Leave master and English paths blank.
3. Run the full pipeline:
   ```bash
   python -m voter_tool.cli run
   ```
4. Check `~/test_output` for results.

---

## 📦 Installing as a Package (Optional)

If you want to use the `voter-tool` command from anywhere, install the package:

```bash
cd /path/to/voter_extractor_tool
pip install -e .
```

Then you can run:
```bash
voter-tool init
voter-tool run
```

The commands work the same as the `python -m` versions.
