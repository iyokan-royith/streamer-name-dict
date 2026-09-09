"""lib/validate.py の CLI（python -m lib.validate）のテスト。

build.py と検証ロジックは共通だが、CI の lint ジョブでは build（生成）まで走らせず
検証だけを単体で回したいので、CLI の出口（終了コード・標準出力/エラー）を確認する。
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "fixtures"


def run_validate(entries_path: Path, aliases_path: Path | None = None):
    cmd = [sys.executable, "-m", "lib.validate", str(entries_path)]
    if aliases_path is not None:
        cmd.append(str(aliases_path))
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)


def test_validate_cli_passes_on_real_data():
    """data/entries.tsv・data/aliases.tsv 自体が検証を通ることを確認する（回帰防止）。"""
    result = run_validate(ROOT / "data" / "entries.tsv", ROOT / "data" / "aliases.tsv")
    assert result.returncode == 0, result.stderr
    assert "検証OK" in result.stdout


def test_validate_cli_aliases_omitted_falls_back_to_sibling_file(tmp_path):
    """aliases 省略時、entries と同じディレクトリの aliases.tsv を拾う。"""
    entries = FIXTURES / "entries_valid.tsv"
    result = run_validate(entries)
    assert result.returncode == 0, result.stderr


def test_validate_cli_fails_nonzero_on_validation_errors():
    result = run_validate(FIXTURES / "entries_invalid.tsv")
    assert result.returncode != 0
    assert "検証エラー" in result.stderr


def test_validate_cli_fails_on_missing_entries_file(tmp_path):
    result = run_validate(tmp_path / "does-not-exist.tsv")
    assert result.returncode != 0
    assert "見つかりません" in result.stderr
