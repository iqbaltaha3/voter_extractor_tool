from dataclasses import dataclass
from pathlib import Path
import os
import yaml

DEFAULT_CONFIG_PATH = Path.home() / ".voter_tool" / "config.yaml"

@dataclass
class ExtractorConfig:
    """Configuration for the PDF extraction process."""
    folder_path: Path
    output_folder: Path
    max_workers: int = os.cpu_count()
    dpi: int = 400
    progress_log: str = "processed.log"

    def __post_init__(self):
        self.folder_path = Path(self.folder_path)
        self.output_folder = Path(self.output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)


def load_config():
    """Load user configuration from ~/.voter_tool/config.yaml."""
    if DEFAULT_CONFIG_PATH.exists():
        with open(DEFAULT_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(config: dict):
    """Save user configuration to ~/.voter_tool/config.yaml."""
    DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DEFAULT_CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def prompt_for_config():
    """Interactively ask the user for default paths."""
    print("\n=== Voter Tool Configuration ===\n")
    pdf_folder = input("Default PDF folder path: ").strip()
    csv_output = input("Default CSV output folder: ").strip()
    master_output = input("Default master CSV output path (optional): ").strip()
    english_output = input("Default transliterated CSV output path (optional): ").strip()
    config = {
        'pdf_folder': pdf_folder,
        'csv_output': csv_output,
        'master_output': master_output or None,
        'english_output': english_output or None,
    }
    save_config(config)
    print("\n✅ Configuration saved to", DEFAULT_CONFIG_PATH)
    return config