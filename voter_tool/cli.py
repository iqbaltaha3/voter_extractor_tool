#!/usr/bin/env python3
import argparse
import sys
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from . import master_merger, transliterator

from voter_tool import utils
from voter_tool.config import ExtractorConfig, load_config, save_config, prompt_for_config
from voter_tool.pdf_processor import PDFProcessor
from voter_tool.ocr_engine import OCREngine
from voter_tool.voter_parser import parse_voter_lines
from voter_tool.csv_writer import CSVWriter
from voter_tool import master_merger, transliterator

# ----------------------------------------------------------------------
# Helper: interactive prompt for missing arguments
def get_param(args, key, env_var, config_key, prompt_msg):
    """Return value from args, then env, then config, else ask user."""
    if getattr(args, key, None):
        return getattr(args, key)
    if env_var and os.environ.get(env_var):
        return os.environ[env_var]
    config = load_config()
    if config_key and config.get(config_key):
        return config[config_key]
    # If we are in non-interactive mode, raise error
    if args.non_interactive:
        raise ValueError(f"Missing required argument: {key}")
    return input(prompt_msg).strip()

# ----------------------------------------------------------------------
def process_one_pdf(pdf_path, output_folder, dpi, progress_log):
    """Process a single PDF: extract voters and save CSV."""
    if utils.INTERRUPTED:
        return None

    print(f"\n📄 Processing: {pdf_path.name}")

    # Convert PDF to images
    try:
        processor = PDFProcessor(dpi=dpi)
        images = processor.convert(pdf_path)
    except Exception as e:
        print(f"  ❌ Failed to read PDF: {e}")
        return None

    # Extract booth name
    booth_name = utils.extract_booth_name_from_images(images, pdf_path.stem)
    print(f"  ✅ Booth name : {booth_name}")

    # OCR each page (skip first two)
    ocr = OCREngine()
    all_voters = []
    for page_num, pil_img in enumerate(images[2:], start=3):
        if utils.INTERRUPTED:
            break
        print(f"  Processing Page {page_num}...")
        text = ocr.extract_text(pil_img)
        lines = utils.preprocess_lines(text)
        page_voters = parse_voter_lines(lines, booth_name)
        all_voters.extend(page_voters)

    # Save CSV
    writer = CSVWriter(output_folder, progress_log)
    csv_path, count = writer.save(all_voters, booth_name, pdf_path.stem)
    print(f"  ✅ CSV saved → {csv_path.name} ({count} voters)")
    return pdf_path.name

# ----------------------------------------------------------------------
def extract_command(args):
    """Run the extraction pipeline."""
    # Determine parameters
    folder = get_param(args, 'folder', 'VOTER_PDF_FOLDER', 'pdf_folder',
                       "PDF folder path: ")
    output = get_param(args, 'output', 'VOTER_CSV_OUTPUT', 'csv_output',
                       "Output CSV folder: ")

    config = ExtractorConfig(
        folder_path=folder,
        output_folder=output,
        max_workers=args.workers or os.cpu_count(),
        dpi=args.dpi
    )
    utils.setup_signal_handler()

    all_pdfs = sorted(config.folder_path.glob("*.pdf"))
    if not all_pdfs:
        print("No PDF files found.")
        return

    writer = CSVWriter(config.output_folder, config.progress_log)
    done = writer.load_completed()
    to_process = [p for p in all_pdfs if p.name not in done]

    print(f"\n📂 Found {len(to_process)} new PDF(s) out of {len(all_pdfs)} total.")
    print(f"💾 Output folder: {config.output_folder}")
    print(f"⚡ Workers: {config.max_workers}")
    print("🛑 Press Ctrl+C to stop gracefully.\n")

    if not to_process:
        print("🎉 All PDFs already processed.")
        return

    success, failed = 0, []
    with ProcessPoolExecutor(max_workers=config.max_workers) as executor:
        future_to_pdf = {
            executor.submit(
                process_one_pdf,
                pdf,
                config.output_folder,
                config.dpi,
                config.progress_log
            ): pdf for pdf in to_process
        }

        try:
            for future in as_completed(future_to_pdf):
                if utils.INTERRUPTED:
                    for f in future_to_pdf:
                        f.cancel()
                    break
                pdf = future_to_pdf[future]
                try:
                    pdf_name = future.result()
                    if pdf_name:
                        writer.mark_completed(pdf_name)
                        success += 1
                        print(f"  ✅ Logged: {pdf_name}")
                    else:
                        failed.append(pdf.name)
                except Exception as e:
                    print(f"\n❌ Error processing {pdf.name}: {e}")
                    failed.append(pdf.name)
        except KeyboardInterrupt:
            # Already handled by signal handler
            pass

    print(f"\n{'='*50}")
    print(f"Extraction complete. Success: {success}, Failed: {len(failed)}")
    if failed:
        print("Failed files:", ", ".join(failed))

# ----------------------------------------------------------------------
def merge_command(args):
    """Merge all CSV files into a master CSV."""
    folder = get_param(args, 'folder', 'VOTER_CSV_OUTPUT', 'csv_output',
                       "CSV folder path: ")
    output = get_param(args, 'output', 'VOTER_MASTER_OUTPUT', 'master_output',
                       "Output master CSV path: ")
    folder = Path(folder)
    output = Path(output)
    print(f"Merging CSVs from {folder}...")
    master_merger.merge_csvs(folder, output)

