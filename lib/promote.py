"""候補 TSV を data/entries.tsv へ取り込む（メンテナ用）。

候補 TSV →（本ファイル）→ data/entries.tsv

ここではファイル I/O を含まない純粋なマージロジックだけを持つ（テスト容易性のため）。
CLI（読み込み・書き出し・validate 呼び出し）は promote.py（リポジトリ直下）が担う。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .entries import EntryRow, FIELDS

# 候補 TSV の列: entries.tsv の全列＋ reading_candidate（かな読みの案）／needs_review（yes/no）／
# romaji（出典に書かれていたローマ字そのまま。無ければ空）。
CANDIDATE_FIELDS = FIELDS + ["reading_candidate", "needs_review", "romaji"]

# DESIGN.md「reading_source の種別（信頼度順）」の表に書かれている並び順。
# インデックスが小さいほど信頼度が高い（＝先に出てくるものほど信頼できる）。
READING_SOURCE_CONFIDENCE = [
    "org_kana",
    "kana_surface",
    "self_channel_title",
    "self_profile",
    "wikidata",
    "wikipedia",
    "org_romaji",
    "pr_manual",
]

# 更新（信頼度昇格）時に candidate 側の値へ差し替える列。
# 昇格時は source_url・note も差し替え、added は据え置く。
# person_id・surface・reading・org・org_source_url・status・added は既存のまま残す。
_UPGRADE_FIELDS = ["reading_source", "source_url", "note"]


def _confidence(source: str) -> int:
    """reading_source の信頼度（小さいほど高信頼）。定義外の値は最低信頼度扱いにする。

    validate 側で定義外の値は別途弾かれる想定だが、ここで誤って昇格させないための保険。
    """
    try:
        return READING_SOURCE_CONFIDENCE.index(source)
    except ValueError:
        return len(READING_SOURCE_CONFIDENCE)


@dataclass
class PromoteResult:
    """1回の promote 実行の結果。"""

    entries: list[dict[str, str]] = field(default_factory=list)
    added: list[dict[str, str]] = field(default_factory=list)
    upgraded: list[tuple[dict[str, str], dict[str, str]]] = field(default_factory=list)  # (before, after)
    unchanged: list[dict[str, str]] = field(default_factory=list)
    skipped_needs_review: list[dict[str, str]] = field(default_factory=list)
    skipped_removed: list[dict[str, str]] = field(default_factory=list)
    skipped_duplicate_candidate: list[dict[str, str]] = field(default_factory=list)
    conflicts: list[tuple[dict[str, str], dict[str, str]]] = field(default_factory=list)  # (existing, candidate)

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)


def _is_promotable(candidate: dict[str, str]) -> bool:
    """needs_review=no かつ reading が空でない行だけを取り込み対象にする。"""
    return candidate.get("needs_review", "").strip() == "no" and bool(candidate.get("reading", "").strip())


def promote_candidates(
    existing_rows: list[EntryRow],
    candidate_rows: list[dict[str, str]],
) -> PromoteResult:
    """既存 entries と候補行をマージし、新しい entries 全体と集計を返す（ファイルには書かない）。

    - needs_review!=no または reading 空の候補行はスキップする
    - **突き合わせの単位は `person_id`+`surface`**（entries.tsv は `person_id`+`surface` で一意
      ＝同一人物の別表記〈英字表記・ハングル表記等〉を別行として持てる。DESIGN.md「データモデル」）。
      person_id だけで突き合わせると、同一人物の新しい surface が既存の別 surface の行と
      誤って比較され「変更なし」に握りつぶされたり、無関係な衝突として弾かれたりする
      （2026-09-09 に発覚した既知課題・alt surfaces 導入で顕在化）。
    - (person_id, surface) の組が既存に無ければ新規追加
    - **ただし削除申請は `person_id` 単位（DESIGN.md「データモデル」）**。候補の `person_id` が
      既存 entries の中に `status=removed` の行を1本でも持っていれば、その候補の `surface` が
      既存のどの行とも一致しない（＝新しい別表記）場合であっても追加しない（skipped_removed 扱い）。
      削除申請された人物に、別 surface の候補（英字表記・愛称由来の別表記など）が後から来て
      復活してしまうのを防ぐ（2026-09-09 発覚: (person_id, surface) 単位の突き合わせにしたことで
      removed 据え置きが surface 単位に縮んでいた）
    - (person_id, surface) の組が既存にあり status=removed なら触らない（復活させない・上の
      person_id 単位の判定に包含される）
    - (person_id, surface) の組が既存にあり reading が同じなら、reading_source の信頼度が
      上がる時だけ更新（source_url・note を差し替え、added は据え置き）。信頼度が同じか下がる
      なら何もしない
    - (person_id, surface) の組が既存にあり reading が違うなら衝突として記録する
      （呼び出し側が書き込みを止める）
    - 同じ (person_id, surface) の候補行が複数（例: 複数の候補 TSV にまたがる）場合、
      最初の1件だけを採用し、以降は重複としてスキップする
    """
    ordered_entries: list[dict[str, str]] = [dict(row.data) for row in existing_rows]
    by_key: dict[tuple[str, str], dict[str, str]] = {
        (row["person_id"], row["surface"]): row for row in ordered_entries
    }
    # 削除申請は person_id 単位（DESIGN.md「データモデル」）。既存 entries の中で1本でも
    # status=removed の行を持つ person_id は、新しい surface の候補が来ても丸ごと据え置く。
    removed_person_ids: set[str] = {row["person_id"] for row in ordered_entries if row["status"] == "removed"}

    result = PromoteResult()
    seen_candidate_keys: set[tuple[str, str]] = set()

    for candidate in candidate_rows:
        if not _is_promotable(candidate):
            result.skipped_needs_review.append(candidate)
            continue

        key = (candidate["person_id"], candidate["surface"])

        if key in seen_candidate_keys:
            result.skipped_duplicate_candidate.append(candidate)
            continue
        seen_candidate_keys.add(key)

        if candidate["person_id"] in removed_person_ids:
            result.skipped_removed.append(candidate)
            continue

        existing = by_key.get(key)

        if existing is None:
            new_row = {f: candidate.get(f, "") for f in FIELDS}
            ordered_entries.append(new_row)
            by_key[key] = new_row
            result.added.append(new_row)
            continue

        if existing["reading"] == candidate["reading"]:
            if _confidence(candidate["reading_source"]) < _confidence(existing["reading_source"]):
                before = dict(existing)
                for f in _UPGRADE_FIELDS:
                    existing[f] = candidate.get(f, existing[f])
                result.upgraded.append((before, dict(existing)))
            else:
                result.unchanged.append(existing)
        else:
            result.conflicts.append((dict(existing), candidate))

    result.entries = ordered_entries
    return result
