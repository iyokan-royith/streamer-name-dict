#!/usr/bin/env python3
"""候補 TSV を data/entries.tsv へ取り込むメンテナ用 CLI。

使い方:
    python promote.py <候補 TSV>...
    python promote.py <候補 TSV>... --dry-run    # 書き込まずに件数・衝突だけ表示

読み込む候補 TSV の列は lib/promote.py の CANDIDATE_FIELDS
（entries.tsv の全列 + reading_candidate/needs_review/romaji）。
"""
from __future__ import annotations

import argparse
import csv
import os
import stat
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.entries import EntryRow, FIELDS, load_entries  # noqa: E402
from lib.promote import CANDIDATE_FIELDS, PromoteResult, promote_candidates  # noqa: E402
from lib.validate import validate_entries  # noqa: E402


def load_candidate_rows(path: str | Path) -> list[dict[str, str]]:
    path = Path(path)
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        missing = set(CANDIDATE_FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: 候補 TSV に必須列が欠けています: {sorted(missing)}")
        for raw in reader:
            rows.append({k: (v if v is not None else "") for k, v in raw.items() if k is not None})
    return rows


def write_entries(entries: list[dict[str, str]], path: str | Path) -> None:
    """entries.tsv を書き出す（既存ファイルと同じ LF・UTF-8・ヘッダ付き TSV の形式）。

    一時ファイルに書いてから os.replace でアトミックに差し替える
    （書き込み途中でのクラッシュ等で entries.tsv が壊れた状態になるのを防ぐ）。

    `tempfile.mkstemp` は 0600 でファイルを作るため、`os.replace` はそのパーミッションを
    そのまま引き継ぐ（既存ファイルが 644 等でも 600 に化けてしまう）。書き込み前に
    既存ファイルのモードを読み、一時ファイルへ `os.chmod` で揃えてから置き換える。
    既存ファイルが無い（新規作成）場合は mkstemp の既定（0600）のままにする。
    """
    path = Path(path)
    original_mode: int | None = None
    if path.exists():
        original_mode = stat.S_IMODE(path.stat().st_mode)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for row in entries:
                writer.writerow({field: row.get(field, "") for field in FIELDS})
        if original_mode is not None:
            os.chmod(tmp_name, original_mode)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def _print_conflicts(conflicts: list[tuple[dict[str, str], dict[str, str]]]) -> None:
    print(f"衝突: {len(conflicts)} 件（reading が既存と候補で異なる。人が決める必要があります）", file=sys.stderr)
    for existing, candidate in conflicts:
        print(
            f"  - person_id={existing['person_id']!r}: "
            f"既存 reading={existing['reading']!r}（{existing['reading_source']}） vs "
            f"候補 reading={candidate['reading']!r}（{candidate['reading_source']}, {candidate.get('source_url', '')}）",
            file=sys.stderr,
        )


def _report(result: PromoteResult) -> None:
    print(f"追加: {len(result.added)} 件")
    print(f"信頼度昇格: {len(result.upgraded)} 件")
    for before, after in result.upgraded:
        print(
            f"  - person_id={before['person_id']!r}: "
            f"{before['reading_source']} → {after['reading_source']}"
        )
    print(f"変更なし: {len(result.unchanged)} 件")
    print(f"スキップ（要確認）: {len(result.skipped_needs_review)} 件")
    print(f"スキップ（removed のため据え置き）: {len(result.skipped_removed)} 件")
    if result.skipped_duplicate_candidate:
        print(f"スキップ（候補内で person_id 重複）: {len(result.skipped_duplicate_candidate)} 件")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("candidates", nargs="+", help="候補 TSV のパス（複数可）")
    parser.add_argument("--entries", default="data/entries.tsv", help="entries.tsv のパス")
    parser.add_argument("--dry-run", action="store_true", help="書き込まずに件数・衝突だけ表示する")
    args = parser.parse_args(argv)

    entries_path = Path(args.entries)
    if not entries_path.exists():
        print(f"エラー: {entries_path} が見つかりません", file=sys.stderr)
        return 1

    existing_rows: list[EntryRow] = load_entries(entries_path)

    candidate_rows: list[dict[str, str]] = []
    for c_path in args.candidates:
        p = Path(c_path)
        if not p.exists():
            print(f"エラー: {p} が見つかりません", file=sys.stderr)
            return 1
        try:
            candidate_rows.extend(load_candidate_rows(p))
        except ValueError as e:
            print(f"エラー: {e}", file=sys.stderr)
            return 1

    result = promote_candidates(existing_rows, candidate_rows)
    _report(result)

    if result.has_conflicts:
        _print_conflicts(result.conflicts)
        print("衝突があるため書き込みは行いません。", file=sys.stderr)
        return 1

    # --dry-run でも検証は必ず通す（書き込みまでの流れを事前に確認できるようにするため。
    # 検証だけ飛ばすと「dry-run では通ったのに本実行で落ちる」という食い違いが起きる）。
    fake_rows = [EntryRow(line_no=i + 2, data=d) for i, d in enumerate(result.entries)]
    errors = validate_entries(fake_rows)
    if errors:
        print(f"検証エラー: {len(errors)} 件（書き込みを中止します）", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    if args.dry_run:
        print("--dry-run のため書き込みは行いません。")
        return 0

    write_entries(result.entries, entries_path)
    print(f"{entries_path} を更新しました（合計 {len(result.entries)} 行）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
