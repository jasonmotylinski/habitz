#!/usr/bin/env python3
"""
Seed basic everyday foods that are missing from the usda_food table.

These are raw/simple foods (eggs, plain meats, basic dairy, etc.) whose
USDA SR Legacy nutrient values are public domain. All values are per 100g;
serving_weight_g sets what one "serving" weighs.

Usage:
    python scripts/seed_basic_foods.py [--db PATH] [--dry-run]
"""

import argparse
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path(__file__).parent.parent / "instance" / "habitz.db"

# fmt: off
# All nutrient values sourced from USDA FoodData Central SR Legacy release.
# Calories = kcal per 100g; other macros in g per 100g.
BASIC_FOODS = [
    # --- Eggs ---
    dict(
        food_id="sr_egg_whole_raw",
        name="Egg, Whole, Raw",
        food_type="everyday",
        calories=143.0, protein_g=12.56, carbs_g=0.72, fat_g=9.51, fiber_g=None,
        serving_description="1 large egg", serving_weight_g=50.0,
        alternate_names="egg raw egg whole eggs",
    ),
    dict(
        food_id="sr_egg_whole_fried",
        name="Egg, Whole, Fried",
        food_type="everyday",
        calories=196.0, protein_g=13.6, carbs_g=0.83, fat_g=14.8, fiber_g=None,
        serving_description="1 large egg", serving_weight_g=46.0,
        alternate_names="fried egg egg fried",
    ),
    dict(
        food_id="sr_egg_whole_scrambled",
        name="Egg, Whole, Scrambled",
        food_type="everyday",
        calories=149.0, protein_g=9.99, carbs_g=1.6, fat_g=11.0, fiber_g=None,
        serving_description="1 large egg", serving_weight_g=61.0,
        alternate_names="scrambled egg egg scrambled",
    ),
    dict(
        food_id="sr_egg_whole_boiled",
        name="Egg, Whole, Hard-Boiled",
        food_type="everyday",
        calories=155.0, protein_g=12.6, carbs_g=1.12, fat_g=10.6, fiber_g=None,
        serving_description="1 large egg", serving_weight_g=50.0,
        alternate_names="boiled egg hard boiled egg egg boiled",
    ),
    dict(
        food_id="sr_egg_whole_poached",
        name="Egg, Whole, Poached",
        food_type="everyday",
        calories=143.0, protein_g=12.5, carbs_g=0.72, fat_g=9.47, fiber_g=None,
        serving_description="1 large egg", serving_weight_g=50.0,
        alternate_names="poached egg egg poached",
    ),
    dict(
        food_id="sr_egg_white_raw",
        name="Egg White, Raw",
        food_type="everyday",
        calories=52.0, protein_g=10.9, carbs_g=0.73, fat_g=0.17, fiber_g=None,
        serving_description="1 large egg white", serving_weight_g=33.0,
        alternate_names="egg white raw egg whites",
    ),
    dict(
        food_id="sr_egg_yolk_raw",
        name="Egg Yolk, Raw",
        food_type="everyday",
        calories=322.0, protein_g=15.9, carbs_g=3.59, fat_g=26.5, fiber_g=None,
        serving_description="1 large egg yolk", serving_weight_g=17.0,
        alternate_names="egg yolk raw yolk",
    ),
]
# fmt: on


def seed(db_path: Path, dry_run: bool = False) -> None:
    con = sqlite3.connect(db_path)
    try:
        inserted = 0
        skipped = 0
        for food in BASIC_FOODS:
            existing = con.execute(
                "SELECT food_id FROM usda_food WHERE food_id = ?", (food["food_id"],)
            ).fetchone()
            if existing:
                skipped += 1
                continue

            if not dry_run:
                con.execute(
                    """
                    INSERT INTO usda_food
                        (food_id, name, food_type, alternate_names, barcode,
                         calories, protein_g, carbs_g, fat_g, fiber_g,
                         serving_description, serving_weight_g)
                    VALUES
                        (:food_id, :name, :food_type, :alternate_names, NULL,
                         :calories, :protein_g, :carbs_g, :fat_g, :fiber_g,
                         :serving_description, :serving_weight_g)
                    """,
                    food,
                )
            inserted += 1
            print(f"  {'[dry-run] ' if dry_run else ''}insert: {food['name']}")

        if not dry_run:
            con.commit()

        print(f"\n{inserted} inserted, {skipped} already present.")
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(description="Seed basic everyday foods into habitz.db.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to habitz.db")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be inserted without writing")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        sys.exit(f"Database not found: {db_path}")

    print(f"Seeding basic foods into {db_path}" + (" (dry run)" if args.dry_run else "") + "...")
    seed(db_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
