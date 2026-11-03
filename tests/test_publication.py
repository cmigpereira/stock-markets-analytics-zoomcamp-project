"""Publication guards recognize secrets without ever printing their values."""

import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publication_audit", ROOT / "scripts/audit_publication.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_recognizes_credentials_including_quoted_json_keys():
    tokens = ["ghp_" + "A" * 36, "AKIA" + "X" * 16, "rnd_" + "z" * 25]
    for token in tokens:
        assert audit.findings(token)
    payload = json.dumps({"api_key": "sample" + "credentialvalue"})
    assert any(label == "literal secret assignment" for label, _ in audit.findings(payload))


def test_recognizes_private_paths_and_email_without_echoing_them():
    path = "/" + "Users" + "/example/work"
    address = "person" + "@" + "mail.example"
    text = path + "\n" + address
    result = audit.findings(text)
    assert ("personal home path", 1) in result
    assert ("email address", 2) in result
    assert path not in repr(result)
    assert address not in repr(result)


def test_private_files_remain_excluded_from_git():
    paths = [
        ".env.production",
        ".streamlit/secrets.toml",
        ".aws/credentials",
        "config/service.key",
        "data/prices.parquet",
        "artifacts/model.joblib",
        "application.log",
    ]
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin"],
        cwd=ROOT,
        input="\n".join(paths),
        text=True,
        capture_output=True,
        check=True,
    )
    assert set(result.stdout.splitlines()) == set(paths)


def test_private_path_policy_does_not_block_presentation_report():
    assert audit.path_is_private(".streamlit/secrets.toml")
    assert audit.path_is_private("data/source.parquet")
    assert audit.path_is_private("config/service.pem")
    assert not audit.path_is_private("reports/dashboard.json")


def test_image_metadata_and_unknown_binaries_require_review():
    chunk = b"\x89PNG\r\n\x1a\n" + (0).to_bytes(4, "big") + b"eXIf" + b"0000"
    assert audit.inspect_bytes("image.png", chunk)
    assert audit.inspect_bytes("unknown.bin", b"\xff\xfe\x00")


def test_public_report_contains_no_secret_patterns():
    assert not audit.inspect_bytes("reports/dashboard.json", (ROOT / "reports/dashboard.json").read_bytes())
