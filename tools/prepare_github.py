from pathlib import Path
import json
import re
import shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", ".venv", "node_modules", "test-results", "__pycache__", ".vscode", ".idea", "github-export"}
SUFFIXES = {".pyc", ".db", ".sqlite", ".sqlite3", ".log", ".zip", ".7z", ".pem", ".key", ".p12", ".pfx", ".bak"}


def main():
    selected, findings = [], []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if any(part in SKIP for part in rel.parts) or not path.is_file():
            continue
        if rel.parts[0] == "data" and str(rel).replace("\\", "/") not in {"data/erd.mmd", "data/erd.html"}:
            continue
        if (path.name == ".env" or path.name.startswith(".env.")) and path.name != ".env.example":
            continue
        if path.suffix.lower() in SUFFIXES or path.name.endswith(("-wal", "-shm")) or path.name in {".DS_Store", "Thumbs.db", "Desktop.ini"}:
            continue
        if path.stat().st_size > 50 * 1024 * 1024:
            findings.append(str(rel) + ": file larger than project export threshold (50 MB)")
        if path.suffix.lower() in {".py", ".js", ".json", ".md", ".txt", ".yml", ".example"}:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            if re.search(r"AIza[0-9A-Za-z_-]{35}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}", text):
                findings.append(str(rel) + ": possible credential; inspect locally")
        selected.append(path)
    if findings:
        raise SystemExit("Export stopped:\n" + "\n".join(findings))
    destination = ROOT / "github-export" / datetime.now().strftime("neu-shop-%Y%m%d-%H%M%S")
    destination.mkdir(parents=True, exist_ok=False)
    total = 0
    for path in selected:
        target = destination / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        total += path.stat().st_size
    (destination / "GITHUB_EXPORT_REPORT.json").write_text(json.dumps({"files": len(selected), "bytes": total, "secret_scan": "No matches for supported patterns; manual review still required", "excluded": sorted(SKIP), "runtime_data": "excluded except ERD"}, indent=2), encoding="utf-8")
    print(f"Prepared {len(selected)} files ({total / 1024 / 1024:.1f} MB): {destination.relative_to(ROOT)}")
    print("No nested Git metadata, runtime databases, .env secrets or installed dependencies were copied.")


if __name__ == "__main__":
    main()
