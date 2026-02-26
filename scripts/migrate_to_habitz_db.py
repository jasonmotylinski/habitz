#!/usr/bin/env python3
"""
Migrate data from the individual per-app SQLite databases into a single habitz.db.

Usage:
    python scripts/migrate_to_habitz_db.py [--dry-run]
        [--meal-planner-db PATH]
        [--calorie-tracker-db PATH]
        [--fasting-tracker-db PATH]
        [--workout-tracker-db PATH]
        [--target-db PATH]

All path arguments are optional — defaults are the pre-consolidation locations
relative to this script. Pass only the ones that differ on your server.

Example (custom server layout):
    python scripts/migrate_to_habitz_db.py \\
        --meal-planner-db    /var/projects/meal-planner/instance/meal_planner.db \\
        --calorie-tracker-db /var/projects/calorie-tracker/instance/calorie_tracker.db \\
        --fasting-tracker-db /var/projects/fasting-tracker/instance/fasting_tracker.db \\
        --workout-tracker-db /var/projects/workout-tracker/instance/workout.db \\
        --target-db          /var/projects/habitz/instance/habitz.db

Notes:
- user_id=1 is assumed to be the same person across all apps.
- The unified 'user' table is a superset of all four user schemas.
- All other tables are copied as-is (user_id references remain unchanged
  since they already match across apps).
- Run ONCE on the production server before deploying the new unified app.
  Running again is safe — INSERT OR IGNORE is used for all rows.
"""
import argparse
import os
import sqlite3
import sys

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_script_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_script_dir)  # habitz/habitz/

SOURCE_DBS = {
    'meal_planner':    os.path.join(_root, 'instance', 'meal_planner.db'),
    'calorie_tracker': os.path.join(_root, 'calorie_tracker', 'instance', 'calorie_tracker.db'),
    'fasting_tracker': os.path.join(_root, 'fasting_tracker', 'instance', 'fasting_tracker.db'),
    'workout_tracker': os.path.join(_root, 'instance', 'workout.db'),
}

TARGET_DB = os.path.join(_root, 'instance', 'habitz.db')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def open_db(path):
    """Return a sqlite3 connection or None if the file doesn't exist."""
    if not os.path.exists(path):
        print(f"  [skip] not found: {path}")
        return None
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn, name):
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    )
    return cur.fetchone() is not None


