from setuptools import setup, find_packages

setup(
    name="voter_tool",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pdf2image",
        "pytesseract",
        "opencv-python",
        "numpy",
        "pandas",
        "indic-transliteration",
        "pyyaml",
    ],
    entry_points={
        "console_scripts": [
            "voter-tool = voter_tool.cli:main",
        ],
    },
    author="Your Name",
    description="Extract voters from electoral roll PDFs",
)