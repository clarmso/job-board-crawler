#!/usr/bin/env python3
"""
Job board crawler. Fetches all job postings from configured career pages
and saves each as a JSON file. Git history tracks when jobs were active.

Supported platforms: greenhouse, lever, ashby, workable, recruitee, smartrecruiters
"""

import json
import os
import sys

from src.crawl import PLATFORMS, crawl


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "companies.json"

    with open(config_path) as f:
        companies = json.load(f)

    total = 0
    for platform, names in companies.items():
        if platform not in PLATFORMS:
            print(f"Skipping unsupported platform: {platform}")
            continue

        for name in names:
            print(f"Crawling {name} ({platform})")
            output_dir = os.path.join("data", name)
            total += crawl(platform, name, output_dir)

    print(f"\nDone. Total jobs processed: {total}")


if __name__ == "__main__":
    main()
