"""Create a source-and-evidence ZIP using an explicit allowlist; never include .env."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "WorkflowDNA-submission.zip"
FOLDERS = ("backend", "training", "data", "artifacts", "docs", "scripts", "tests", "frontend/app", "frontend/components", "frontend/lib", "frontend/tests", "frontend/e2e")
FILES = ("README.md", ".gitignore", ".env.example", "requirements.txt", "requirements.lock.txt", "frontend/package.json", "frontend/package-lock.json", "frontend/next.config.ts", "frontend/tsconfig.json", "frontend/playwright.config.ts")
EXCLUDED = {"__pycache__", ".pytest_cache", "node_modules", ".next", "test-results", "playwright-report"}

def package() -> Path:
    paths = {ROOT / name for name in FILES if (ROOT / name).is_file()}
    for folder in FOLDERS:
        paths.update(p for p in (ROOT / folder).rglob("*") if p.is_file() and not EXCLUDED.intersection(p.parts) and not p.name.startswith(".env") and p.suffix not in {".pyc", ".log", ".tmp"})
    with ZipFile(DESTINATION, "w", ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            archive.write(path, Path("WorkflowDNA") / path.relative_to(ROOT))
    with ZipFile(DESTINATION) as archive:
        assert not any(Path(name).name == ".env" or "node_modules" in Path(name).parts for name in archive.namelist())
    print(f"Saved {DESTINATION.name}: {len(paths)} files, {DESTINATION.stat().st_size:,} bytes; credentials excluded.")
    return DESTINATION

if __name__ == "__main__":
    package()
