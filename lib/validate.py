"""entries.tsv の入力検証。

CI で門番として使う想定なので、検出したエラーは1つに絞らず全部集めて返す。
"""
from __future__ import annotations

import re

from .aliases import AliasRow
from .aliases import REQUIRED_FIELDS as ALIAS_REQUIRED_FIELDS
from .aliases import VALID_KINDS
from .entries import EntryRow, REQUIRED_FIELDS, VALID_READING_SOURCES, VALID_STATUSES

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


def check_alias_reading_variant_surface_matches(rows: list[AliasRow], entry_rows: list[EntryRow]) -> list[str]:
    """kind=reading_variant の alias は、同じ person_id の entries に同じ surface が存在すること。"""
    surfaces_by_person: dict[str, set[str]] = {}
    for entry in entry_rows:
        surfaces_by_person.setdefault(entry["person_id"], set()).add(entry["surface"])

    errors = []
    for row in rows:
        if row["kind"] != "reading_variant":
            continue
        known_surfaces = surfaces_by_person.get(row["person_id"], set())
        if row["surface"] not in known_surfaces:
            errors.append(
                f"{row.line_no}行目: kind=reading_variant ですが、"
                f" person_id={row['person_id']!r} の entries に surface {row['surface']!r} が見つかりません"
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
    errors += check_no_duplicate_alias(rows)
    return errors
