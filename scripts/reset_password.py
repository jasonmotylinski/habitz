#!/usr/bin/env python3
"""
Reset a user's password in habitz.db.

Usage:
    python scripts/reset_password.py <email> [--db PATH]

The script will prompt for the new password interactively (not echoed).
"""

import argparse
import getpass
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path(__file__).parent.parent / "instance" / "habitz.db"


def main():
    parser = argparse.ArgumentParser(description="Reset a Habitz user password.")
    parser.add_argument("email", help="Email of the user whose password to reset")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to habitz.db")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        sys.exit(f"Database not found: {db_path}")

    # Lazy import so the script works without activating the venv for werkzeug,
    # as long as werkzeug is installed in the active Python environment.
    try:
        from werkzeug.security import generate_password_hash
    except ImportError:
        sys.exit("werkzeug is not installed. Run: pip install werkzeug")

    new_password = getpass.getpass("New password: ")
    confirm = getpass.getpass("Confirm password: ")
    if new_password != confirm:
        sys.exit("Passwords do not match.")
    if not new_password:
        sys.exit("Password cannot be empty.")

    password_hash = generate_password_hash(new_password)

    con = sqlite3.connect(db_path)
    try:
        cur = con.execute(
            "SELECT id, email FROM user WHERE email = ?", (args.email,)
        )
        row = cur.fetchone()
        if row is None:
            sys.exit(f"No user found with email: {args.email}")

        user_id, email = row
        con.execute(
            "UPDATE user SET password_hash = ? WHERE id = ?",
            (password_hash, user_id),
        )
        con.commit()
        print(f"Password reset for {email} (id={user_id}).")
    finally:
        con.close()


if __name__ == "__main__":
    main()
