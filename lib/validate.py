"""entries.tsv の入力検証。

CI で門番として使う想定なので、検出したエラーは1つに絞らず全部集めて返す。

単体で構文・検証だけを走らせたい場合（CI の lint ジョブ・手元確認）は CLI として実行できる:
    python -m lib.validate data/entries.tsv data/aliases.tsv
（aliases.tsv は省略可。省略時は entries.tsv と同じディレクトリの aliases.tsv を探し、無ければ0件扱い）
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .aliases import AliasRow, load_aliases
from .aliases import REQUIRED_FIELDS as ALIAS_REQUIRED_FIELDS
from .aliases import FULL_SURFACE_KINDS, NAME_PART_KINDS, VALID_KINDS
from .entries import EntryRow, REQUIRED_FIELDS, VALID_READING_SOURCES, VALID_STATUSES, load_entries

# ひらがなのみを許可する（長音記号「ー」は将来の読みで使う可能性があるため許容）。
# 「ゔ」（U+3094・ヴ音のひらがな表記）はひらがな連続範囲 ぁ-ん の外側にあるため個別に許容する
# （ヴ音を含む活動名に備える）。カタカナ・漢字・英数字が混じっていたら弾く。
HIRAGANA_RE = re.compile(r"^[ぁ-んーゔ]+$")


def check_required_fields(rows: list[EntryRow]) -> list[str]:
    errors = []
    for row in rows:
        for field in REQUIRED_FIELDS:
            if not row[field].strip():
                errors.append(f"{row.line_no}行目: 必須列 '{field}' が空です（person_id={row['person_id']!r}）")
    return errors


def check_reading_is_hiragana(rows: list[EntryRow]) -> list[str]:
    errors = []
    for row in rows:
        reading = row["reading"]
        if reading and not HIRAGANA_RE.match(reading):
            errors.append(
                f"{row.line_no}行目: reading '{reading}' がひらがな以外の文字を含んでいます"
                f"（person_id={row['person_id']!r}）"
            )
    return errors


def check_reading_source_valid(rows: list[EntryRow]) -> list[str]:
    errors = []
    for row in rows:
        value = row["reading_source"]
        if value and value not in VALID_READING_SOURCES:
            errors.append(
                f"{row.line_no}行目: reading_source '{value}' は定義外です"
                f"（許可値: {sorted(VALID_READING_SOURCES)}）"
            )
    return errors


def check_status_valid(rows: list[EntryRow]) -> list[str]:
    errors = []
    for row in rows:
        value = row["status"]
        if value and value not in VALID_STATUSES:
            errors.append(
                f"{row.line_no}行目: status '{value}' は定義外です（許可値: {sorted(VALID_STATUSES)}）"
            )
    return errors


def check_no_duplicate_person_surface(rows: list[EntryRow]) -> list[str]:
    errors = []
    seen: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (row["person_id"], row["surface"])
        if key in seen:
            errors.append(
                f"{row.line_no}行目: person_id={key[0]!r} surface={key[1]!r} が"
                f" {seen[key]}行目と重複しています"
            )
        else:
            seen[key] = row.line_no
    return errors


def validate_entries(rows: list[EntryRow]) -> list[str]:
    """全チェックを実行し、エラーメッセージのリストを返す（空なら合格）。"""
    errors: list[str] = []
    errors += check_required_fields(rows)
    errors += check_reading_is_hiragana(rows)
    errors += check_reading_source_valid(rows)
    errors += check_status_valid(rows)
    errors += check_no_duplicate_person_surface(rows)
    return errors


# --- aliases.tsv 用の検証（DESIGN.md「データモデル」の aliases 節参照） ---


def check_alias_required_fields(rows: list[AliasRow]) -> list[str]:
    errors = []
    for row in rows:
        for field in ALIAS_REQUIRED_FIELDS:
            if not row[field].strip():
                errors.append(
                    f"{row.line_no}行目: 必須列 '{field}' が空です（person_id={row['person_id']!r}）"
                )
    return errors


def check_alias_reading_is_hiragana(rows: list[AliasRow]) -> list[str]:
    errors = []
    for row in rows:
        reading = row["reading"]
        if reading and not HIRAGANA_RE.match(reading):
            errors.append(
                f"{row.line_no}行目: reading '{reading}' がひらがな以外の文字を含んでいます"
                f"（person_id={row['person_id']!r}）"
            )
    return errors


def check_alias_kind_valid(rows: list[AliasRow]) -> list[str]:
    errors = []
    for row in rows:
        value = row["kind"]
        if value and value not in VALID_KINDS:
            errors.append(f"{row.line_no}行目: kind '{value}' は定義外です（許可値: {sorted(VALID_KINDS)}）")
    return errors


def check_alias_person_id_exists(rows: list[AliasRow], entry_rows: list[EntryRow]) -> list[str]:
    """alias の person_id が entries.tsv に（status を問わず）存在するかを確認する。"""
    known_person_ids = {row["person_id"] for row in entry_rows}
    errors = []
    for row in rows:
        person_id = row["person_id"]
        if person_id and person_id not in known_person_ids:
            errors.append(
                f"{row.line_no}行目: person_id {person_id!r} が data/entries.tsv に存在しません"
            )
    return errors


def _surfaces_by_person(entry_rows: list[EntryRow]) -> dict[str, set[str]]:
    surfaces_by_person: dict[str, set[str]] = {}
    for entry in entry_rows:
        surfaces_by_person.setdefault(entry["person_id"], set()).add(entry["surface"])
    return surfaces_by_person


def check_alias_reading_variant_surface_matches(rows: list[AliasRow], entry_rows: list[EntryRow]) -> list[str]:
    """kind=reading_variant / short_name の alias は、同じ person_id の entries に同じ surface が存在すること。

    どちらも「正式名の表記そのもの」に別の読みを与える種別なので、表記は entries 側と一致していなければならない。
    """
    surfaces_by_person = _surfaces_by_person(entry_rows)

    errors = []
    for row in rows:
        if row["kind"] not in FULL_SURFACE_KINDS:
            continue
        known_surfaces = surfaces_by_person.get(row["person_id"], set())
        if row["surface"] not in known_surfaces:
            errors.append(
                f"{row.line_no}行目: kind={row['kind']} ですが、"
                f" person_id={row['person_id']!r} の entries に surface {row['surface']!r} が見つかりません"
            )
    return errors


def check_alias_name_part_surface_is_substring(rows: list[AliasRow], entry_rows: list[EntryRow]) -> list[str]:
    """kind=family_name / given_name の alias は、surface が同じ person_id の entries のいずれかの surface の部分文字列であること。

    姓・名は正式名を切り出したものなので、正式名に含まれない文字列を「姓」「名」として登録することはできない。
    """
    surfaces_by_person = _surfaces_by_person(entry_rows)

    errors = []
    for row in rows:
        if row["kind"] not in NAME_PART_KINDS:
            continue
        surface = row["surface"]
        known_surfaces = surfaces_by_person.get(row["person_id"], set())
        if not surface or not any(surface in known for known in known_surfaces):
            errors.append(
                f"{row.line_no}行目: kind={row['kind']} ですが、"
                f" surface {surface!r} が person_id={row['person_id']!r} の entries のどの surface にも含まれていません"
            )
    return errors


def check_alias_no_single_char_reading(rows: list[AliasRow]) -> list[str]:
    """reading が 1 文字の行は拒否する（`は`→`ハ` のように 1 文字の読みから人名候補が出るのは IME 辞書として有害）。

    surface だけが 1 文字の行（例: surface `榊`・reading `さかき`）は通常の辞書項目なので許容する。
    """
    errors = []
    for row in rows:
        if len(row["reading"]) == 1:
            errors.append(
                f"{row.line_no}行目: reading {row['reading']!r} が 1 文字です"
                f"（1 文字の読みは登録できません・person_id={row['person_id']!r}）"
            )
    return errors


def check_no_duplicate_alias(rows: list[AliasRow]) -> list[str]:
    errors = []
    seen: dict[tuple[str, str, str], int] = {}
    for row in rows:
        key = (row["person_id"], row["surface"], row["reading"])
        if key in seen:
            errors.append(
                f"{row.line_no}行目: person_id={key[0]!r} surface={key[1]!r} reading={key[2]!r} が"
                f" {seen[key]}行目と重複しています"
            )
        else:
            seen[key] = row.line_no
    return errors


def validate_aliases(rows: list[AliasRow], entry_rows: list[EntryRow]) -> list[str]:
    """aliases.tsv 全チェックを実行し、エラーメッセージのリストを返す（空なら合格）。

    entry_rows（data/entries.tsv）は person_id の存在確認・reading_variant の surface 突き合わせに使う。
    """
    errors: list[str] = []
    errors += check_alias_required_fields(rows)
    errors += check_alias_reading_is_hiragana(rows)
    errors += check_alias_kind_valid(rows)
    errors += check_alias_person_id_exists(rows, entry_rows)
    errors += check_alias_reading_variant_surface_matches(rows, entry_rows)
    errors += check_alias_name_part_surface_is_substring(rows, entry_rows)
    errors += check_alias_no_single_char_reading(rows)
    errors += check_no_duplicate_alias(rows)
    return errors


# --- CLI（build.py から検証だけを切り離して単体で走らせたい場合用。出口のみでロジックは持たない） ---


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entries", help="entries.tsv のパス")
    parser.add_argument(
        "aliases",
        nargs="?",
        default=None,
        help="aliases.tsv のパス（省略時は entries と同じディレクトリの aliases.tsv。無ければ0件扱い）",
    )
    args = parser.parse_args(argv)

    entries_path = Path(args.entries)
    if not entries_path.exists():
        print(f"エラー: {entries_path} が見つかりません", file=sys.stderr)
        return 1

    aliases_path = Path(args.aliases) if args.aliases else entries_path.parent / "aliases.tsv"

    rows = load_entries(entries_path)
    alias_rows = load_aliases(aliases_path) if aliases_path.exists() else []

    errors = validate_entries(rows)
    errors += validate_aliases(alias_rows, rows)
    if errors:
        print(f"検証エラー: {len(errors)} 件", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"検証OK: entries {len(rows)} 行・aliases {len(alias_rows)} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
