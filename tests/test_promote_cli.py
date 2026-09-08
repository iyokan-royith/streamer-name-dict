"""promote.py CLI の end-to-end テスト（実ファイル I/O・subprocess 経由）。"""
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

ENTRIES_HEADER = "person_id\tsurface\treading\treading_source\tsource_url\torg\torg_source_url\tstatus\tadded\tnote\n"

CANDIDATE_HEADER = (
    "person_id\tsurface\treading\treading_source\tsource_url\torg\torg_source_url\t"
    "status\tadded\tnote\treading_candidate\tneeds_review\tromaji\n"
)


def run_promote(entries_path: Path, candidate_paths: list[Path], extra_args: list[str] | None = None):
    args = [sys.executable, str(ROOT / "promote.py")]
    args += [str(p) for p in candidate_paths]
    args += ["--entries", str(entries_path)]
    args += extra_args or []
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True)


def write_tsv(path: Path, header: str, rows: list[str]) -> None:
    path.write_text(header + "".join(row + "\n" for row in rows), encoding="utf-8")


def read_entries(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def test_promote_adds_new_and_upgrades_existing(tmp_path):
    entries_path = tmp_path / "entries.tsv"
    write_tsv(
        entries_path,
        ENTRIES_HEADER,
        [
            "zeta-k4sen\tK4SEN\tかせん\torg_romaji\thttps://old\tZETA DIVISION\thttps://old-org\tactive\t2026-09-01\t旧note",
        ],
    )

    candidates_path = tmp_path / "candidates.tsv"
    write_tsv(
        candidates_path,
        CANDIDATE_HEADER,
        [
            # 既存と同じ reading・より高信頼度の source → 昇格
            "zeta-k4sen\tK4SEN\tかせん\torg_kana\thttps://new\tZETA DIVISION\thttps://new-org\tactive\t2026-09-08\t新note\tかせん\tno\tK4sen",
            # 新規人物 → 追加
            "new-org-newperson\t新人\tしんじん\torg_kana\thttps://new-person\tテスト事務所\thttps://test-org\tactive\t2026-09-08\t\tしんじん\tno\tShinjin",
            # needs_review=yes → スキップ
            "new-org-review\t要確認\t\torg_romaji\thttps://review\tテスト事務所\thttps://test-org\tactive\t2026-09-08\t\tようかくにん\tyes\tYoukakunin",
        ],
    )

    result = run_promote(entries_path, [candidates_path])
    assert result.returncode == 0, result.stderr

    rows = read_entries(entries_path)
    assert len(rows) == 2

    k4sen = next(r for r in rows if r["person_id"] == "zeta-k4sen")
    assert k4sen["reading_source"] == "org_kana"
    assert k4sen["source_url"] == "https://new"
    assert k4sen["note"] == "新note"
    # 据え置きの列
    assert k4sen["added"] == "2026-09-01"
    assert k4sen["org"] == "ZETA DIVISION"

    newperson = next(r for r in rows if r["person_id"] == "new-org-newperson")
    assert newperson["reading"] == "しんじん"

    assert "追加: 1 件" in result.stdout
    assert "信頼度昇格: 1 件" in result.stdout
    assert "スキップ（要確認）: 1 件" in result.stdout


def test_promote_conflict_blocks_write_and_exits_nonzero(tmp_path):
    entries_path = tmp_path / "entries.tsv"
    write_tsv(
        entries_path,
        ENTRIES_HEADER,
        [
            "zeta-k4sen\tK4SEN\tかせん\torg_kana\thttps://old\tZETA DIVISION\thttps://old-org\tactive\t2026-09-01\t",
        ],
    )
    original_text = entries_path.read_text(encoding="utf-8")

    candidates_path = tmp_path / "candidates.tsv"
    write_tsv(
        candidates_path,
        CANDIDATE_HEADER,
        [
            "zeta-k4sen\tK4SEN\tべつのよみ\torg_kana\thttps://new\tZETA DIVISION\thttps://new-org\tactive\t2026-09-08\t\tべつのよみ\tno\tBetsu",
        ],
    )

    result = run_promote(entries_path, [candidates_path])
    assert result.returncode != 0
    assert "衝突" in result.stderr
    # 書き込まれていない（ファイルは変化しない）
    assert entries_path.read_text(encoding="utf-8") == original_text


def test_promote_removed_status_is_not_reactivated(tmp_path):
    entries_path = tmp_path / "entries.tsv"
    write_tsv(
        entries_path,
        ENTRIES_HEADER,
        [
            "zeta-k4sen\tK4SEN\tかせん\tself_profile\thttps://old\tZETA DIVISION\thttps://old-org\tremoved\t2026-09-01\t削除申請済み",
        ],
    )

    candidates_path = tmp_path / "candidates.tsv"
    write_tsv(
        candidates_path,
        CANDIDATE_HEADER,
        [
            "zeta-k4sen\tK4SEN\tかせん\torg_kana\thttps://new\tZETA DIVISION\thttps://new-org\tactive\t2026-09-08\t\tかせん\tno\tK4sen",
        ],
    )

    result = run_promote(entries_path, [candidates_path])
    assert result.returncode == 0, result.stderr

    rows = read_entries(entries_path)
    assert len(rows) == 1
    assert rows[0]["status"] == "removed"
    assert rows[0]["reading_source"] == "self_profile"
    assert "スキップ（removed のため据え置き）: 1 件" in result.stdout


def test_promote_dry_run_does_not_write(tmp_path):
    entries_path = tmp_path / "entries.tsv"
    write_tsv(entries_path, ENTRIES_HEADER, [])
    original_text = entries_path.read_text(encoding="utf-8")

    candidates_path = tmp_path / "candidates.tsv"
    write_tsv(
        candidates_path,
        CANDIDATE_HEADER,
        [
            "new-org-newperson\t新人\tしんじん\torg_kana\thttps://new-person\tテスト事務所\thttps://test-org\tactive\t2026-09-08\t\tしんじん\tno\tShinjin",
        ],
    )

    result = run_promote(entries_path, [candidates_path], extra_args=["--dry-run"])
    assert result.returncode == 0, result.stderr
    assert "追加: 1 件" in result.stdout
    assert "--dry-run のため書き込みは行いません" in result.stdout
    assert entries_path.read_text(encoding="utf-8") == original_text


def test_promote_dry_run_also_validates_and_blocks_on_error(tmp_path):
    """--dry-run でも validate を通す（台帳 A149）。カタカナ混じりの reading は検証エラーになる。"""
    entries_path = tmp_path / "entries.tsv"
    write_tsv(entries_path, ENTRIES_HEADER, [])
    original_text = entries_path.read_text(encoding="utf-8")

    candidates_path = tmp_path / "candidates.tsv"
    write_tsv(
        candidates_path,
        CANDIDATE_HEADER,
        [
            # reading がカタカナ混じり → validate でエラーになるはず
            "new-org-newperson\t新人\tシンジン\torg_kana\thttps://new-person\tテスト事務所\thttps://test-org\tactive\t2026-09-08\t\tシンジン\tno\tShinjin",
        ],
    )

    result = run_promote(entries_path, [candidates_path], extra_args=["--dry-run"])
    assert result.returncode != 0
    assert "検証エラー" in result.stderr
    # --dry-run でも書き込みが起きないことは従来どおり保たれる
    assert entries_path.read_text(encoding="utf-8") == original_text


def test_promote_does_not_write_when_validation_fails(tmp_path):
    """validate 失敗時（dry-run 無し）は entries.tsv を書き換えずに非ゼロ終了する（台帳 A149）。"""
    entries_path = tmp_path / "entries.tsv"
    write_tsv(entries_path, ENTRIES_HEADER, [])
    original_text = entries_path.read_text(encoding="utf-8")

    candidates_path = tmp_path / "candidates.tsv"
    write_tsv(
        candidates_path,
        CANDIDATE_HEADER,
        [
            "new-org-newperson\t新人\tシンジン\torg_kana\thttps://new-person\tテスト事務所\thttps://test-org\tactive\t2026-09-08\t\tシンジン\tno\tShinjin",
        ],
    )

    result = run_promote(entries_path, [candidates_path])
    assert result.returncode != 0
    assert "検証エラー" in result.stderr
    assert entries_path.read_text(encoding="utf-8") == original_text


def test_promote_write_preserves_existing_file_permissions(tmp_path):
    """アトミック書き込み後、entries.tsv のパーミッションは元のまま（台帳 A151）。

    tempfile.mkstemp は 0600 で一時ファイルを作るため、既存ファイルのモードを引き継がないと
    644 等だった entries.tsv が os.replace の後 600 に化けてしまう。
    """
    entries_path = tmp_path / "entries.tsv"
    write_tsv(entries_path, ENTRIES_HEADER, [])
    entries_path.chmod(0o644)

    candidates_path = tmp_path / "candidates.tsv"
    write_tsv(
        candidates_path,
        CANDIDATE_HEADER,
        [
            "new-org-newperson\t新人\tしんじん\torg_kana\thttps://new-person\tテスト事務所\thttps://test-org\tactive\t2026-09-08\t\tしんじん\tno\tShinjin",
        ],
    )

    result = run_promote(entries_path, [candidates_path])
    assert result.returncode == 0, result.stderr

    mode = entries_path.stat().st_mode & 0o777
    assert mode == 0o644
