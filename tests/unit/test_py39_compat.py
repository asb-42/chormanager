"""Regression tests for Python 3.9 syntax compatibility (PEP 604 crash).

User report (2026-09-10, target machine with Python 3.9.5)::

    File ".../chormanager/config.py", line 289, in <module>
        _vg_color_theme: str | None = None
    TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'

Root cause: ``run.sh`` promises Python >= 3.9 support, but modules
without ``from __future__ import annotations`` used PEP 604 unions
(``str | None``). Function / module-level annotations ARE evaluated
at import time on 3.9, where ``type | None`` raises ``TypeError``.

Contract pinned by these tests (for every module in the
``chormanager`` package):

* Modules that do NOT have ``from __future__ import annotations``
  must not use ``X | Y`` unions in ANY evaluated annotation:
  function parameters, return annotations, and module-level /
  class-level variable annotations.
* Modules WITH the future import may use PEP 604 freely (their
  annotations are stored as strings and never evaluated).

The test is AST-based so it runs on any interpreter version and
catches the crash class without needing a real 3.9 runtime.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterator, List

import pytest

_PKG_ROOT = Path(__file__).parent.parent.parent / "chormanager"


def _iter_package_modules() -> Iterator[Path]:
    """Yield every ``.py`` file inside the chormanager package."""
    if not _PKG_ROOT.is_dir():
        pytest.skip("package root not found")
    for path in sorted(_PKG_ROOT.rglob("*.py")):
        yield path


def _has_future_annotations(tree: ast.Module) -> bool:
    """Return True if the module activates PEP 563 string annotations."""
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            if node.module == "__future__" and any(
                alias.name == "annotations" for alias in node.names
            ):
                return True
    return False


def _annotation_binops(node: ast.expr) -> List[ast.BinOp]:
    """Collect ``X | Y`` (BinOp BitOr) nodes inside an annotation expr."""
    found: List[ast.BinOp] = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.BitOr):
            found.append(sub)
    return found


def _evaluated_annotation_binops(tree: ast.Module) -> List[str]:
    """Collect PEP 604 unions in annotations that WOULD be evaluated.

    Covers function parameter + return annotations and variable
    annotations (AnnAssign). Local variable annotations inside
    function bodies are not evaluated at import time on CPython, so
    only module/class level AnnAssigns are checked.
    """
    offenders: List[str] = []

    def check_expr(expr: ast.expr, where: str) -> None:
        for _bin in _annotation_binops(expr):
            offenders.append(where)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in (
                [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
                + ([node.args.vararg] if node.args.vararg else [])
                + ([node.args.kwarg] if node.args.kwarg else [])
            ):
                if arg.annotation is not None:
                    check_expr(arg.annotation, f"{node.name}({arg.arg})")
            if node.returns is not None:
                check_expr(node.returns, f"{node.name} -> return")
        elif isinstance(node, ast.AnnAssign):
            # Module/class level only: parents are Module/ClassDef
            # (approximated via col_offset == 0 for module level).
            if node.annotation is not None:
                check_expr(
                    node.annotation,
                    f"variable at line {node.lineno}",
                )

    return offenders


def test_all_modules_py39_annotation_compatible():
    """No evaluated PEP 604 unions in modules without the future import.

    This is the regression test for the 3.9.5 startup crash: any
    offender listed here would raise ``TypeError: unsupported
    operand type(s) for |`` the moment the module is imported on
    Python 3.9.
    """
    offenders: List[str] = []
    for path in _iter_package_modules():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:  # pragma: no cover
            offenders.append(f"{path.relative_to(path.parents[1])}: {exc}")
            continue
        if _has_future_annotations(tree):
            continue
        for where in _evaluated_annotation_binops(tree):
            rel = path.relative_to(path.parents[1])
            offenders.append(f"{rel}: {where} uses X | Y without future import")

    assert offenders == [], (
        "Python 3.9 incompatible PEP 604 annotations found "
        "(evaluated at import time without PEP 563):\n  "
        + "\n  ".join(offenders)
    )
