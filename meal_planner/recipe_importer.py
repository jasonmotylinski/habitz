"""
Recipe Importer - Extract recipe data from URLs
Supports structured data (schema.org/Recipe format)
"""

import urllib.request
import json
import re
from urllib.parse import urlparse


def extract_domain_name(url):
    """Extract domain name from URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return domain
    except:
        return 'unknown'


def _is_recipe_type(type_value):
    """Check if a @type value indicates a Recipe (handles string or list)"""
    if isinstance(type_value, list):
        return 'Recipe' in type_value
    return type_value == 'Recipe'


def extract_structured_data(html):
    """
    Extract recipe from JSON-LD structured data (schema.org)
    Returns dict with recipe data or None if not found
    """
    try:
        # Allow any attributes on the script tag (e.g. id="schema-unified-0")
        pattern = r'<script[^>]+type="application/ld\+json"[^>]*>(.+?)</script>'
        matches = re.findall(pattern, html, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match.strip())

                recipe = None
                if isinstance(data, dict):
                    if _is_recipe_type(data.get('@type')):
                        recipe = data
                    elif '@graph' in data:
                        for item in data['@graph']:
                            if isinstance(item, dict) and _is_recipe_type(item.get('@type')):
                                recipe = item
                                break
                elif isinstance(data, list):
                    # JSON-LD can be a top-level array
                    for item in data:
                        if isinstance(item, dict) and _is_recipe_type(item.get('@type')):
                            recipe = item
                            break

                if recipe:
                    return _parse_recipe_schema(recipe)
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

        return None
    except Exception as e:
        print(f"Error extracting structured data: {e}")
        return None


def _parse_recipe_schema(recipe):
    """Parse schema.org Recipe format into our format"""
    try:
        # Extract ingredients
        ingredients_raw = recipe.get('recipeIngredient', [])
        ingredients = '\n'.join(ingredients_raw) if ingredients_raw else ''

        # Extract instructions
        instructions_raw = recipe.get('recipeInstructions', [])
        instructions = _parse_instructions(instructions_raw)

        # Extract image URL
        image_url = None
        image_data = recipe.get('image')
        if image_data:
            if isinstance(image_data, str):
                image_url = image_data
            elif isinstance(image_data, dict):
                image_url = image_data.get('url')
            elif isinstance(image_data, list) and len(image_data) > 0:
                if isinstance(image_data[0], dict):
                    image_url = image_data[0].get('url')
                else:
                    image_url = image_data[0]

        return {
            'name': recipe.get('name', 'Imported Recipe'),
            'description': recipe.get('description', ''),
            'ingredients': ingredients,
            'instructions': instructions,
            'image_url': image_url,
            'prep_time': recipe.get('prepTime', ''),
            'cook_time': recipe.get('cookTime', ''),
            'servings': recipe.get('recipeYield', ''),
        }
    except Exception as e:
        print(f"Error parsing recipe schema: {e}")
        return None


def _parse_instructions(instructions_raw):
    """Parse various instruction formats"""
    if not instructions_raw:
        return ''

    lines = []
    if isinstance(instructions_raw, list):
        for item in instructions_raw:
            if isinstance(item, dict):
                text = item.get('text') or item.get('description', '')
                if text:
                    lines.append(text.strip())
            elif isinstance(item, str):
                lines.append(item.strip())
    elif isinstance(instructions_raw, str):
        return instructions_raw

    return '\n'.join(lines)




def import_recipe_from_url(url, api_endpoint=None):
    """
    Main function to import a recipe from a URL
    Extracts recipe using JSON-LD structured data (schema.org)

    Args:
        url: Recipe URL to import from
        api_endpoint: Optional API endpoint URL to submit recipe to
                     e.g., "http://localhost:5000/api/recipes"

    Returns:
        dict with recipe data and metadata, or None if import fails
    """
    try:
        print(f"Importing recipe from: {url}")

        # Fetch the page
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode("utf-8", errors="ignore")

        print("✓ Page fetched successfully")

        # Extract structured data
        recipe = extract_structured_data(html)
        if recipe:
            print("✓ Recipe extracted from structured data")
            recipe["source"] = "structured_data"
            recipe["source_url"] = url
            recipe["source_name"] = extract_domain_name(url)

            # If API endpoint provided, submit to API
            if api_endpoint:
                return submit_to_api(recipe, api_endpoint)
            return recipe

        print("✗ No structured recipe data found on this page")
        return None

    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
        return None
    except Exception as e:
        print(f"Error importing recipe: {e}")
        return None


def submit_to_api(recipe_data, api_endpoint, auth_token=None):
    """
    Submit extracted recipe data to API endpoint

    Args:
        recipe_data: Dict with recipe fields
        api_endpoint: API endpoint URL (e.g., http://localhost:5000/api/recipes)
        auth_token: Optional authentication token

    Returns:
        dict with API response or None if submission fails
    """
    try:
        print(f"Submitting to API: {api_endpoint}")

        payload = json.dumps({
            "name": recipe_data.get("name"),
            "description": recipe_data.get("description"),
            "ingredients": recipe_data.get("ingredients"),
            "instructions": recipe_data.get("instructions"),
            "image_url": recipe_data.get("image_url"),
            "source_url": recipe_data.get("source_url")
        })

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "MealPlanner-RecipeImporter/1.0"
        }

        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        req = urllib.request.Request(
            api_endpoint,
            data=payload.encode('utf-8'),
            headers=headers,
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            print("✓ Recipe submitted to API successfully")
            return result

    except urllib.error.HTTPError as e:
        error_response = e.read().decode('utf-8')
        print(f"API Error {e.code}: {error_response}")
        return None
    except Exception as e:
        print(f"Error submitting to API: {e}")
        return None
