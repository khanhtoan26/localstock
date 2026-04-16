#!/usr/bin/env python3
"""Initialize database schema with Alembic migrations.

Usage:
    uv run python bin/init_db.py
"""

import subprocess
import sys


def main() -> None:
    print("Initializing database schema...")
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
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
