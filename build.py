#!/usr/bin/env python3
"""entries.tsv から各 IME 向け辞書ファイルを生成する CLI。

使い方:
    python build.py                          # data/entries.tsv → dist/
    python build.py --data path/to.tsv --out-dir path/to/dist
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib.aliases import active_aliases, load_aliases
from lib.entries import EntryRow, active_person_ids, active_rows, load_entries
from lib.formats import FORMAT_GENERATORS
from lib.validate import validate_aliases, validate_entries


def _alias_as_entry_row(alias, org_by_person: dict[str, str]) -> EntryRow:
    """alias 行を、フォーマット生成器（lib/formats.py）がそのまま読める形に変換する。

    フォーマット生成器は EntryRow の 'surface' / 'reading' / 'org' しか見ないので、
    aliases.tsv 由来の行に entries.tsv 側の org を補って渡す（aliases.tsv 自体は org を持たない）。
    """
    data = {
        "person_id": alias["person_id"],
        "surface": alias["surface"],
        "reading": alias["reading"],
        "reading_source": "",
        "source_url": "",
        "org": org_by_person.get(alias["person_id"], ""),
        "org_source_url": "",
        "status": "active",
        "added": alias["added"],
        "note": alias["note"],
    }
    return EntryRow(line_no=alias.line_no, data=data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/entries.tsv", help="entries.tsv のパス")
    parser.add_argument(
        "--aliases",
        default=None,
        help="aliases.tsv のパス（省略時は --data と同じディレクトリの aliases.tsv。無ければ0件扱い）",
    )
    parser.add_argument("--out-dir", default="dist", help="生成物の出力先ディレクトリ")
    args = parser.parse_args(argv)

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"エラー: {data_path} が見つかりません", file=sys.stderr)
        return 1

    aliases_path = Path(args.aliases) if args.aliases else data_path.parent / "aliases.tsv"

    rows = load_entries(data_path)
    alias_rows = load_aliases(aliases_path) if aliases_path.exists() else []

    errors = validate_entries(rows)
    errors += validate_aliases(alias_rows, rows)
    if errors:
        print(f"検証エラー: {len(errors)} 件", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    active = active_rows(rows)
    removed_count = len(rows) - len(active)

    org_by_person = {r["person_id"]: r["org"] for r in active}
    active_alias_rows = active_aliases(alias_rows, active_person_ids(rows))
    alias_entry_like = [_alias_as_entry_row(a, org_by_person) for a in active_alias_rows]

    combined = active + alias_entry_like

    for filename, generator in FORMAT_GENERATORS.items():
        out_path = out_dir / filename
        out_path.write_bytes(generator(combined))
        print(f"生成: {out_path}（{len(combined)} 件）")

    print(
        f"収録 {len(combined)} 件（正式 {len(active)}・別名 {len(alias_entry_like)}）"
        f" / removed 除外 {removed_count} 件（合計 {len(rows)} 行）"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
