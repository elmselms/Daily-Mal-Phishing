#!/usr/bin/env python3

import argparse
import base64
import csv
import io
from pathlib import Path
from urllib.parse import urlsplit


def is_url(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def encode_url(url: str) -> str:
    encoded = base64.b64encode(url.encode("utf-8")).decode("ascii")
    decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
    if decoded != url:
        raise ValueError(f"Base64 round-trip verification failed for {url!r}")
    return encoded


def convert_csv(path: Path) -> tuple[int, bool]:
    raw = path.read_bytes()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")

    rows = list(csv.reader(io.StringIO(text, newline="")))
    converted = 0

    for row in rows:
        for index, value in enumerate(row):
            if is_url(value):
                row[index] = encode_url(value)
                converted += 1

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows(rows)
    encoded_output = output.getvalue().encode("utf-8")
    if has_bom:
        encoded_output = b"\xef\xbb\xbf" + encoded_output

    changed = encoded_output != raw
    if changed:
        path.write_bytes(encoded_output)

    return converted, changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Base64-encode complete HTTP(S) URL cells in CSV files."
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory containing CSV files (defaults to the repository root).",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"not a directory: {root}")

    files_changed = 0
    urls_converted = 0
    for path in sorted(root.rglob("*.csv")):
        converted, changed = convert_csv(path)
        if changed:
            files_changed += 1
        urls_converted += converted

    print(f"Encoded {urls_converted} URLs; updated {files_changed} CSV files.")


if __name__ == "__main__":
    main()
