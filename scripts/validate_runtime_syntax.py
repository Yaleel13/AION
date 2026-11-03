"""Parse runtime sources without importing them or writing bytecode."""

import ast
from pathlib import Path

root = Path(__file__).resolve().parent.parent
paths = sorted([*root.glob("aion/**/*.py"), *root.glob("api/**/*.py"), root / "run.py"])
for path in paths:
    ast.parse(path.read_bytes(), filename=str(path.relative_to(root)))
print(f"Runtime syntax valid: {len(paths)} Python files.")
