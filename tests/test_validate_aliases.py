"""lib/aliases.py・lib/validate.py の aliases.tsv 向け検証のテスト。"""
from pathlib import Path

from lib.aliases import AliasRow, load_aliases
from lib.entries import load_entries
from lib.validate import (
    check_alias_kind_valid,
    check_alias_name_part_surface_is_substring,
    check_alias_no_single_char_reading,
    check_alias_person_id_exists,
    check_alias_reading_is_hiragana,
    check_alias_reading_variant_surface_matches,
    check_alias_required_fields,
    check_no_duplicate_alias,
    validate_aliases,
)

FIXTURES = Path(__file__).parent / "fixtures"


def make_entry_row(line_no=2, **overrides):
    from lib.entries import EntryRow

    base = {
        "person_id": "zeta-k4sen",
        "surface": "K4SEN",
        "reading": "かせん",
        "reading_source": "self_channel_title",
        "source_url": "https://example.com",
        "org": "ZETA DIVISION",
        "org_source_url": "",
        "status": "active",
        "added": "2026-09-07",
        "note": "",
    }
    base.update(overrides)
    return EntryRow(line_no=line_no, data=base)


def make_alias_row(line_no=2, **overrides):
    base = {
        "person_id": "zeta-k4sen",
        "surface": "ケイフォー",
        "reading": "けいふぉー",
        "kind": "nickname",
        "note": "",
        "added": "2026-09-07",
    }
    base.update(overrides)
    return AliasRow(line_no=line_no, data=base)


def test_valid_fixture_has_no_errors():
    entries = load_entries(FIXTURES / "entries_valid.tsv")
    aliases = load_aliases(FIXTURES / "aliases_valid.tsv")
    assert validate_aliases(aliases, entries) == []


def test_missing_required_field_detected():
    row = make_alias_row(surface="")
    errors = check_alias_required_fields([row])
    assert len(errors) == 1
    assert "surface" in errors[0]


def test_reading_with_katakana_is_rejected():
    row = make_alias_row(reading="テスト")
    errors = check_alias_reading_is_hiragana([row])
    assert len(errors) == 1


def test_reading_pure_hiragana_is_ok():
    row = make_alias_row(reading="けいふぉー")
    assert check_alias_reading_is_hiragana([row]) == []


def test_undefined_kind_is_rejected():
    row = make_alias_row(kind="guess")
    errors = check_alias_kind_valid([row])
    assert len(errors) == 1
    assert "guess" in errors[0]


def test_defined_kind_is_ok():
    for value in ["nickname", "reading_variant", "family_name", "given_name", "short_name"]:
        row = make_alias_row(kind=value)
        assert check_alias_kind_valid([row]) == []


def test_person_id_not_in_entries_is_rejected():
    entries = [make_entry_row(person_id="zeta-k4sen")]
    row = make_alias_row(person_id="unknown-person")
    errors = check_alias_person_id_exists([row], entries)
    assert len(errors) == 1
    assert "unknown-person" in errors[0]


def test_person_id_in_entries_is_ok_even_if_removed():
    entries = [make_entry_row(person_id="retired-person", status="removed")]
    row = make_alias_row(person_id="retired-person")
    assert check_alias_person_id_exists([row], entries) == []


def test_reading_variant_requires_matching_surface_in_entries():
    entries = [make_entry_row(person_id="zeta-k4sen", surface="K4SEN")]
    bad = make_alias_row(person_id="zeta-k4sen", surface="ｋ4sen", kind="reading_variant")
    errors = check_alias_reading_variant_surface_matches([bad], entries)
    assert len(errors) == 1
    assert "reading_variant" in errors[0]

    good = make_alias_row(person_id="zeta-k4sen", surface="K4SEN", kind="reading_variant")
    assert check_alias_reading_variant_surface_matches([good], entries) == []


