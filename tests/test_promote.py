"""lib/promote.py の純関数（promote_candidates）のテスト。"""
from lib.entries import EntryRow, FIELDS
from lib.promote import promote_candidates


def make_entry_row(line_no: int, **overrides) -> EntryRow:
    base = {
        "person_id": "zeta-k4sen",
        "surface": "K4SEN",
        "reading": "かせん",
        "reading_source": "self_channel_title",
        "source_url": "https://example.com/k4sen",
        "org": "ZETA DIVISION",
        "org_source_url": "https://example.com/org",
        "status": "active",
        "added": "2026-09-07",
        "note": "",
    }
    base.update(overrides)
    return EntryRow(line_no=line_no, data=base)


def make_candidate(**overrides) -> dict[str, str]:
    base = {
        "person_id": "new-person",
        "surface": "新人",
        "reading": "しんじん",
        "reading_source": "org_kana",
        "source_url": "https://example.com/new",
        "org": "テスト事務所",
        "org_source_url": "https://example.com/test-org",
        "status": "active",
        "added": "2026-09-08",
        "note": "テスト候補",
        "reading_candidate": "しんじん",
        "needs_review": "no",
        "romaji": "Shinjin",
    }
    base.update(overrides)
    return base


def test_new_person_is_added():
    result = promote_candidates([], [make_candidate()])
    assert len(result.added) == 1
    assert result.entries[0]["person_id"] == "new-person"
    # entries.tsv の全列だけが渡る（reading_candidate 等の候補固有列は落ちる）
    assert set(result.entries[0].keys()) == set(FIELDS)
    assert not result.upgraded
    assert not result.conflicts


def test_needs_review_yes_is_skipped():
    result = promote_candidates([], [make_candidate(needs_review="yes", reading="")])
    assert not result.added
    assert len(result.skipped_needs_review) == 1


def test_needs_review_no_but_reading_empty_is_skipped():
    # needs_review=no のはずが reading が空という壊れた入力も安全側でスキップする
    result = promote_candidates([], [make_candidate(reading="")])
    assert not result.added
    assert len(result.skipped_needs_review) == 1


def test_same_reading_lower_confidence_source_is_unchanged():
    existing = [make_entry_row(2, reading_source="org_kana")]
    # org_romaji は org_kana より信頼度が低いので更新しない
    candidate = make_candidate(
        person_id="zeta-k4sen", surface="K4SEN", reading="かせん", reading_source="org_romaji"
    )
    result = promote_candidates(existing, [candidate])
    assert not result.upgraded
    assert len(result.unchanged) == 1
    assert result.entries[0]["reading_source"] == "org_kana"


def test_same_reading_same_confidence_source_is_unchanged():
    existing = [make_entry_row(2, reading_source="kana_surface")]
    candidate = make_candidate(person_id="zeta-k4sen", surface="K4SEN", reading="かせん", reading_source="kana_surface")
    result = promote_candidates(existing, [candidate])
    assert not result.upgraded
    assert len(result.unchanged) == 1


def test_same_reading_higher_confidence_source_upgrades():
    existing = [make_entry_row(2, reading_source="org_romaji", note="旧note")]
    candidate = make_candidate(
        person_id="zeta-k4sen",
        surface="K4SEN",
        reading="かせん",
        reading_source="org_kana",
        source_url="https://example.com/new-source",
        note="新note",
    )
    result = promote_candidates(existing, [candidate])
    assert len(result.upgraded) == 1
    before, after = result.upgraded[0]
    assert before["reading_source"] == "org_romaji"
    assert after["reading_source"] == "org_kana"
    assert after["source_url"] == "https://example.com/new-source"
    assert after["note"] == "新note"
    # added・org・org_source_url・surface・status は据え置き
    assert after["added"] == before["added"]
    assert after["org"] == before["org"]
    assert after["org_source_url"] == before["org_source_url"]
    assert result.entries[0]["reading_source"] == "org_kana"


