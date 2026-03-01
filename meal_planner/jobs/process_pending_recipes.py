#!/usr/bin/env python3
"""
Cron job: Process pending recipe imports using Claude API

Usage: python jobs/process_pending_recipes.py
Add to crontab: */5 * * * * cd /path/to/meal-planner && python jobs/process_pending_recipes.py

This script:
1. Finds all MealPlan entries with import_status='pending'
2. Calls Claude API to extract recipe data from source_url
3. Creates Meal record with extracted data
4. Updates MealPlan with imported_meal_id and status='imported'
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/meal_planner_import.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add parent directory to path so we can import app
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from app import create_app
    from app.models import db, MealPlan, Meal, User
    from app.recipe_importer import import_recipe_from_url, extract_domain_name
    from anthropic import Anthropic
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)


def extract_recipe_with_claude(html, url, api_key):
    """
    Use Claude to extract recipe data from HTML

    Returns dict with: name, ingredients, instructions, description, servings, prep_time, cook_time
    Returns None if extraction fails
    """
    try:
        client = Anthropic(api_key=api_key)

        # Extract recipe-relevant portion of HTML for Claude
        # Look for common recipe markers first, then limit to reasonable size
        recipe_start = 0

        # Try to find recipe section markers (lower case for matching)
        html_lower = html.lower()
        markers = [
            r'<article',
            r'<div class=["\']recipe',
            r'<div class=["\']post-content',
            r'<main',
            r'<div id=["\']recipe',
        ]

        import re as regex
        for marker in markers:
            match = regex.search(marker, html_lower)
            if match:
                recipe_start = max(0, match.start() - 500)  # Back up 500 chars for context
                break

        # Include up to 60000 chars from recipe start (to capture ingredients AND instructions)
        html_excerpt = html[recipe_start:recipe_start + 60000]

        prompt = f"""Extract recipe data from this HTML and return ONLY valid JSON (no markdown, no extra text).

EXTRACTION RULES:
- name: Recipe title (required)
- ingredients: Array of individual ingredient items with quantities (e.g., "2 cups flour", "1 tbsp salt"). Required, at least 3 items. Extract as many as found.
- instructions: Array of numbered steps as separate items. Required, at least 2 steps. Keep each step concise (1-2 sentences max).
- description: 1-2 sentence summary of what the dish is. Optional, can be empty string.
- image_url: Full absolute URL to the recipe's main/featured image. Look for og:image meta tag first, then img src tags. Copy URLs exactly as they appear in HTML. If relative path, prepend domain. Return empty string if not found.
- servings: Number or "serves X" format (e.g., "4" or "serves 4-6"). Optional.
- prep_time: Duration format like "15 min", "1 hour 30 min". Optional.
- cook_time: Duration format like "30 min", "2 hours". Optional.
- category: Best guess at recipe category. Choose from: Breakfast, Lunch, Dinner, Snacks, Dessert, Beverages, Sides, Soups, Salads, Pasta, Meat, Vegetarian, Vegan, or Baking. Return single string. Optional but recommended.

REQUIRED FORMAT (return valid JSON only):
{{
    "name": "Recipe Name",
    "ingredients": ["2 cups flour", "1 tbsp salt", "1 egg"],
    "instructions": ["Preheat oven to 350F", "Mix dry ingredients", "Bake for 30 minutes"],
    "description": "A delicious baked good.",
    "image_url": "https://example.com/recipe.jpg",
    "servings": "8",
    "prep_time": "15 min",
    "cook_time": "45 min",
    "category": "Baking"
}}

URL: {url}

