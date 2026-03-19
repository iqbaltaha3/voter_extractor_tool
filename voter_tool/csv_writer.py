import pandas as pd
from pathlib import Path
from . import utils

class CSVWriter:
    """Write voter records to a CSV file and manage progress log."""
    def __init__(self, output_folder: Path, log_file: str = "processed.log"):
        self.output_folder = output_folder
        self.log_file = output_folder / log_file

    def save(self, voters, booth_name: str, pdf_stem: str):
        """Save voters to a CSV file named after the booth."""
        df = pd.DataFrame(voters) if voters else pd.DataFrame(columns=[
            'Booth', 'Name', 'Father_Husband', 'House', 'Age', 'Gender', 'EPIC'
        ])
        # Ensure all columns exist
        for col in ['Booth', 'Name', 'Father_Husband', 'House', 'Age', 'Gender', 'EPIC']:
            if col not in df.columns:
                df[col] = ''
        df = df[['Booth', 'Name', 'Father_Husband', 'House', 'Age', 'Gender', 'EPIC']]

        safe_name = utils.booth_to_filename(booth_name)
        csv_path = self.output_folder / safe_name
        df.to_csv(csv_path, index=False, encoding='utf-8')
        return csv_path, len(df)

    def mark_completed(self, pdf_name: str):
        """Append the PDF name to the progress log."""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(pdf_name + '\n')

    def load_completed(self):
        """Return a set of PDF filenames that have been successfully processed."""
        if not self.log_file.exists():
            return set()
        with open(self.log_file, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip()}