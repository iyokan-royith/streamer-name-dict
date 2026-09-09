"""data/aliases.tsv の読み込みとスキーマ定義。

entries.tsv とは別ファイル（DESIGN.md「データモデル」の aliases 節参照）。
出典を持つ「公式の読み」を主張する entries.tsv に対し、こちらは
「愛称」「同じ表記への別読み（表記揺れ）」という、出典を求めない補助情報を持つ。
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

# aliases.tsv の列
FIELDS = [
    "person_id",
    "surface",
    "reading",
    "kind",
    "note",
    "added",
]

# 空欄を許可しない列（note は自由記述なので空でよい）
REQUIRED_FIELDS = [
    "person_id",
    "surface",
    "reading",
    "kind",
    "added",
]

# kind の定義済み値
# - nickname: 表記が正式名と異なる愛称
# - reading_variant: 表記は正式名と同じだが、別の読みが通用している（表記揺れ）
# - family_name: 正式名の姓の部分だけ（surface は正式名の部分文字列・reading はその部分の読み）
# - given_name: 正式名の名の部分だけ（同上）
# - short_name: 本人が名乗る短縮名からフルネームへの変換（surface は正式名そのもの・reading は短縮名の読み）
VALID_KINDS = {"nickname", "reading_variant", "family_name", "given_name", "short_name"}

# surface が同じ person_id の正式名の部分文字列であることを求める kind
NAME_PART_KINDS = {"family_name", "given_name"}
# surface が同じ person_id の正式名と一致することを求める kind
FULL_SURFACE_KINDS = {"reading_variant", "short_name"}


@dataclass
class AliasRow:
    """1 行ぶんのデータ＋TSV 上の行番号（エラーメッセージ用）。"""

    line_no: int  # ヘッダを含めた実際のファイル上の行番号（1始まり）
    data: dict[str, str]

    def __getitem__(self, key: str) -> str:
        return self.data.get(key, "")


def active_aliases(rows: list[AliasRow], active_person_ids: set[str]) -> list[AliasRow]:
    """紐づく person_id が active_person_ids に含まれる alias だけを返す（配布物向け）。

    entries.tsv 側で person_id が削除（status=removed）されると、その person_id の alias は
    ここで連動して除外される（人物ごと消える。DESIGN.md 参照）。
    """
    return [r for r in rows if r["person_id"] in active_person_ids]


def load_aliases(path: str | Path) -> list[AliasRow]:
    """aliases.tsv を読み込み、AliasRow のリストを返す。"""
    path = Path(path)
    rows: list[AliasRow] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for i, raw in enumerate(reader):
            line_no = i + 2
            data = {k: (v if v is not None else "") for k, v in raw.items() if k is not None}
            rows.append(AliasRow(line_no=line_no, data=data))
    return rows