def test_self_profile_outranks_org_romaji():
    # DESIGN.md の訂正後順序: self_* は org_romaji より信頼度が高い
    # （org_romaji は機械かな化を人が目視確認しただけで、self_* は本人の自己申告）。
    # 旧順序（org_romaji を self_* より上に置いていた）だとこの昇格は起きなかった。
    existing = [make_entry_row(2, reading_source="org_romaji", note="旧note")]
    candidate = make_candidate(
        person_id="zeta-k4sen",
        surface="K4SEN",
        reading="かせん",
        reading_source="self_profile",
        note="新note",
    )
    result = promote_candidates(existing, [candidate])
    assert len(result.upgraded) == 1
    before, after = result.upgraded[0]
    assert before["reading_source"] == "org_romaji"
    assert after["reading_source"] == "self_profile"


def test_self_channel_title_outranks_org_romaji():
    existing = [make_entry_row(2, reading_source="org_romaji")]
    candidate = make_candidate(
        person_id="zeta-k4sen", surface="K4SEN", reading="かせん", reading_source="self_channel_title"
    )
    result = promote_candidates(existing, [candidate])
    assert len(result.upgraded) == 1


def test_self_profile_outranks_wikidata_outranks_wikipedia_outranks_org_romaji():
    # DESIGN.md「reading_source の種別」の順序: self_profile > wikidata > wikipedia > org_romaji
    existing_org_romaji = [make_entry_row(2, reading_source="org_romaji")]
    upgraded_to_wikipedia = promote_candidates(
        existing_org_romaji,
        [make_candidate(person_id="zeta-k4sen", surface="K4SEN", reading="かせん", reading_source="wikipedia")],
    )
    assert len(upgraded_to_wikipedia.upgraded) == 1
    assert upgraded_to_wikipedia.upgraded[0][1]["reading_source"] == "wikipedia"

    existing_wikipedia = [make_entry_row(2, reading_source="wikipedia")]
    upgraded_to_wikidata = promote_candidates(
        existing_wikipedia,
        [make_candidate(person_id="zeta-k4sen", surface="K4SEN", reading="かせん", reading_source="wikidata")],
    )
    assert len(upgraded_to_wikidata.upgraded) == 1
    assert upgraded_to_wikidata.upgraded[0][1]["reading_source"] == "wikidata"

    existing_wikidata = [make_entry_row(2, reading_source="wikidata")]
    upgraded_to_self_profile = promote_candidates(
        existing_wikidata,
        [make_candidate(person_id="zeta-k4sen", surface="K4SEN", reading="かせん", reading_source="self_profile")],
    )
    assert len(upgraded_to_self_profile.upgraded) == 1
    assert upgraded_to_self_profile.upgraded[0][1]["reading_source"] == "self_profile"


def test_different_reading_is_a_conflict_and_does_not_mutate_entries():
    existing = [make_entry_row(2, reading="かせん")]
    candidate = make_candidate(person_id="zeta-k4sen", surface="K4SEN", reading="べつのよみ")
    result = promote_candidates(existing, [candidate])
    assert result.has_conflicts
    assert len(result.conflicts) == 1
    existing_snapshot, candidate_snapshot = result.conflicts[0]
    assert existing_snapshot["reading"] == "かせん"
    assert candidate_snapshot["reading"] == "べつのよみ"
    # 既存行はそのまま（衝突相手には触れない）
    assert result.entries[0]["reading"] == "かせん"


def test_removed_status_is_left_untouched():
    existing = [make_entry_row(2, status="removed", reading="かせん", reading_source="self_profile")]
    # 信頼度が上がる候補が来ても reading が違っていても removed には触れない
    candidate = make_candidate(person_id="zeta-k4sen", surface="K4SEN", reading="ちがうよみ", reading_source="org_kana")
    result = promote_candidates(existing, [candidate])
    assert len(result.skipped_removed) == 1
    assert not result.upgraded
    assert not result.conflicts
    assert result.entries[0]["status"] == "removed"
    assert result.entries[0]["reading"] == "かせん"


