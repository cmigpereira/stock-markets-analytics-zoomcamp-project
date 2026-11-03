"""Scan intended publication files and reachable Git blobs without printing secret values.

This is a deterministic guard for common leaks, not a proof that arbitrary private
information can be recognized. Public research hashes and synthetic trades are expected.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    "private key": r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----",
    "AWS access identifier": r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "GitHub credential": r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b",
    "Google API credential": r"\bAIza[A-Za-z0-9_-]{30,}\b",
    "Slack credential": r"\bxox[baprs]-[A-Za-z0-9-]{15,}\b",
    "OpenAI credential": r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}\b",
    "Render credential": r"\brnd_[A-Za-z0-9]{20,}\b",
    "Hugging Face credential": r"\bhf_[A-Za-z0-9]{25,}\b",
    "Stripe live credential": r"\b[rs]k_live_[A-Za-z0-9]{20,}\b",
    "credential in URL": r"https?://[^\s/\"'<>:@]+:[^\s/\"'<>@]+@",
    "literal secret assignment": r"(?i)(?:api_key|api_token|access_token|client_secret|password|secret_key)[\"']?\s*[:=]\s*[\"'][A-Za-z0-9_+/=.-]{12,}[\"']",
    "bearer credential": r"(?i)\bBearer\s+[A-Za-z0-9_.-]{20,}",
    "personal home path": r"/(?:Users|home)/[A-Za-z0-9_.-]+/",
    "Windows home path": r"[A-Za-z]:\\Users\\[A-Za-z0-9_. -]+\\",
    "email address": r"\b[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
}
COMPILED = {name: re.compile(pattern) for name, pattern in RULES.items()}
PUBLIC_EMAILS = {"noreply@github.com"}  # GitHub's public commit-signing bot, not a personal address.
PRIVATE_PARTS = {".aws", ".ssh", ".codex", ".agents", "data", "artifacts", ".venv"}
PRIVATE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".parquet", ".joblib", ".pkl", ".pickle", ".db"}


def findings(text):
    """Return labels and line numbers only; never echo matched credentials."""
    result = []
    for label, pattern in COMPILED.items():
        for match in pattern.finditer(text):
            if label == "email address" and match.group(0) in PUBLIC_EMAILS:
                continue
            result.append((label, text.count("\n", 0, match.start()) + 1))
    return result


def path_is_private(path):
    p = Path(path)
    return (
        bool(set(p.parts) & PRIVATE_PARTS)
        or p.name.startswith(".env")
        and p.name != ".env.example"
        or p.name == "secrets.toml"
        or p.suffix.lower() in PRIVATE_SUFFIXES
        or p.name.startswith(("id_rsa", "id_ed25519"))
    )


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def inspect_bytes(name, content):
    if content.startswith(b"\x89PNG"):
        # Parse PNG ancillary text chunks without dependencies or exposing their contents.
        import struct

        offset = 8
        while offset + 12 <= len(content):
            length = struct.unpack(">I", content[offset : offset + 4])[0]
            kind = content[offset + 4 : offset + 8]
            if kind in {b"tEXt", b"iTXt", b"zTXt", b"eXIf"}:
                return [(name, "image text/EXIF metadata requires review", 0)]
            offset += length + 12
        return []
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return [(name, "unexpected binary requires review", 0)]
    return [(name, label, line) for label, line in findings(text)]


def main():
    parser = argparse.ArgumentParser(description="Audit files and the history of the branch being published")
    parser.add_argument("--ref", default="HEAD", help="Commit or branch to publish (default: HEAD)")
    args = parser.parse_args()
    revision = git("rev-parse", "--verify", "--end-of-options", args.ref + "^{commit}").decode().strip()
    issues = []
    paths = set(git("ls-files", "--cached", "--others", "--exclude-standard", "-z").decode().split("\0")) - {
        ""
    }
    for path in sorted(paths):
        if path_is_private(path):
            issues.append((path, "private/source-data file in publication set", 0))
        location = ROOT / path
        if location.is_symlink():
            issues.append((path, "symlink requires review", 0))
        elif location.is_file():
            issues.extend(inspect_bytes(path, location.read_bytes()))
    objects = git("rev-list", "--objects", revision).decode().splitlines()
    blobs = 0
    for item in objects:
        oid, _, path = item.partition(" ")
        if git("cat-file", "-t", oid).strip() == b"blob":
            blobs += 1
            label = f"history:{oid[:8]}:{path}"
            if path_is_private(path):
                issues.append((label, "private/source-data file in history", 0))
            issues.extend(inspect_bytes(label, git("cat-file", "blob", oid)))
    # Commit identity is intentionally public; require GitHub's privacy-preserving address.
    emails = git("log", revision, "--format=%ae%n%ce").decode().splitlines()
    current = subprocess.run(
        ["git", "config", "user.email"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    if any(
        not email.endswith("@users.noreply.github.com") and email != "noreply@github.com" for email in emails
    ):
        issues.append(
            ("Git history", "personal author/committer email requires history cleanup before publication", 0)
        )
    if current and not current.endswith("@users.noreply.github.com"):
        issues.append(("Git identity", "future commits need a GitHub noreply address", 0))
    print(
        json.dumps(
            {
                "publication_files_checked": len(paths),
                "historical_blobs_checked": blobs,
                "findings": [{"file": p, "rule": rule, "line": line} for p, rule, line in issues],
            },
            indent=2,
        )
    )
    return bool(issues)


if __name__ == "__main__":
    sys.exit(main())
