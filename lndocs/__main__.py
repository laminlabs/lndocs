import argparse
import os
from pathlib import Path

from dirsync import sync

HERE = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser(description="Build Lamin website.")
    aa = parser.add_argument
    aa("--docs", type=str, default="docs", help="directory with docs sources")
    aa("--site", type=str, default="_build/html", help="output directory")
    args = parser.parse_args()
    sync(str(HERE.parent / "lamin_sphinx"), "./lamin_sphinx", "sync", create=True)
    os.system(f"sphinx-build {args.docs} {args.site}")
