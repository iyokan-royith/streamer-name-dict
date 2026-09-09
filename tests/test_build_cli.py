import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "fixtures"


def run_build(data_path: Path, out_dir: Path, aliases_path: Path | None = None):
    cmd = [sys.executable, str(ROOT / "build.py"), "--data", str(data_path), "--out-dir", str(out_dir)]
    if aliases_path is not None:
        cmd += ["--aliases", str(aliases_path)]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def test_build_generates_four_formats(tmp_path):
    out_dir = tmp_path / "dist"
    result = run_build(FIXTURES / "entries_valid.tsv", out_dir)
    assert result.returncode == 0, result.stderr
    for filename in ["streamer_dict_msime.txt", "streamer_dict_google_mozc.txt", "streamer_dict_atok.txt", "streamer_dict_skk.txt"]:
        assert (out_dir / filename).exists()


def test_build_excludes_removed_status(tmp_path):
    out_dir = tmp_path / "dist"
    result = run_build(FIXTURES / "entries_with_removed.tsv", out_dir)
    assert result.returncode == 0, result.stderr

    google_text = (out_dir / "streamer_dict_google_mozc.txt").read_text(encoding="utf-8")
    assert "K4SEN" in google_text
    assert "引退太郎" not in google_text

    skk_text = (out_dir / "streamer_dict_skk.txt").read_text(encoding="utf-8")
    assert "K4SEN" in skk_text
    assert "引退太郎" not in skk_text


def test_build_fails_nonzero_on_validation_errors(tmp_path):
    out_dir = tmp_path / "dist"
    result = run_build(FIXTURES / "entries_invalid.tsv", out_dir)
    assert result.returncode != 0
    assert "検証エラー" in result.stderr
    # 検証に失敗したら dist は作られない（中途半端な生成物を残さない）
    assert not out_dir.exists() or list(out_dir.iterdir()) == []


def test_build_on_real_data_passes(tmp_path):
    """data/entries.tsv 自体が検証を通り、4形式が生成できることを確認する（回帰防止）。"""
    out_dir = tmp_path / "dist"
    result = run_build(ROOT / "data" / "entries.tsv", out_dir)
    assert result.returncode == 0, result.stderr
    assert (out_dir / "streamer_dict_msime.txt").exists()


def test_build_with_no_aliases_file_is_zero_alias(tmp_path):
    """--aliases 省略時、entries.tsv と同じディレクトリに aliases.tsv が無ければ 0 件扱いになる。"""
    out_dir = tmp_path / "dist"
    result = run_build(FIXTURES / "entries_valid.tsv", out_dir)
    assert result.returncode == 0, result.stderr
    assert "別名 0" in result.stdout


def test_build_merges_aliases_into_all_formats(tmp_path):
    out_dir = tmp_path / "dist"
    result = run_build(FIXTURES / "entries_valid.tsv", out_dir, FIXTURES / "aliases_valid.tsv")
    assert result.returncode == 0, result.stderr
    assert "収録 4 件（正式 2・別名 2）" in result.stdout

    google_text = (out_dir / "streamer_dict_google_mozc.txt").read_text(encoding="utf-8")
    assert "ケイフォー" in google_text
    assert "けいふぉー" in google_text

    skk_text = (out_dir / "streamer_dict_skk.txt").read_text(encoding="utf-8")
    assert "ケイフォー" in skk_text

    ms_ime_text = (out_dir / "streamer_dict_msime.txt").read_bytes().decode("utf-16")
    assert "ケイフォー" in ms_ime_text

    atok_text = (out_dir / "streamer_dict_atok.txt").read_bytes().decode("utf-16")
    assert "ケイフォー" in atok_text


def test_build_excludes_alias_of_removed_person(tmp_path):
    """entries 側で status=removed になった person_id の alias は build から連動除外される。"""
    out_dir = tmp_path / "dist"
    result = run_build(
        FIXTURES / "entries_with_removed.tsv",
        out_dir,
        FIXTURES / "aliases_for_removed_test.tsv",
    )
    assert result.returncode == 0, result.stderr
    assert "収録 2 件（正式 1・別名 1）" in result.stdout

    google_text = (out_dir / "streamer_dict_google_mozc.txt").read_text(encoding="utf-8")
    assert "ケイフォー" in google_text
    assert "いんたい" not in google_text


def test_build_fails_on_alias_validation_error(tmp_path):
    out_dir = tmp_path / "dist"
    result = run_build(FIXTURES / "entries_valid.tsv", out_dir, FIXTURES / "aliases_invalid.tsv")
    assert result.returncode != 0
    assert "検証エラー" in result.stderr
