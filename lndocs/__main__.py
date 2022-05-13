import argparse
import os


def main():
    parser = argparse.ArgumentParser(description="Build Lamin website.")
    aa = parser.add_argument
    aa("docs", type=str, default="docs", help="directory with docs sources")
    aa("site", type=str, default="_build", help="directory with docs sources")
    args = parser.parse_args()
    os.system(f"sphinx-build {args.docs} {args.site}")
