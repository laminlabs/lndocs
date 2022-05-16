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
    aa("--live", action="store_true", help="use autobuild")
    args = parser.parse_args()
    sync(str(HERE / "lamin_sphinx"), "./lamin_sphinx", "sync", create=True)
    if args.live:
        build_command = "sphinx-autobuild"
    else:
        build_command = "sphinx-build"
    os.system(f"{build_command} {args.docs} {args.site}")