def test_nickname_does_not_require_matching_surface():
    entries = [make_entry_row(person_id="zeta-k4sen", surface="K4SEN")]
    row = make_alias_row(person_id="zeta-k4sen", surface="ケイフォー", kind="nickname")
    assert check_alias_reading_variant_surface_matches([row], entries) == []


def test_short_name_requires_matching_surface_in_entries():
    entries = [make_entry_row(person_id="p1", surface="雪花ラミィ")]
    bad = make_alias_row(person_id="p1", surface="ラミィ", reading="らみぃ", kind="short_name")
    errors = check_alias_reading_variant_surface_matches([bad], entries)
    assert len(errors) == 1
    assert "short_name" in errors[0]

    good = make_alias_row(person_id="p1", surface="雪花ラミィ", reading="らみぃ", kind="short_name")
    assert check_alias_reading_variant_surface_matches([good], entries) == []


def test_name_part_surface_must_be_substring_of_an_entry_surface():
    entries = [make_entry_row(person_id="p1", surface="雪花ラミィ"), make_entry_row(line_no=3, person_id="p1", surface="Yukihana Lamy")]
    for kind, surface in (("family_name", "雪花"), ("given_name", "ラミィ"), ("family_name", "Yukihana")):
        row = make_alias_row(person_id="p1", surface=surface, kind=kind)
        assert check_alias_name_part_surface_is_substring([row], entries) == [], (kind, surface)
    bad = make_alias_row(person_id="p1", surface="雪華", kind="family_name")
    errors = check_alias_name_part_surface_is_substring([bad], entries)
    assert len(errors) == 1
    assert "family_name" in errors[0] and "雪華" in errors[0]


def test_name_part_check_ignores_other_kinds():
    entries = [make_entry_row(person_id="p1", surface="雪花ラミィ")]
    row = make_alias_row(person_id="p1", surface="らみちゃん", kind="nickname")
    assert check_alias_name_part_surface_is_substring([row], entries) == []


def test_single_char_reading_is_rejected():
    for surface in ("ハ", "ケイ"):
        errors = check_alias_no_single_char_reading([make_alias_row(surface=surface, reading="は")])
        assert len(errors) == 1, surface
        assert "1 文字" in errors[0]


def test_single_char_surface_with_longer_reading_is_allowed():
    assert check_alias_no_single_char_reading([make_alias_row(surface="榊", reading="さかき")]) == []


def test_duplicate_person_surface_reading_is_rejected():
    rows = [
        make_alias_row(line_no=2, person_id="p1", surface="A", reading="あ"),
        make_alias_row(line_no=3, person_id="p1", surface="A", reading="あ"),
    ]
    errors = check_no_duplicate_alias(rows)
    assert len(errors) == 1
    assert "3行目" in errors[0]


def test_same_surface_different_reading_is_not_duplicate():
    rows = [
        make_alias_row(line_no=2, person_id="p1", surface="A", reading="あ"),
        make_alias_row(line_no=3, person_id="p1", surface="A", reading="えー"),
    ]
    assert check_no_duplicate_alias(rows) == []


def test_invalid_fixture_collects_all_error_types():
    entries = load_entries(FIXTURES / "entries_valid.tsv")
    aliases = load_aliases(FIXTURES / "aliases_invalid.tsv")
    errors = validate_aliases(aliases, entries)
    assert any("surface" in e for e in errors)  # 必須列欠落
    assert any("テスト" in e for e in errors)  # カタカナ reading
    assert any("guess" in e for e in errors)  # kind 定義外
    assert any("unknown-person" in e for e in errors)  # person_id 不在
    assert any("reading_variant" in e for e in errors)  # surface 不一致
    assert any("重複" in e for e in errors)  # 重複
    assert any("family_name" in e and "葛丸" in e for e in errors)  # 姓が正式名に含まれない
    assert any("short_name" in e and "葛葉丸" in e for e in errors)  # short_name の surface 不一致
    assert any("1 文字です" in e for e in errors)  # reading が 1 文字
