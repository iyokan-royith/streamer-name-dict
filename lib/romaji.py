"""ローマ字（ヘボン式主体）→ ひらがな の機械変換。

用途は `org_romaji`（公式情報にローマ字表記しか無い場合に、人が確認するための読み案を作る）。
**この変換は常に候補であり、人の確認（`needs_review=yes`）を前提とする**。
そのため「それらしい1案を返す」ことを優先し、揺れ（長音・促音・撥音）は深追いしない。

変換できない入力（ピンイン系のローマ字・英語圏 VTuber の英語名など、ヘボン式のモーラに
分解できない文字列）は例外を投げず `None` を返す（純関数として扱いやすくするため）。
呼び出し側は `None` を「機械かな化できなかった」として扱い、reading を空・needs_review=yes にする。
"""
from __future__ import annotations

import re

# --- カタカナ→ひらがな -------------------------------------------------

_KATAKANA_LO = 0x30A1  # ァ
_KATAKANA_HI = 0x30FA  # ヺ（ヴ=0x30F4 を含む）
_KATA_HIRA_OFFSET = 0x60

# reading として不要な区切り文字（人名の姓名区切り「・」・空白）
_DROP_CHARS = set("・ 　")

_TRAILING_KATAKANA_RE = re.compile(r"([ァ-ヺー]+)$")


def katakana_to_hiragana(s: str) -> str:
    """カタカナをひらがなに変換する。長音符「ー」はそのまま残す。

    「・」「 」（姓名区切り）は読みに不要なので取り除く。ヴ（U+30F4）は ゔ（U+3094）になる
    （validate.py の HIRAGANA_RE がヴ音のひらがな表記として許容している）。
    """
    out: list[str] = []
    for ch in s:
        code = ord(ch)
        if ch in _DROP_CHARS:
            continue
        if _KATAKANA_LO <= code <= _KATAKANA_HI:
            out.append(chr(code - _KATA_HIRA_OFFSET))
        else:
            out.append(ch)
    return "".join(out)


_HIRAGANA_ONLY_RE = re.compile(r"^[ぁ-んーゔ]+$")
_KANA_SURFACE_RE = re.compile(r"^[ぁ-んァ-ヶーゔ・\s]+$")


def is_kana_only_surface(surface: str) -> bool:
    """表記がひらがな・カタカナ・長音・区切りのみで構成されている（漢字を含まない）か。"""
    return bool(surface) and bool(_KANA_SURFACE_RE.match(surface))


def hiraganize_kana_surface(surface: str) -> str:
    """かなのみの表記を、読みとして使えるひらがな文字列にする（区切り除去込み）。"""
    return katakana_to_hiragana(surface)


# --- ローマ字→ひらがな --------------------------------------------------

# 拗音（3文字綴り）。長さ優先で先に試す。
_YOON = {
    "kya": "きゃ", "kyu": "きゅ", "kyo": "きょ",
    "sha": "しゃ", "shu": "しゅ", "sho": "しょ",
    "sya": "しゃ", "syu": "しゅ", "syo": "しょ",
    "cha": "ちゃ", "chu": "ちゅ", "cho": "ちょ",
    "tya": "ちゃ", "tyu": "ちゅ", "tyo": "ちょ",
    "nya": "にゃ", "nyu": "にゅ", "nyo": "にょ",
    "hya": "ひゃ", "hyu": "ひゅ", "hyo": "ひょ",
    "mya": "みゃ", "myu": "みゅ", "myo": "みょ",
    "rya": "りゃ", "ryu": "りゅ", "ryo": "りょ",
    "lya": "りゃ", "lyu": "りゅ", "lyo": "りょ",
    "gya": "ぎゃ", "gyu": "ぎゅ", "gyo": "ぎょ",
    "jya": "じゃ", "jyu": "じゅ", "jyo": "じょ",
    "bya": "びゃ", "byu": "びゅ", "byo": "びょ",
    "pya": "ぴゃ", "pyu": "ぴゅ", "pyo": "ぴょ",
    "dya": "ぢゃ", "dyu": "ぢゅ", "dyo": "ぢょ",
}

