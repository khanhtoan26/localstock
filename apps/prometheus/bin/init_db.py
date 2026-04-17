#!/usr/bin/env python3
"""Initialize database schema with Alembic migrations.

Usage:
    uv run python apps/prometheus/bin/init_db.py
"""

import subprocess
import sys
from pathlib import Path

# Resolve apps/prometheus/ directory (parent of bin/)
PROMETHEUS_DIR = Path(__file__).resolve().parent.parent


def main() -> None:
    print("Initializing database schema...")
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        cwd=PROMETHEUS_DIR,
    )

    if result.returncode == 0:
        print("✅ Database schema initialized successfully!")
        if result.stdout:
            print(result.stdout)
    else:
        print("❌ Database initialization failed!")
        print(result.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