# ----------------------------------------------------------------------
def transliterate_command(args):
    """Transliterate a master CSV to English."""
    input_path = get_param(args, 'input', 'VOTER_MASTER_OUTPUT', 'master_output',
                           "Input master CSV path: ")
    output_path = get_param(args, 'output', 'VOTER_ENGLISH_OUTPUT', 'english_output',
                            "Output transliterated CSV path: ")
    input_path = Path(input_path)
    output_path = Path(output_path)
    print(f"Transliterating {input_path}...")
    transliterator.transliterate_csv(input_path, output_path)

# ----------------------------------------------------------------------
def run_command(args):
    """Run the full pipeline: extract → merge → transliterate."""
    print("\n🚀 Running full pipeline (extract → merge → transliterate)\n")

    # Determine folders using same logic as extract
    pdf_folder = get_param(args, 'pdf_folder', 'VOTER_PDF_FOLDER', 'pdf_folder',
                           "PDF folder path: ")
    csv_output = get_param(args, 'csv_output', 'VOTER_CSV_OUTPUT', 'csv_output',
                           "CSV output folder: ")
    master_output = get_param(args, 'master_output', 'VOTER_MASTER_OUTPUT', 'master_output',
                              "Master CSV output path (optional): ")
    english_output = get_param(args, 'english_output', 'VOTER_ENGLISH_OUTPUT', 'english_output',
                               "Transliterated CSV output path (optional): ")

    # If master_output not provided, default to csv_output / "master.csv"
    if not master_output:
        master_output = str(Path(csv_output) / "master.csv")
    # If english_output not provided, default to same folder with "_english" suffix
    if not english_output:
        p = Path(master_output)
        english_output = str(p.parent / f"{p.stem}_english{p.suffix}")

    # Create a fake args object for extract, merge, transliterate
    class FakeArgs:
        pass

    # Extract
    print("\n--- Step 1: Extraction ---")
    extract_args = FakeArgs()
    extract_args.folder = pdf_folder
    extract_args.output = csv_output
    extract_args.workers = args.workers
    extract_args.dpi = args.dpi
    extract_args.non_interactive = args.non_interactive
    extract_command(extract_args)

    if utils.INTERRUPTED:
        print("\n⏹️  Interrupted. Pipeline stopped.")
        return

    # Merge
    print("\n--- Step 2: Merging ---")
    merge_args = FakeArgs()
    merge_args.folder = csv_output
    merge_args.output = master_output
    merge_args.non_interactive = args.non_interactive
    merge_command(merge_args)

    if utils.INTERRUPTED:
        print("\n⏹️  Interrupted. Pipeline stopped.")
        return

    # Transliterate
    print("\n--- Step 3: Transliteration ---")
    trans_args = FakeArgs()
    trans_args.input = master_output
    trans_args.output = english_output
    trans_args.non_interactive = args.non_interactive
    transliterate_command(trans_args)

    print("\n🎉 Full pipeline completed successfully!")
    print(f"   Master CSV: {master_output}")
    print(f"   English CSV: {english_output}")

# ----------------------------------------------------------------------
def init_command(args):
    """Interactively set up default configuration."""
    prompt_for_config()

# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Voter Extraction Tool – extract voters from electoral roll PDFs."
    )
    parser.add_argument("--non-interactive", action="store_true",
                        help="Do not prompt for missing arguments; fail if missing.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Init command
    init_parser = subparsers.add_parser("init", help="Set up default configuration interactively")
    init_parser.set_defaults(func=init_command)

    # Extract subcommand
    ex_parser = subparsers.add_parser("extract", aliases=["ex"], help="Extract voters from PDFs")
    ex_parser.add_argument("--folder", help="Folder containing PDFs")
    ex_parser.add_argument("--output", help="Output folder for CSV files")
    ex_parser.add_argument("--workers", type=int, help="Number of parallel workers")
    ex_parser.add_argument("--dpi", type=int, default=400, help="DPI for PDF conversion")
    ex_parser.set_defaults(func=extract_command)

    # Merge subcommand
    mg_parser = subparsers.add_parser("merge", aliases=["mg"], help="Merge all CSVs into one master CSV")
    mg_parser.add_argument("--folder", help="Folder containing CSV files")
    mg_parser.add_argument("--output", help="Output master CSV file path")
    mg_parser.set_defaults(func=merge_command)

    # Transliterate subcommand
    tr_parser = subparsers.add_parser("transliterate", aliases=["tr"], help="Transliterate a master CSV to English")
    tr_parser.add_argument("--input", help="Input master CSV path")
    tr_parser.add_argument("--output", help="Output transliterated CSV path")
    tr_parser.set_defaults(func=transliterate_command)

    # Run (full pipeline) subcommand
    run_parser = subparsers.add_parser("run", aliases=["all"], help="Run full pipeline: extract → merge → transliterate")
    run_parser.add_argument("--pdf-folder", help="Folder containing PDFs")
    run_parser.add_argument("--csv-output", help="Folder to save individual CSVs")
    run_parser.add_argument("--master-output", help="Path for master CSV (optional)")
    run_parser.add_argument("--english-output", help="Path for transliterated CSV (optional)")
    run_parser.add_argument("--workers", type=int, help="Number of parallel workers")
    run_parser.add_argument("--dpi", type=int, default=400, help="DPI for PDF conversion")
    run_parser.set_defaults(func=run_command)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()