def test_duplicate_key_across_candidate_rows_only_promotes_first():
    candidate_a = make_candidate(person_id="dup-person", reading="いちばん")
    candidate_b = make_candidate(person_id="dup-person", reading="にばんめ")
    result = promote_candidates([], [candidate_a, candidate_b])
    assert len(result.added) == 1
    assert result.entries[0]["reading"] == "いちばん"
    assert len(result.skipped_duplicate_candidate) == 1


def test_same_person_id_different_surface_candidates_are_both_added_not_treated_as_duplicate():
    """突き合わせキーは (person_id, surface) なので、同じ person_id でも surface が違えば
    別候補として扱い、両方とも追加される（重複スキップにならない）。"""
    candidate_a = make_candidate(person_id="multi-surface-person", surface="表記A", reading="ひょうきA")
    candidate_b = make_candidate(person_id="multi-surface-person", surface="表記B", reading="ひょうきB")
    result = promote_candidates([], [candidate_a, candidate_b])
    assert len(result.added) == 2
    assert not result.skipped_duplicate_candidate
    assert {r["surface"] for r in result.entries} == {"表記A", "表記B"}


def test_removed_person_blocks_new_surface_candidate_even_when_surface_differs():
    """2026-09-09 監査差し戻し: 削除申請は person_id 単位（DESIGN.md）。

    突き合わせキーを (person_id, surface) にしたことで、removed 据え置きが surface 単位に
    縮んでいた。既存に removed 行が1本でもある person_id には、別 surface の候補（英字表記等）
    が来ても active で追加してはならない。
    """
    existing = [
        make_entry_row(2, status="removed", surface="K4SEN", reading="かせん", reading_source="self_profile")
    ]
    alt_surface_candidate = make_candidate(
        person_id="zeta-k4sen",
        surface="K4sen-EN",  # removed 行とは別の surface
        reading="かせん",
        reading_source="pr_manual",
    )
    result = promote_candidates(existing, [alt_surface_candidate])
    assert not result.added
    assert len(result.skipped_removed) == 1
    assert len(result.entries) == 1
    assert result.entries[0]["status"] == "removed"


def test_same_person_id_different_surface_is_added_not_conflict_or_unchanged():
    """entries.tsv は person_id+surface で一意（同一人物の別表記を別行で持てる）。

    2026-09-09 に発覚した既知課題: person_id だけで突き合わせると、同じ人物の新しい
    surface（英字表記など）が既存の別 surface の行と誤って比較され、reading が同じなら
    「変更なし」に握りつぶされ、reading が違えば無関係な「衝突」として弾かれていた。
    """
    existing = [make_entry_row(2)]  # zeta-k4sen / K4SEN / かせん
    alt_surface_candidate = make_candidate(
        person_id="zeta-k4sen",
        surface="K4sen-EN",  # 別表記（例: 英字表記のバリエーション）
        reading="かせん",
        reading_source="pr_manual",
    )
    result = promote_candidates(existing, [alt_surface_candidate])
    assert not result.conflicts
    assert not result.unchanged
    assert len(result.added) == 1
    assert result.entries[0]["surface"] == "K4SEN"
    assert result.entries[1]["surface"] == "K4sen-EN"
    assert result.entries[1]["person_id"] == "zeta-k4sen"


def test_same_person_id_same_surface_still_upgrades_not_added_twice():
    """回帰確認: surface まで一致するケースは従来どおり同一行として扱われる（新規追加にならない）。"""
    existing = [make_entry_row(2, reading_source="org_romaji")]
    same_surface_candidate = make_candidate(
        person_id="zeta-k4sen", surface="K4SEN", reading="かせん", reading_source="org_kana"
    )
    result = promote_candidates(existing, [same_surface_candidate])
    assert not result.added
    assert len(result.upgraded) == 1
    assert len(result.entries) == 1


def test_multiple_rows_preserve_existing_order_and_append_new_after():
    existing = [
        make_entry_row(2, person_id="a", reading="あ"),
        make_entry_row(3, person_id="b", reading="い"),
    ]
    candidate = make_candidate(person_id="c", reading="う")
    result = promote_candidates(existing, [candidate])
    assert [r["person_id"] for r in result.entries] == ["a", "b", "c"]
