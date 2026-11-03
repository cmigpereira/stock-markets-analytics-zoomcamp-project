"""Verify the hosted dashboard from a repository without ignored local data or network."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from etf_pressure.dashboard import LATEST_COLUMNS, load_report, source

ROOT = Path(__file__).resolve().parents[1]


def test_published_report_contains_only_presentation_fields():
    report = load_report(ROOT / "reports/dashboard.json")
    assert set(report["latest"].columns) == set(LATEST_COLUMNS)
    summary = report["summary"]
    assert summary["raw_rows"] >= summary["feature_rows"] >= summary["test_rows"] > 0
    assert len(report["models"]["experiments"]) == 6
    assert set(report["performance"].strategy) == set(report["curves"].strategy)
    assert report["curves"].date.notna().all()


def test_incomplete_local_outputs_fall_back_to_published_report(tmp_path):
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts/summary.json").write_text("{}")
    (tmp_path / "reports").mkdir()
    shutil.copy(ROOT / "reports/dashboard.json", tmp_path / "reports/dashboard.json")
    location, _ = source(tmp_path)
    assert location == tmp_path / "reports/dashboard.json"


def test_clean_checkout_renders_all_views_without_network(tmp_path):
    for name in ["src", "reports", ".streamlit"]:
        shutil.copytree(ROOT / name, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(ROOT / "app.py", tmp_path / "app.py")
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "artifacts").exists()
    code = """
import socket
def offline(*args, **kwargs):
    raise AssertionError("Dashboard startup must not need the network")
socket.socket.connect = offline
from streamlit.testing.v1 import AppTest
app = AppTest.from_file("app.py", default_timeout=60).run()
assert not app.exception, app.exception
assert any("PUBLISHED RESEARCH SNAPSHOT" in str(item.value) for item in app.caption)
for view in ["Signal explorer", "Model evidence", "Trade ledger", "Data & method"]:
    app.sidebar.radio[0].set_value(view).run()
    assert not app.exception, (view, app.exception)
print("All five cloud views render offline from a clean checkout")
"""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_report_is_strict_json():
    def reject(value):
        raise ValueError(value)

    json.loads((ROOT / "reports/dashboard.json").read_text(), parse_constant=reject)
