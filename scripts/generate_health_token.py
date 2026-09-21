#!/usr/bin/env python3
"""
Generate (or regenerate) an Apple Health export token for a user.

Usage:
    python scripts/generate_health_token.py <email> [--db PATH]

Prints the new Bearer token. Configure the iOS Shortcut to send it as:
    Authorization: Bearer <token>

Running the script again invalidates the previous token.
"""

import argparse
import secrets
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path(__file__).parent.parent / "instance" / "habitz.db"


def main():
    parser = argparse.ArgumentParser(description="Generate an Apple Health export token.")
    parser.add_argument("email", help="Email of the user to generate a token for")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to habitz.db")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        sys.exit(f"Database not found: {db_path}")

    token = secrets.token_urlsafe(24)

    con = sqlite3.connect(db_path)
    try:
        cur = con.execute(
            "SELECT id, email FROM user WHERE lower(email) = lower(?)", (args.email,)
        )
        row = cur.fetchone()
        if row is None:
            sys.exit(f"No user found with email: {args.email}")

        user_id, email = row
        con.execute(
            "UPDATE user SET apple_health_token = ? WHERE id = ?",
            (token, user_id),
        )
        con.commit()
        print(f"Apple Health token for {email} (id={user_id}):")
        print(token)
    finally:
        con.close()


if __name__ == "__main__":
    main()
