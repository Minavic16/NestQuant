"""Architecture boundary: NQTS must not depend on Studio or research code.

NQTS runs validated strategies. Experiments, research engines and Studio live in
`studio/`. Studio may read NQTS (indicators, contracts); NQTS must never import
Studio. This test fails the build if that rule is broken.
"""
import ast
from pathlib import Path

PKG = Path(__file__).resolve().parents[2] / "nestquant"
FORBIDDEN = ("nestquant_studio", "nestquant.research", "research.experiments")


def _imports(path: Path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield node.lineno, a.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.lineno, node.module


def test_nqts_never_imports_studio_or_research():
    offenders = [
        f"{p.relative_to(PKG.parent)}:{ln} imports {mod}"
        for p in PKG.rglob("*.py")
        for ln, mod in _imports(p)
        if mod.startswith(FORBIDDEN)
    ]
    assert not offenders, "NQTS depends on research/Studio code:\n" + "\n".join(offenders)


def test_no_experiments_directory_inside_nqts():
    assert not (PKG / "research").exists(), "research/ must live in studio/, not NQTS"
    assert not list(PKG.rglob("experiments")), "no experiments inside NQTS"
