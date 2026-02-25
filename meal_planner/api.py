"""
Recipe API endpoints for external integrations
Provides a discoverable interface for submitting recipe data
Secured with API key authentication
"""

from flask import Blueprint, request, jsonify
from functools import wraps
from .models import db, Meal, ApiKey, User
from urllib.parse import urlparse

api_bp = Blueprint('api', __name__, url_prefix='/api/recipes')


def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')

        if not api_key:
            return jsonify({"error": "Missing API key. Use X-API-Key header."}), 401

        key = ApiKey.query.filter_by(key=api_key, is_active=True).first()
        if not key:
            return jsonify({"error": "Invalid API key"}), 401

        # Update last_used timestamp
        from datetime import datetime
        key.last_used = datetime.utcnow()
        db.session.commit()

        # Add user to request context
        request.api_user = key.user
        return f(*args, **kwargs)

    return decorated_function


@api_bp.route('/schema', methods=['GET'])
def get_recipe_schema():
    """Get the JSON schema for creating a recipe"""
    schema = {
        "title": "Recipe Schema",
        "description": "Schema for submitting recipe data to the Meal Planner",
        "type": "object",
        "required": ["name", "ingredients", "instructions"],
        "properties": {
            "name": {
                "type": "string",
                "description": "Recipe name/title",
                "minLength": 3,
                "maxLength": 255,
                "example": "Spaghetti Carbonara"
            },
            "description": {
                "type": "string",
                "description": "Brief description of the recipe",
                "maxLength": 500,
                "example": "Classic Italian pasta with bacon and creamy sauce"
            },
            "ingredients": {
                "type": "string",
                "description": "Ingredients list, one per line",
                "example": "400g spaghetti\n200g bacon\n3 eggs\n100g parmesan cheese\nSalt and pepper"
            },
            "instructions": {
                "type": "string",
                "description": "Cooking instructions, one step per line",
                "example": "Cook pasta according to package directions\nFry bacon until crispy\nWhisk eggs with cheese\nCombine all ingredients"
            },
            "category": {
                "type": "string",
                "description": "Recipe category",
                "enum": ["Breakfast", "Lunch", "Dinner", "Appetizer", "Side", "Dessert", "Vegetarian", "Vegan", "Beef", "Chicken", "Pork", "Seafood", "Pasta", "Soup", "Salad", "Other"],
                "example": "Pasta"
            },
            "source_url": {
                "type": "string",
                "description": "URL where recipe was sourced from",
                "format": "uri",
                "example": "https://www.example.com/recipe"
            },
            "image_url": {
                "type": "string",
                "description": "URL of recipe image",
                "format": "uri",
                "example": "https://www.example.com/recipe-image.jpg"
            }
        }
    }
    return jsonify(schema)


