from pathlib import Path

from lib.entries import EntryRow
from lib.formats import generate_atok, generate_google, generate_ms_ime, generate_skk

GOLDEN = Path(__file__).parent / "fixtures" / "golden"

ROWS = [
    EntryRow(
        2,
        {
            "person_id": "zeta-k4sen",
            "surface": "K4SEN",
            "reading": "かせん",
            "reading_source": "self_channel_title",
            "source_url": "https://www.youtube.com/channel/UChUjERVG8eKEAJSCef-tTmg",
            "org": "ZETA DIVISION",
            "org_source_url": "https://zetadivision.com/members",
            "status": "active",
            "added": "2026-09-07",
            "note": "",
        },
    ),
    EntryRow(
        3,
        {
            "person_id": "nijisanji-kuzuha",
            "surface": "葛葉",
            "reading": "くずは",
            "reading_source": "org_romaji",
            "source_url": "https://www.nijisanji.jp/talents",
            "org": "にじさんじ",
            "org_source_url": "https://www.nijisanji.jp/talents",
            "status": "active",
            "added": "2026-09-07",
            "note": "",
        },
    ),
]


def test_ms_ime_matches_golden():
    assert generate_ms_ime(ROWS) == (GOLDEN / "ms-ime.bin").read_bytes()


def test_ms_ime_is_utf16_le_bom_with_crlf():
    data = generate_ms_ime(ROWS)
    assert data.startswith(b"\xff\xfe")  # UTF-16LE BOM
    text = data.decode("utf-16")
    assert "\r\n" in text
    assert "かせん\tK4SEN\t人名" in text


def test_google_matches_golden():
    assert generate_google(ROWS) == (GOLDEN / "google-mozc.txt").read_bytes()


def test_google_is_utf8_no_bom():
    data = generate_google(ROWS)
    assert not data.startswith(b"\xef\xbb\xbf")
    text = data.decode("utf-8")
    assert "かせん\tK4SEN\t人名\tZETA DIVISION" in text


def test_atok_matches_golden():
    assert generate_atok(ROWS) == (GOLDEN / "atok.bin").read_bytes()


def test_atok_starts_with_header_and_is_utf16_crlf():
    data = generate_atok(ROWS)
    assert data.startswith(b"\xff\xfe")
    text = data.decode("utf-16")
    lines = text.split("\r\n")
    assert lines[0] == "!!ATOK_TANGO_TEXT_HEADER_1"
    assert "かせん\tK4SEN\t固有人名" in lines


def test_skk_matches_golden():
    assert generate_skk(ROWS) == (GOLDEN / "skk.txt").read_bytes()


def test_skk_merges_same_reading_into_one_line():
    rows = ROWS + [
        EntryRow(
            4,
            {
                "person_id": "other-kasen",
                "surface": "かせん２",
                "reading": "かせん",
                "reading_source": "pr_manual",
                "source_url": "https://example.com",
                "org": "",
                "org_source_url": "",
                "status": "active",
                "added": "2026-09-07",
                "note": "",
            },
        )
    ]
    text = generate_skk(rows).decode("utf-8")
    assert "かせん /K4SEN/かせん２/" in text


def test_skk_deduplicates_identical_surface_for_same_reading():
    rows = ROWS + [ROWS[0]]  # 同じ行を重ねても候補は増えない
    text = generate_skk(rows).decode("utf-8")
    assert text.count("K4SEN") == 1


def test_empty_rows_produce_empty_but_valid_output():
    assert generate_ms_ime([]).decode("utf-16") == ""
    assert generate_google([]) == b""
    atok_text = generate_atok([]).decode("utf-16")
    assert atok_text == "!!ATOK_TANGO_TEXT_HEADER_1\r\n"
    # SKK は空辞書でも skk-dev 規約の2ヘッダ行だけは必ず出力する
    assert generate_skk([]).decode("utf-8") == ";; okuri-ari entries.\n;; okuri-nasi entries.\n"


def test_skk_always_includes_required_skk_dev_headers():
    """skk-dev の辞書規約（committers.md）は okuri-ari / okuri-nasi の2行を必須と定めている。

    本辞書は送りあり活用語を扱わないため okuri-ari 節は常に空で、
    全項目は okuri-nasi ヘッダの後ろに置かれる。
    """
    text = generate_skk(ROWS).decode("utf-8")
    lines = text.split("\n")
    assert lines[0] == ";; okuri-ari entries."
    assert lines[1] == ";; okuri-nasi entries."
    # okuri-ari と okuri-nasi の間に項目行が無い（送りあり節は空）
    assert lines[2] != ";; okuri-ari entries." and lines[2] != ";; okuri-nasi entries."