def fetch_one_user(conn, user_id=1):
    """Return the user row as a dict, or None."""
    if not table_exists(conn, 'user') and not table_exists(conn, 'users'):
        return None
    tbl = 'user' if table_exists(conn, 'user') else 'users'
    cur = conn.execute(f"SELECT * FROM {tbl} WHERE id = ?", (user_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def columns_of(conn, table):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [row['name'] for row in cur.fetchall()]


def copy_table(src_conn, dst_conn, table, dry_run=False):
    """Copy all rows from src table into dst table using INSERT OR IGNORE."""
    if not table_exists(src_conn, table):
        print(f"    [skip] table '{table}' not in source")
        return 0

    src_cols = set(columns_of(src_conn, table))
    dst_cols = set(columns_of(dst_conn, table))
    common = [c for c in columns_of(src_conn, table) if c in dst_cols]

    if not common:
        print(f"    [skip] no matching columns for '{table}'")
        return 0

    rows = src_conn.execute(
        f"SELECT {', '.join(common)} FROM {table}"
    ).fetchall()

    if not rows:
        print(f"    [skip] '{table}' is empty")
        return 0

    placeholders = ', '.join('?' * len(common))
    sql = f"INSERT OR IGNORE INTO {table} ({', '.join(common)}) VALUES ({placeholders})"

    count = 0
    for row in rows:
        values = [row[c] for c in common]
        if not dry_run:
            dst_conn.execute(sql, values)
        count += 1

    print(f"    copied {count} row(s) into '{table}'")
    return count


# ---------------------------------------------------------------------------
# Schema bootstrap via Flask app
# ---------------------------------------------------------------------------

def create_schema(dry_run=False):
    """Use the unified Flask app to create habitz.db schema."""
    if dry_run:
        print("[dry-run] skipping schema creation")
        return

    sys.path.insert(0, _root)
    # Import the unified wsgi app — this triggers create_all() for all models
    print("  bootstrapping schema via Flask apps…")
    import wsgi  # noqa: F401 – side-effect: creates all tables in habitz.db
    print("  schema ready.")


# ---------------------------------------------------------------------------
# User merge
# ---------------------------------------------------------------------------

def merge_users(sources, dst_conn, dry_run=False):
    """
    Merge user rows from all source DBs into a single unified row in habitz.db.

    Strategy: start from any app that has a row for id=1, then overlay
    app-specific columns from the relevant source.
    """
    print("\n[users] merging…")

    # Gather data from each source
    meal    = sources.get('meal_planner')
    calorie = sources.get('calorie_tracker')
    fasting = sources.get('fasting_tracker')
    workout = sources.get('workout_tracker')

    u_meal    = fetch_one_user(meal)    if meal    else None
    u_calorie = fetch_one_user(calorie) if calorie else None
    u_fasting = fetch_one_user(fasting) if fasting else None
    u_workout = fetch_one_user(workout) if workout else None

    if not any([u_meal, u_calorie, u_fasting, u_workout]):
        print("  no user rows found in any source — skipping")
        return

    # Base fields (prefer meal_planner, then calorie, fasting, workout)
    base = u_meal or u_calorie or u_fasting or u_workout
    merged = {
        'id':            base.get('id', 1),
        'email':         base.get('email'),
        'username':      base.get('username'),
        'password_hash': base.get('password_hash'),
        'created_at':    base.get('created_at'),
        'household_id':  (u_meal or {}).get('household_id'),
        # calorie_tracker specific
        'daily_calorie_goal': (u_calorie or {}).get('daily_calorie_goal', 2000),
        'protein_goal_pct':   (u_calorie or {}).get('protein_goal_pct', 30),
        'carb_goal_pct':      (u_calorie or {}).get('carb_goal_pct', 40),
        'fat_goal_pct':       (u_calorie or {}).get('fat_goal_pct', 30),
        # fasting_tracker specific
        'default_fast_hours': (u_fasting or {}).get('default_fast_hours', 16),
    }

    # Override password_hash / email with whichever source has it (prefer workout
    # since it originally used bcrypt — password was migrated in Phase 5)
    if u_workout and u_workout.get('email') and not merged['email']:
        merged['email'] = u_workout['email']
    if u_workout and u_workout.get('password_hash') and not merged['password_hash']:
        merged['password_hash'] = u_workout['password_hash']

    dst_cols = columns_of(dst_conn, 'user')
    cols = [c for c in merged if c in dst_cols and merged[c] is not None]
    vals = [merged[c] for c in cols]

    sql = (
        f"INSERT OR IGNORE INTO user ({', '.join(cols)}) "
        f"VALUES ({', '.join('?' * len(cols))})"
    )

    print(f"  merged user: email={merged.get('email')!r}, username={merged.get('username')!r}")
    if not dry_run:
        dst_conn.execute(sql, vals)

    # If more than one user exists in any source, copy the rest verbatim
    for app_name, conn in [
        ('meal_planner', meal), ('calorie_tracker', calorie),
        ('fasting_tracker', fasting), ('workout_tracker', workout),
    ]:
        if conn is None:
            continue
        tbl = 'user' if table_exists(conn, 'user') else 'users'
        rows = conn.execute(f"SELECT * FROM {tbl} WHERE id != 1").fetchall()
        for row in rows:
            d = dict(row)
            cols2 = [c for c in d if c in dst_cols and d[c] is not None]
            vals2 = [d[c] for c in cols2]
            sql2 = (
                f"INSERT OR IGNORE INTO user ({', '.join(cols2)}) "
                f"VALUES ({', '.join('?' * len(cols2))})"
            )
            print(f"  [{app_name}] extra user id={d.get('id')}")
            if not dry_run:
                dst_conn.execute(sql2, vals2)


# ---------------------------------------------------------------------------
# Tables per app
# ---------------------------------------------------------------------------

# Non-user tables to migrate per app
APP_TABLES = {
    'meal_planner': [
        'household',
        'household_invite',
        'meal',
        'meal_favorites',
        'meal_plan',
        'shopping_list',
        'shopping_list_item',
        'api_key',
    ],
    'calorie_tracker': [
        'food_item',
        'usda_food',
        'food_log',
    ],
    'fasting_tracker': [
        'fast',
    ],
    'workout_tracker': [
        'exercises',
        'programs',
        'workouts',
        'workout_exercises',
        'program_workout_order',
        'workout_logs',
        'set_logs',
    ],
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Migrate per-app SQLite databases into a single habitz.db.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without writing anything')
    parser.add_argument('--meal-planner-db',    metavar='PATH',
                        default=SOURCE_DBS['meal_planner'],
                        help=f'meal_planner source DB (default: {SOURCE_DBS["meal_planner"]})')
    parser.add_argument('--calorie-tracker-db', metavar='PATH',
                        default=SOURCE_DBS['calorie_tracker'],
                        help=f'calorie_tracker source DB (default: {SOURCE_DBS["calorie_tracker"]})')
    parser.add_argument('--fasting-tracker-db', metavar='PATH',
                        default=SOURCE_DBS['fasting_tracker'],
                        help=f'fasting_tracker source DB (default: {SOURCE_DBS["fasting_tracker"]})')
    parser.add_argument('--workout-tracker-db', metavar='PATH',
                        default=SOURCE_DBS['workout_tracker'],
                        help=f'workout_tracker source DB (default: {SOURCE_DBS["workout_tracker"]})')
    parser.add_argument('--target-db', metavar='PATH',
                        default=TARGET_DB,
                        help=f'habitz.db destination (default: {TARGET_DB})')
    args = parser.parse_args()

    # Apply path overrides
    source_paths = {
        'meal_planner':    args.meal_planner_db,
        'calorie_tracker': args.calorie_tracker_db,
        'fasting_tracker': args.fasting_tracker_db,
        'workout_tracker': args.workout_tracker_db,
    }
    target_db = args.target_db

    dry_run = args.dry_run
    if dry_run:
        print("=== DRY RUN — no data will be written ===\n")

    # 1. Create schema
    print("=== Step 1: ensure habitz.db schema ===")
    create_schema(dry_run)

    # 2. Open connections
    print("\n=== Step 2: open source databases ===")
    sources = {}
    for app, path in source_paths.items():
        print(f"  {app}: {path}")
        conn = open_db(path)
        if conn:
            sources[app] = conn

    if not sources:
        print("\nNo source databases found — nothing to migrate.")
        return

    # 3. Open target
    if not dry_run:
        dst_conn = sqlite3.connect(target_db)
        dst_conn.row_factory = sqlite3.Row
        dst_conn.execute("PRAGMA foreign_keys = OFF")
    else:
        # Open target read-only for column introspection
        if not os.path.exists(target_db):
            print(f"\n[dry-run] target not found at {target_db}; schema bootstrap needed first.")
            return
        dst_conn = sqlite3.connect(target_db)
        dst_conn.row_factory = sqlite3.Row

    # 4. Merge users
    merge_users(sources, dst_conn, dry_run)

    # 5. Copy app-specific tables
    print("\n=== Step 3: copy app-specific tables ===")
    for app, tables in APP_TABLES.items():
        if app not in sources:
            continue
        src = sources[app]
        print(f"\n[{app}]")
        for tbl in tables:
            copy_table(src, dst_conn, tbl, dry_run)

    # 6. Commit and close
    if not dry_run:
        dst_conn.execute("PRAGMA foreign_keys = ON")
        dst_conn.commit()
        dst_conn.close()
        print(f"\nMigration complete. Data written to: {target_db}")
    else:
        dst_conn.close()
        print("\n[dry-run] complete — no data written.")

    for conn in sources.values():
        conn.close()


if __name__ == '__main__':
    main()