# 通常のモーラ（1〜3文字綴り）。
_MORA = {
    "a": "あ", "i": "い", "u": "う", "e": "え", "o": "お",
    "ka": "か", "ki": "き", "ku": "く", "ke": "け", "ko": "こ",
    "sa": "さ", "shi": "し", "si": "し", "su": "す", "se": "せ", "so": "そ",
    "ta": "た", "chi": "ち", "ti": "ち", "tsu": "つ", "tu": "つ", "te": "て", "to": "と",
    "na": "な", "ni": "に", "nu": "ぬ", "ne": "ね", "no": "の",
    "ha": "は", "hi": "ひ", "fu": "ふ", "hu": "ふ", "he": "へ", "ho": "ほ",
    "ma": "ま", "mi": "み", "mu": "む", "me": "め", "mo": "も",
    "ya": "や", "yu": "ゆ", "yo": "よ",
    "ra": "ら", "ri": "り", "ru": "る", "re": "れ", "ro": "ろ",
    "la": "ら", "li": "り", "lu": "る", "le": "れ", "lo": "ろ",
    "wa": "わ", "wo": "を",
    "ga": "が", "gi": "ぎ", "gu": "ぐ", "ge": "げ", "go": "ご",
    "za": "ざ", "ji": "じ", "zi": "じ", "zu": "ず", "ze": "ぜ", "zo": "ぞ",
    "ja": "じゃ", "ju": "じゅ", "jo": "じょ",
    "da": "だ", "di": "ぢ", "du": "づ", "de": "で", "do": "ど",
    "ba": "ば", "bi": "び", "bu": "ぶ", "be": "べ", "bo": "ぼ",
    "pa": "ぱ", "pi": "ぴ", "pu": "ぷ", "pe": "ぺ", "po": "ぽ",
    "va": "ゔぁ", "vi": "ゔぃ", "vu": "ゔ", "ve": "ゔぇ", "vo": "ゔぉ",
}

# 撥音「ん」の直後に来ても「な行」に化けない子音（同じ子音の連続や b/p 前の m 変換の判定に使う）
_CONSONANTS = set("bcdfghjklmpqrstvwxyz")
_VOWELS = set("aeiou")

_MAX_MORA_LEN = 3


def _mora_at(s: str, i: int) -> tuple[str, int] | None:
    """位置 i から始まる最長一致のモーラを (かな, 消費文字数) で返す。無ければ None。

    文字列末尾付近では `s[i:i+length]` が `length` より短くなりうる（Python のスライスは
    範囲外を静かに切り詰める）ため、実際の長さが要求と一致する場合のみ候補として扱う。
    """
    for length in (3, 2, 1):
        seg = s[i : i + length]
        if len(seg) != length:
            continue
        if length == 3 and seg in _YOON:
            return _YOON[seg], 3
        if seg in _MORA:
            return _MORA[seg], length
    return None


def _convert_word(word: str) -> str | None:
    """1単語（空白を含まないローマ字）をひらがなに変換する。失敗したら None。"""
    s = re.sub(r"[^a-z']", "", word.lower())
    if not s:
        return None
    # 英語風の綴りで /k/ を表す単独の "c"（"ch" 以外）を "k" に正規化する
    # （例: "Robocosan" → "robokosan"、"Choco" → "choko"）。
    s = re.sub(r"c(?!h)", "k", s)

    out: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]

        if c == "'":
            i += 1
            continue

        if c == "n":
            nxt = s[i + 1] if i + 1 < n else ""
            if nxt == "'":
                out.append("ん")
                i += 2
                continue
            if nxt in _VOWELS or nxt == "y":
                pass  # な行・にゃ行としてモーラ表に任せる（下の通常処理へ）
            else:
                out.append("ん")
                i += 1
                continue

        if c == "m":
            nxt = s[i + 1] if i + 1 < n else ""
            if nxt in ("b", "p"):
                out.append("ん")
                i += 1
                continue

        # 促音（同じ子音の連続。ex. kk, ss, pp, tt）
        if (
            c in _CONSONANTS
            and c != "n"
            and i + 1 < n
            and s[i + 1] == c
        ):
            out.append("っ")
            i += 1
            continue

        # tch → っ + ch...（例: "matcha" の "tch"）
        if s[i : i + 3] == "tch":
            out.append("っ")
            i += 1
            continue

        matched = _mora_at(s, i)
        if matched is None:
            return None  # x, q, c(非ch) など未対応の綴り → 変換不能
        kana, consumed = matched
        out.append(kana)
        i += consumed

    return "".join(out)


def _trailing_kana_reading(surface: str) -> str | None:
    """表記の末尾がカタカナ（長音含む）なら、そのひらがな読みを返す（語順判定用）。"""
    m = _TRAILING_KATAKANA_RE.search(surface)
    if not m:
        return None
    return katakana_to_hiragana(m.group(1))


def romaji_to_hiragana(romaji: str, surface: str | None = None) -> str | None:
    """ローマ字表記をひらがなに変換する。

    `surface`（出典の日本語表記）を渡すと、語順（姓名の順）を表記に合わせて調整する。
    表記の末尾がカタカナ表記（例: `緋笠トモシカ` の `トモシカ`）の場合、そのカタカナに
    対応する単語を末尾に置く（`Tomoshika Hikasa` のように語順が逆でも `Hikasa Tomoshika`
    の順に直してから連結する）。表記が全て漢字などで手がかりが無ければ、渡された語順のまま連結する。

    変換できない単語が1つでもあれば全体として `None` を返す（機械かな化を諦める）。
    """
    words = romaji.split()
    if not words:
        return None

    hiraganized = [_convert_word(w) for w in words]
    if any(h is None for h in hiraganized):
        return None

    if surface and len(hiraganized) > 1:
        target = _trailing_kana_reading(surface)
        if target is not None and target in hiraganized:
            idx = hiraganized.index(target)
            hiraganized = [h for j, h in enumerate(hiraganized) if j != idx] + [target]

    return "".join(hiraganized)
