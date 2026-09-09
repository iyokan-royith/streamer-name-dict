"""各 IME 向け辞書形式の生成。

細部（ヘッダ・品詞名・エンコーディング）の実機確認は README.md「使い方」節のとおり募集中。
ここでは DESIGN.md の決定（品詞は「人名」、ATOK は「固有人名」）をそのまま実装する。
"""
from __future__ import annotations

from .entries import EntryRow

CRLF = "\r\n"

MS_IME_POS = "人名"
GOOGLE_POS = "人名"
ATOK_POS = "固有人名"
ATOK_HEADER = "!!ATOK_TANGO_TEXT_HEADER_1"

# skk-dev 辞書規約（committers.md）: どんな小さな辞書でも必須の2行
SKK_OKURI_ARI_HEADER = ";; okuri-ari entries."
SKK_OKURI_NASI_HEADER = ";; okuri-nasi entries."

# SKK-JISYO.L（skk-dev/dict）の実例で確認済み: ヴ音のひらがな表記は「ゔ」（U+3094・結合済み1文字）
# ではなく「う゛」（う U+3046 + 濁点 U+309B・2文字）で見出しに現れる
# （実例: "ぐるーう゛かん /グルーヴ感/"・"しう゛ぁ /湿婆/"）。SKKIME 等の `vu` ローマ字入力も
# 「う゛」を生成するため、SKK 形式の見出しだけこの表記に変換する。
# data/entries.tsv・data/aliases.tsv 側の正本は「ゔ」のまま変更しない（他の3形式は「ゔ」を使う）。
def _to_skk_vu_notation(reading: str) -> str:
    return reading.replace("ゔ", "う゛")


def generate_ms_ime(rows: list[EntryRow]) -> bytes:
    """MS-IME（Microsoft IME）ユーザー辞書インポート用テキスト。

    UTF-16LE（BOM 付き）・CRLF・「読み\\t表記\\t品詞」。
    """
    lines = [f"{row['reading']}\t{row['surface']}\t{MS_IME_POS}" for row in rows]
    text = CRLF.join(lines) + (CRLF if lines else "")
    return text.encode("utf-16")  # Python の "utf-16" は LE + BOM を付与する


def generate_google(rows: list[EntryRow]) -> bytes:
    """Google 日本語入力 / Mozc ユーザー辞書インポート用テキスト。

    UTF-8（BOM 無し）・「読み\\t表記\\t品詞\\tコメント」。コメント欄には org を入れる（無ければ空欄）。
    """
    lines = []
    for row in rows:
        comment = row["org"]
        lines.append(f"{row['reading']}\t{row['surface']}\t{GOOGLE_POS}\t{comment}")
    text = "\n".join(lines) + ("\n" if lines else "")
    return text.encode("utf-8")


def generate_atok(rows: list[EntryRow]) -> bytes:
    """ATOK 単語一括登録用テキスト。

    UTF-16LE（BOM 付き）・CRLF・先頭行がヘッダ・以降「読み\\t表記\\t品詞」。
    """
    lines = [ATOK_HEADER]
    lines += [f"{row['reading']}\t{row['surface']}\t{ATOK_POS}" for row in rows]
    text = CRLF.join(lines) + CRLF
    return text.encode("utf-16")


def generate_skk(rows: list[EntryRow]) -> bytes:
    """SKK 辞書（UTF-8）。

    同じ reading を持つ行は1行にまとめる: `よみ /表記1/表記2/`
    読みの Unicode コードポイント順にソートする（バイナリサーチ前提の厳密な SKK 辞書ソートではないが、
    個人利用の追加辞書としては十分。SKK 本家の辞書ソート順（版によっては特殊な照合順）と
    厳密に一致するかは実機未確認）。

    skk-dev の辞書規約（`committers.md`）は、どんな小さな辞書でも
    `;; okuri-ari entries.` `;; okuri-nasi entries.` の2行を必ず含めることを定めている。
    本辞書は送りあり活用語を扱わないため okuri-ari 節は空にし、全項目を okuri-nasi 節に置く。

    読みに「ゔ」を含む場合は、SKK の慣習に合わせて見出しだけ「う゛」に変換する
    （`_to_skk_vu_notation` 参照）。変換後の文字列でグルーピング・ソートするため、
    「ゔ」と「う゛」で読みが実質同じ項目は自動的に1行へ統合される。
    """
    grouped: dict[str, list[str]] = {}
    for row in rows:
        reading = _to_skk_vu_notation(row["reading"])
        surfaces = grouped.setdefault(reading, [])
        if row["surface"] not in surfaces:
            surfaces.append(row["surface"])

    lines = [SKK_OKURI_ARI_HEADER, SKK_OKURI_NASI_HEADER]
    for reading in sorted(grouped):
        candidates = "/".join(grouped[reading])
        lines.append(f"{reading} /{candidates}/")
    text = "\n".join(lines) + "\n"
    return text.encode("utf-8")


FORMAT_GENERATORS = {
    "streamer_dict_msime.txt": generate_ms_ime,
    "streamer_dict_google_mozc.txt": generate_google,
    "streamer_dict_atok.txt": generate_atok,
    "streamer_dict_skk.txt": generate_skk,
}
