#!/usr/bin/env python3
from voter_tool.cli import main
import sys

# Simulate command-line arguments
sys.argv = ["voter-tool", "run", 
            "--pdf-folder", "/Users/iqbaltaha3/Documents/voter_tool/input_folder",
            "--csv-output", "/Users/iqbaltaha3/Documents/voter_tool/output_folder/output_csvs"]

if __name__ == "__main__":
    main()