HTML:
{html_excerpt}"""

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract JSON from response
        response_text = response.content[0].text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]

        recipe_data = json.loads(response_text)
        return recipe_data

    except json.JSONDecodeError as e:
        logger.warning(f"Claude returned invalid JSON for {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error calling Claude API for {url}: {e}")
        return None


def process_pending_recipes():
    """Main function to process all pending recipe imports"""

    app = create_app('production')

    with app.app_context():
        # Get API key from environment or config
        api_key = app.config.get('ANTHROPIC_API_KEY')

        if not api_key:
            logger.error("ANTHROPIC_API_KEY not found in config")
            return False

        # Find all pending imports (failed ones are not retried)
        pending = MealPlan.query.filter(MealPlan.import_status == 'pending').all()

        if not pending:
            logger.info("No pending recipes to process")
            return True

        logger.info(f"Processing {len(pending)} pending recipes")

        processed = 0
        failed = 0

        for meal_plan in pending:
            try:
                if not meal_plan.source_url:
                    logger.warning(f"MealPlan {meal_plan.id} has no source_url, skipping")
                    meal_plan.import_status = 'failed'
                    db.session.add(meal_plan)
                    failed += 1
                    continue

                logger.info(f"Processing {meal_plan.source_url}")

                # Step 1: Try fast schema.org parsing first
                recipe_data = import_recipe_from_url(meal_plan.source_url)

                if not recipe_data:
                    # Step 2: Try Claude API for intelligent parsing
                    logger.info(f"Schema.org failed, trying Claude API for {meal_plan.source_url}")

                    # Fetch HTML
                    import urllib.request
                    req = urllib.request.Request(
                        meal_plan.source_url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                    )

                    with urllib.request.urlopen(req, timeout=15) as response:
                        html = response.read().decode("utf-8", errors="ignore")

                    # Extract with Claude
                    recipe_data = extract_recipe_with_claude(html, meal_plan.source_url, api_key)

                if not recipe_data:
                    logger.warning(f"Could not extract recipe from {meal_plan.source_url}")
                    meal_plan.import_status = 'failed'
                    db.session.add(meal_plan)
                    db.session.commit()
                    failed += 1
                    continue

                # Step 3: Create Meal record
                # Convert lists to newline-separated strings for database storage
                ingredients_data = recipe_data.get('ingredients', [])
                if isinstance(ingredients_data, list):
                    ingredients_str = '\n'.join(ingredients_data)
                else:
                    ingredients_str = ingredients_data

                instructions_data = recipe_data.get('instructions', [])
                if isinstance(instructions_data, list):
                    instructions_str = '\n'.join(instructions_data)
                else:
                    instructions_str = instructions_data

                # Get image URL (ensure it's a string, not empty, and accessible)
                image_url = recipe_data.get('image_url', '')
                if image_url and not isinstance(image_url, str):
                    image_url = str(image_url)

                # Validate that the image URL is actually accessible
                if image_url:
                    try:
                        req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, timeout=5) as response:
                            if response.status == 200:
                                logger.info(f"✓ Image URL verified: {image_url}")
                            else:
                                logger.warning(f"Image URL returned status {response.status}, skipping: {image_url}")
                                image_url = None
                    except Exception as e:
                        logger.warning(f"Image URL not accessible ({str(e)[:50]}), skipping: {image_url}")
                        image_url = None

                meal = Meal(
                    name=recipe_data.get('name', 'Imported Recipe'),
                    description=recipe_data.get('description', ''),
                    category=recipe_data.get('category'),  # Claude's category suggestion
                    ingredients=ingredients_str,
                    instructions=instructions_str,
                    image_filename=image_url or None,
                    source_url=meal_plan.source_url,
                    source_name=extract_domain_name(meal_plan.source_url),
                    household_id=meal_plan.household_id,
                    created_by=meal_plan.household.created_by  # Attribute to household creator
                )

                db.session.add(meal)
                db.session.flush()  # Get meal.id

                # Step 4: Update MealPlan
                meal_plan.meal_id = meal.id
                meal_plan.import_status = 'imported'
                meal_plan.custom_entry = None
                db.session.add(meal_plan)
                db.session.commit()

                logger.info(f"✓ Successfully imported: {meal.name}")
                processed += 1

            except urllib.error.URLError as e:
                logger.error(f"Network error for {meal_plan.source_url}: {e}")
                meal_plan.import_status = 'failed'
                db.session.add(meal_plan)
                db.session.commit()
                failed += 1
            except Exception as e:
                logger.error(f"Error processing {meal_plan.source_url}: {e}")
                meal_plan.import_status = 'failed'
                db.session.add(meal_plan)
                db.session.commit()
                failed += 1

        logger.info(f"Processing complete: {processed} imported, {failed} failed")
        return True


if __name__ == '__main__':
    try:
        success = process_pending_recipes()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
