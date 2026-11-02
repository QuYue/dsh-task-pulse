#!/usr/bin/env python3
"""Tiny word-count CLI used as the demo task's codebase."""
import argparse
import json
import sys
from collections import Counter


def read_text(path):
    if path in (None, "-"):
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def count_words(text):
    return Counter(word.lower() for word in text.split())


def main(argv=None):
    parser = argparse.ArgumentParser(description="count words in a file or stdin")
    parser.add_argument("path", nargs="?", default="-")
    parser.add_argument("--top", type=int, default=0, help="show the N most common words")
    args = parser.parse_args(argv)
    counts = count_words(read_text(args.path))
    if args.top:
        for word, number in counts.most_common(args.top):
            print(f"{word}\t{number}")
    else:
        print(sum(counts.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
