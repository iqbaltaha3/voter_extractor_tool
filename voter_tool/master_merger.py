import pandas as pd
from pathlib import Path

def merge_csvs(csv_folder: Path, output_path: Path):
    """
    Read all CSV files in a folder and merge them into a single master CSV.
    Returns the merged DataFrame, or None if no valid CSV found.
    """
    csvs = sorted(csv_folder.glob("*.csv"))
    if not csvs:
        print("No CSV files found.")
        return None

    dfs = []
    for csv_path in csvs:
        try:
            df = pd.read_csv(csv_path)
            if not df.empty:
                dfs.append(df)
                print(f"✅ {len(df):>4} voters — {csv_path.name}")
            else:
                print(f"⚠️  Empty: {csv_path.name}")
        except Exception as e:
            print(f"❌ Failed to read {csv_path.name}: {e}")

    if not dfs:
        print("No valid data to merge.")
        return None

    master = pd.concat(dfs, ignore_index=True)
    master.to_csv(output_path, index=False, encoding='utf-8')
    print(f"\n✅ Total voters: {len(master)}")
    print(f"✅ Total booths: {master['Booth'].nunique()}")
    print(f"💾 Saved to: {output_path}")
    return master