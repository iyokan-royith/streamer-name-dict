from pathlib import Path

from lib.entries import EntryRow, load_entries
from lib.validate import (
    check_no_duplicate_person_surface,
    check_reading_is_hiragana,
    check_reading_source_valid,
    check_required_fields,
    check_status_valid,
    validate_entries,
)

FIXTURES = Path(__file__).parent / "fixtures"


def make_row(line_no=2, **overrides):
    base = {
        "person_id": "p1",
        "surface": "テスト",
        "reading": "てすと",
        "reading_source": "pr_manual",
        "source_url": "https://example.com",
        "org": "",
        "org_source_url": "",
        "status": "active",
        "added": "2026-09-07",
        "note": "",
    }
    base.update(overrides)
    return EntryRow(line_no=line_no, data=base)


def test_valid_fixture_has_no_errors():
    rows = load_entries(FIXTURES / "entries_valid.tsv")
    assert validate_entries(rows) == []


def test_missing_required_field_detected():
    row = make_row(source_url="")
    errors = check_required_fields([row])
    assert len(errors) == 1
    assert "source_url" in errors[0]


def test_all_required_fields_present_is_ok():
    row = make_row()
    assert check_required_fields([row]) == []


def test_reading_with_katakana_is_rejected():
    row = make_row(reading="テスト")
    errors = check_reading_is_hiragana([row])
    assert len(errors) == 1
    assert "テスト" in errors[0]


def test_reading_with_kanji_is_rejected():
    row = make_row(reading="漢字")
    errors = check_reading_is_hiragana([row])
    assert len(errors) == 1


def test_reading_pure_hiragana_is_ok():
    row = make_row(reading="ほしまちすいせい")
    assert check_reading_is_hiragana([row]) == []


def test_reading_with_choonpu_is_ok():
    # 長音記号「ー」は許容する
    row = make_row(reading="こんぴゅーたー")
    assert check_reading_is_hiragana([row]) == []


def test_reading_with_vu_hiragana_is_ok():
    # 「ゔ」（U+3094・ヴ音のひらがな表記）は ぁ-ん の連続範囲外だが許容する（ヴ音を含む活動名に備える）
    row = make_row(reading="ゔぁいおれっと")
    assert check_reading_is_hiragana([row]) == []


def test_undefined_reading_source_is_rejected():
    row = make_row(reading_source="guess")
    errors = check_reading_source_valid([row])
    assert len(errors) == 1
    assert "guess" in errors[0]


def test_defined_reading_source_is_ok():
    for value in ["org_kana", "org_romaji", "self_channel_title", "self_profile", "kana_surface", "pr_manual"]:
        row = make_row(reading_source=value)
        assert check_reading_source_valid([row]) == []


def test_undefined_status_is_rejected():
    row = make_row(status="pending")
    errors = check_status_valid([row])
    assert len(errors) == 1


def test_defined_status_is_ok():
    assert check_status_valid([make_row(status="active")]) == []
    assert check_status_valid([make_row(status="removed")]) == []


def test_duplicate_person_id_and_surface_is_rejected():
    rows = [
        make_row(line_no=2, person_id="p1", surface="A"),
        make_row(line_no=3, person_id="p1", surface="A"),
    ]
    errors = check_no_duplicate_person_surface(rows)
    assert len(errors) == 1
    assert "3行目" in errors[0]


def test_same_person_different_surface_is_ok():
    rows = [
        make_row(line_no=2, person_id="p1", surface="A"),
        make_row(line_no=3, person_id="p1", surface="B"),
    ]
    assert check_no_duplicate_person_surface(rows) == []


def test_invalid_fixture_collects_all_error_types():
    rows = load_entries(FIXTURES / "entries_invalid.tsv")
    errors = validate_entries(rows)
    # a-person: source_url欠落 / b-person: カタカナ / c-person: reading_source定義外 /
    # d-person: status定義外 / e-person 2行: 重複
    assert any("source_url" in e for e in errors)
    assert any("ジンブツビー" in e for e in errors)
    assert any("guess" in e for e in errors)
    assert any("pending" in e for e in errors)
    assert any("重複" in e for e in errors)
    assert len(errors) == 5
