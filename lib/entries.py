"""entries.tsv の読み込みとスキーマ定義。

単一の真実は data/entries.tsv（DESIGN.md「データモデル」参照）。
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

# entries.tsv の列（DESIGN.md の順序と一致させる）
FIELDS = [
    "person_id",
    "surface",
    "reading",
    "reading_source",
    "source_url",
    "org",
    "org_source_url",
    "status",
    "added",
    "note",
]

# 空欄を許可しない列（org / org_source_url / note は個人勢で空でよい）
REQUIRED_FIELDS = [
    "person_id",
    "surface",
    "reading",
    "reading_source",
    "source_url",
    "status",
    "added",
]

# reading_source の定義済み値（DESIGN.md「reading_source の種別」表）
VALID_READING_SOURCES = {
    "org_kana",
    "org_romaji",
    "self_channel_title",
    "self_profile",
    "kana_surface",
    "wikidata",
    "wikipedia",
    "pr_manual",
}

VALID_STATUSES = {"active", "removed"}


@dataclass
class EntryRow:
    """1 行ぶんのデータ＋TSV 上の行番号（エラーメッセージ用）。"""

    line_no: int  # ヘッダを含めた実際のファイル上の行番号（1始まり）
    data: dict[str, str]

    def __getitem__(self, key: str) -> str:
        return self.data.get(key, "")


def load_entries(path: str | Path) -> list[EntryRow]:
    """entries.tsv を読み込み、EntryRow のリストを返す。

    列が過不足していても DictReader は許容する（欠落列は None/欠損キーになりうる）ため、
    値の有無チェックは validate 側で行う。
    """
    path = Path(path)
    rows: list[EntryRow] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for i, raw in enumerate(reader):
            # DictReader は行番号を保持しないので、ヘッダ行(1) + 現在までのデータ行数 + 1 で復元する
            line_no = i + 2
            data = {k: (v if v is not None else "") for k, v in raw.items() if k is not None}
            rows.append(EntryRow(line_no=line_no, data=data))
    return rows


def active_rows(rows: list[EntryRow]) -> list[EntryRow]:
    """配布物に含める行を返す（削除後は配布物に含めない。`data/` の管理用の行は `status=removed` として残る）。"""
    return [r for r in rows if r["status"] != "removed"]


def active_person_ids(rows: list[EntryRow]) -> set[str]:
    """status=active の行を1つでも持つ person_id の集合を返す。

    aliases.tsv 側の除外判定（削除申請された人物の alias を build から連動除外する）に使う。
    """
    return {r["person_id"] for r in rows if r["status"] == "active"}