@api_bp.route('', methods=['POST'])
@require_api_key
def create_recipe():
    """
    Create a new recipe via API

    Request body should be JSON matching the recipe schema.
    Returns the created recipe with ID.
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Validate required fields
        required_fields = ["name", "ingredients", "instructions"]
        missing_fields = [f for f in required_fields if not data.get(f)]
        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "required_fields": required_fields
            }), 400

        # Extract source name from URL if provided
        source_name = None
        source_url = data.get('source_url')
        if source_url:
            try:
                parsed = urlparse(source_url)
                source_name = parsed.netloc.replace('www.', '')
            except:
                pass

        # Verify user has a household
        if not request.api_user.household_id:
            return jsonify({"error": "API user must be part of a household"}), 400

        # Create meal
        meal = Meal(
            name=data.get('name', '').strip(),
            description=data.get('description', '').strip(),
            category=data.get('category'),
            ingredients=data.get('ingredients', '').strip(),
            instructions=data.get('instructions', '').strip(),
            image_filename=data.get('image_url'),  # Store URL directly
            source_url=source_url,
            source_name=source_name,
            household_id=request.api_user.household_id,
            created_by=request.api_user.id
        )

        db.session.add(meal)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Recipe '{meal.name}' created successfully",
            "recipe": {
                "id": meal.id,
                "name": meal.name,
                "description": meal.description,
                "category": meal.category,
                "source_url": meal.source_url,
                "source_name": meal.source_name,
                "created_at": meal.created_at.isoformat() if meal.created_at else None
            }
        }), 201

    except ValueError as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create recipe: {str(e)}"}), 500


@api_bp.route('/<int:recipe_id>', methods=['GET'])
@require_api_key
def get_recipe(recipe_id):
    """Get a specific recipe by ID"""
    meal = Meal.query.get(recipe_id)
    if not meal:
        return jsonify({"error": "Recipe not found"}), 404

    # Check ownership
    if meal.created_by != request.api_user.id:
        return jsonify({"error": "Access denied"}), 403

    return jsonify({
        "id": meal.id,
        "name": meal.name,
        "description": meal.description,
        "category": meal.category,
        "ingredients": meal.ingredients,
        "instructions": meal.instructions,
        "image_url": meal.image_filename,
        "source_url": meal.source_url,
        "source_name": meal.source_name,
        "created_by": meal.creator.username,
        "created_at": meal.created_at.isoformat() if meal.created_at else None
    })


@api_bp.route('/<int:recipe_id>', methods=['PUT', 'PATCH'])
@require_api_key
def update_recipe(recipe_id):
    """Update an existing recipe"""
    meal = Meal.query.get(recipe_id)
    if not meal:
        return jsonify({"error": "Recipe not found"}), 404

    # Check ownership
    if meal.created_by != request.api_user.id:
        return jsonify({"error": "Access denied"}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Update allowed fields
        if 'name' in data:
            meal.name = data['name'].strip()
        if 'description' in data:
            meal.description = data['description'].strip()
        if 'category' in data:
            meal.category = data['category']
        if 'ingredients' in data:
            meal.ingredients = data['ingredients'].strip()
        if 'instructions' in data:
            meal.instructions = data['instructions'].strip()
        if 'image_url' in data:
            meal.image_filename = data['image_url']

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Recipe '{meal.name}' updated successfully",
            "recipe": {
                "id": meal.id,
                "name": meal.name,
                "description": meal.description,
                "category": meal.category
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update recipe: {str(e)}"}), 500


@api_bp.route('/<int:recipe_id>', methods=['DELETE'])
@require_api_key
def delete_recipe(recipe_id):
    """Delete a recipe"""
    meal = Meal.query.get(recipe_id)
    if not meal:
        return jsonify({"error": "Recipe not found"}), 404

    # Check ownership
    if meal.created_by != request.api_user.id:
        return jsonify({"error": "Access denied"}), 403

    try:
        recipe_name = meal.name
        db.session.delete(meal)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Recipe '{recipe_name}' deleted successfully"
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete recipe: {str(e)}"}), 500


@api_bp.route('', methods=['GET'])
@require_api_key
def list_recipes():
    """List all recipes for the current user"""
    try:
        # Get user's recipes
        user_recipes = Meal.query.filter_by(created_by=request.api_user.id)

        recipes = []
        for meal in user_recipes:
            recipes.append({
                "id": meal.id,
                "name": meal.name,
                "category": meal.category,
                "description": meal.description[:100] if meal.description else None,
                "source_url": meal.source_url,
                "created_at": meal.created_at.isoformat() if meal.created_at else None
            })

        return jsonify({
            "total": len(recipes),
            "recipes": recipes
        })

    except Exception as e:
        return jsonify({"error": f"Failed to list recipes: {str(e)}"}), 500


@api_bp.route('/status', methods=['GET'])
def api_status():
    """Health check endpoint and API documentation"""
    return jsonify({
        "status": "ok",
        "version": "1.0",
        "endpoints": {
            "status": "GET /api/recipes/status",
            "schema": "GET /api/recipes/schema",
            "list": "GET /api/recipes",
            "create": "POST /api/recipes",
            "get": "GET /api/recipes/<id>",
            "update": "PUT/PATCH /api/recipes/<id>",
            "delete": "DELETE /api/recipes/<id>"
        },
        "authentication": "All endpoints except /status and /schema require login"
    })
