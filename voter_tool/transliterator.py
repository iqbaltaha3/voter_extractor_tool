import pandas as pd
from pathlib import Path
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

GENDER_MAP = {
    'महिला': 'Female',
    'पुरुष': 'Male',
    'अन्य': 'Other'
}
HINDI_DIGITS = str.maketrans('०१२३४५६७८९', '0123456789')

def transliterate_text(text):
    """Convert Devanagari text to ITRANS (English) and title case."""
    if pd.isna(text) or str(text).strip().lower() in ('nan', ''):
        return text
    text = str(text).translate(HINDI_DIGITS).strip()
    try:
        result = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
        return result.title()
    except Exception:
        return text

def translate_gender(text):
    if pd.isna(text):
        return text
    return GENDER_MAP.get(str(text).strip(), text)

def convert_house(text):
    if pd.isna(text):
        return text
    return str(text).translate(HINDI_DIGITS).strip()

def transliterate_csv(input_path: Path, output_path: Path):
    """Load a master CSV, transliterate relevant columns, and save."""
    print("Loading master CSV...")
    df = pd.read_csv(input_path)
    print(f"Loaded {len(df)} voters.\n")

    print("Transliterating...")
    df['Booth'] = df['Booth'].apply(transliterate_text)
    df['Name'] = df['Name'].apply(transliterate_text)
    df['Father_Husband'] = df['Father_Husband'].apply(transliterate_text)
    df['House'] = df['House'].apply(convert_house)
    df['Gender'] = df['Gender'].apply(translate_gender)
    # Age and EPIC remain as is

    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"\n✅ Total voters: {len(df)}")
    print(f"✅ Total booths: {df['Booth'].nunique()}")
    print(f"💾 Saved to: {output_path}")
    print("\nSample (first 5 rows):")
    print(df.head().to_string(index=False))
    return df