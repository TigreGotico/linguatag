"""The docs say what the code does: each example prints its ``# `` comment,
each link resolves, and each figure equals a fresh one."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["README.md", *sorted(str(p.relative_to(ROOT)) for p in (ROOT / "docs").glob("*.md"))]


@pytest.mark.parametrize("page", PAGES)
def test_a_docs_page_matches_the_code(page):
    result = subprocess.run([sys.executable, "scripts/check_doc_page.py", page],
                            capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_figures_are_fresh():
    result = subprocess.run([sys.executable, "scripts/docs_figures.py", "--check"],
                            capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
