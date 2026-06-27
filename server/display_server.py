#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from displayhub.server import run


def main():
    parser = argparse.ArgumentParser(description="HA Display Hub server")
    parser.add_argument("-c", "--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
