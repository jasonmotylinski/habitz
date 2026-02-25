import re
import requests
import sqlalchemy as sa
from flask import current_app
from sqlalchemy import text

from ..models import FoodItem, UsdaFood, db

FDC_SEARCH_URL = 'https://api.nal.usda.gov/fdc/v1/foods/search'
NUTRITIONIX_URL = 'https://trackapi.nutritionix.com/v2/natural/nutrients'
OFF_SEARCH_URL = 'https://world.openfoodfacts.org/cgi/search.pl'
OFF_HEADERS = {'User-Agent': 'Habitz/1.0 (https://github.com/habitz)'}

# Nutrient IDs in the FoodData Central API
FDC_NUTRIENTS = {
    1008: 'calories',   # Energy (kcal)
    957:  'calories',   # Energy, Atwater General (fallback)
    958:  'calories',   # Energy, Atwater Specific (fallback)
    1003: 'protein_g',
    1004: 'fat_g',
    1005: 'carbs_g',
    1079: 'fiber_g',
}


# ---------------------------------------------------------------------------
# Natural language query preprocessing
# ---------------------------------------------------------------------------

# Words that carry no food meaning and should be stripped
_FILLERS = {
    'a', 'an', 'the', 'some', 'of', 'with', 'and', 'my', 'fresh',
    'organic', 'large', 'medium', 'small', 'big', 'little', 'extra',
    'hot', 'cold', 'warm', 'homemade', 'store', 'bought',
}

# Measurement units — strip these so "2 cups rice" → "rice"
_UNITS = {
    'cup', 'cups', 'tbsp', 'tablespoon', 'tablespoons',
    'tsp', 'teaspoon', 'teaspoons', 'oz', 'ounce', 'ounces',
    'lb', 'lbs', 'pound', 'pounds', 'g', 'gram', 'grams',
    'kg', 'ml', 'l', 'liter', 'liters',
    'slice', 'slices', 'piece', 'pieces', 'serving', 'servings',
    'bowl', 'bowls', 'handful', 'handfuls', 'scoop', 'scoops',
    'can', 'cans', 'bottle', 'bottles', 'package', 'packages', 'pkg',
    'container', 'bar', 'bars',
}

# Common shorthand → full search term
_ALIASES = {
    'pb':         'peanut butter',
    'pb&j':       'peanut butter',
    'oj':         'orange juice',
    'evoo':       'olive oil',
    'ff':         'fat free',
    'lf':         'low fat',
    'ww':         'whole wheat',
    'gf':         'gluten free',
    'spud':       'potato',
    'spuds':      'potatoes',
    'yam':        'sweet potato',
    'yams':       'sweet potatoes',
    'berries':    'mixed berries',
    'greens':     'mixed greens',
}


def _parse_query(query):
    """
    Clean a natural language food query down to searchable terms.

    Examples:
      "2 cups of brown rice"   → "brown rice"
      "a banana"               → "banana"
      "3 scrambled eggs"       → "scrambled eggs"
      "pb"                     → "peanut butter"
      "large chicken breast"   → "chicken breast"
    """
    q = query.lower().strip()

    # Full-phrase alias check first
    if q in _ALIASES:
        return _ALIASES[q]

    # Strip leading quantity: integers, decimals, fractions (½ ¼ ¾ etc.)
    q = re.sub(r'^[\d½¼¾⅓⅔⅛⅜⅝⅞]+(\.\d+)?\s*', '', q)
    # Written-out numbers at the start
    q = re.sub(
        r'^(half|a half|one|two|three|four|five|six|seven|eight|nine|ten)\s+',
        '', q,
    )

    words = q.split()
    cleaned = []
    for word in words:
        w = word.strip('.,!?')
        if not w:
            continue
        if w in _ALIASES:
            cleaned.extend(_ALIASES[w].split())
        elif w not in _FILLERS and w not in _UNITS:
            cleaned.append(w)

    return ' '.join(cleaned) if cleaned else query.strip()


# ---------------------------------------------------------------------------
# Local search — FTS5 with ILIKE fallback
# ---------------------------------------------------------------------------

def _fts_query(words):
    """Build an FTS5 MATCH expression: each word as a prefix term."""
    safe = [re.sub(r'[^\w]', '', w) for w in words]
    safe = [w for w in safe if w]
    if not safe:
        return None
    return ' '.join(f'{w}*' for w in safe)


def _search_local(words, offset, page_size):
    fts_q = _fts_query(words)
    if fts_q:
        try:
            rows = db.session.execute(text("""
                SELECT food_id
                FROM usda_food_fts
                WHERE usda_food_fts MATCH :q
                ORDER BY
                    CASE food_type
                        WHEN 'everyday'   THEN 0
                        WHEN 'prepared'   THEN 1
                        WHEN 'restaurant' THEN 2
                        ELSE 3
                    END,
                    rank
                LIMIT :limit OFFSET :offset
            """), {'q': fts_q, 'limit': page_size, 'offset': offset}).fetchall()

            food_ids = [r[0] for r in rows]
            if food_ids:
                by_id = {f.food_id: f for f in
                         UsdaFood.query.filter(UsdaFood.food_id.in_(food_ids)).all()}
                return [by_id[fid].to_search_result() for fid in food_ids if fid in by_id]
        except Exception:
            pass  # FTS table not built yet — fall through to ILIKE

    # ILIKE fallback (used before first import or if FTS table is missing)
    return _search_local_ilike(words, offset, page_size)


def _stem(word):
    w = word.lower()
    if w.endswith('oes') and len(w) > 4:
        return w[:-2]
    if w.endswith('ies') and len(w) > 4:
        return w[:-3] + 'y'
    if w.endswith('s') and not w.endswith('ss') and len(w) > 3:
        return w[:-1]
    return w


def _search_local_ilike(words, offset, page_size):
    def word_filter(word):
        stem = _stem(word)
        terms = {word.lower(), stem}
        clauses = []
        for t in terms:
            clauses.append(UsdaFood.name.ilike(f'%{t}%'))
            clauses.append(UsdaFood.alternate_names.ilike(f'%{t}%'))
        return sa.or_(*clauses)

    first_stem = _stem(words[0])
    first_word = words[0].lower()
    type_rank = sa.case(
        (UsdaFood.food_type == 'everyday', 0),
        (UsdaFood.food_type == 'prepared', 1),
        (UsdaFood.food_type == 'restaurant', 2),
        else_=3,
    )
    name_rank = sa.case(
        (sa.or_(UsdaFood.name.ilike(f'{first_word}'),
                UsdaFood.name.ilike(f'{first_stem}')), 0),
        (sa.or_(UsdaFood.name.ilike(f'{first_word},%'),
                UsdaFood.name.ilike(f'{first_stem},%'),
                UsdaFood.name.ilike(f'{first_stem}s,%')), 1),
        (sa.or_(UsdaFood.name.ilike(f'{first_word} %'),
                UsdaFood.name.ilike(f'{first_stem} %')), 2),
        else_=3,
    )

    q = UsdaFood.query
    for word in words:
        q = q.filter(word_filter(word))
    foods = q.order_by(type_rank, name_rank, UsdaFood.name).offset(offset).limit(page_size).all()
    return [f.to_search_result() for f in foods]


# ---------------------------------------------------------------------------
# FoodData Central API search
# ---------------------------------------------------------------------------

def _extract_fdc_nutrient(nutrients, *nutrient_ids):
    """Return the first matching nutrient value from a list of candidate IDs."""
    for nid in nutrient_ids:
        for n in nutrients:
            if n.get('nutrientId') == nid:
                val = n.get('value') or n.get('amount', 0)
                if val:
                    return float(val)
    return 0


def _search_fdc(query, page, page_size):
    api_key = current_app.config.get('USDA_API_KEY')
    if not api_key:
        return []

    try:
        resp = requests.get(FDC_SEARCH_URL, params={
            'api_key': api_key,
            'query': query,
            'pageSize': page_size,
            'pageNumber': page,
            'dataType': 'Foundation,SR Legacy',
            'sortOrder': 'asc',
        }, timeout=2)
    except requests.RequestException:
        return []

    if resp.status_code != 200:
        return []

    results = []
    for food in resp.json().get('foods', []):
        nutrients = food.get('foodNutrients', [])
        serving_size = food.get('servingSize')
        serving_unit = food.get('servingSizeUnit') or 'g'
        results.append({
            'name': food.get('description', '').title(),
            'brand': food.get('brandOwner') or food.get('brandName'),
            'source': 'usda_fdc',
            'source_id': str(food.get('fdcId', '')),
            # Calories: try 1008 first, fall back to Atwater variants
            'calories': _extract_fdc_nutrient(nutrients, 1008, 957, 958),
            'protein_g': _extract_fdc_nutrient(nutrients, 1003),
            'fat_g': _extract_fdc_nutrient(nutrients, 1004),
            'carbs_g': _extract_fdc_nutrient(nutrients, 1005),
            'fiber_g': _extract_fdc_nutrient(nutrients, 1079) or None,
            'serving_size': f"{serving_size}{serving_unit}" if serving_size else '100g',
            'serving_weight_g': float(serving_size) if serving_size else 100,
        })
    return results


# ---------------------------------------------------------------------------
# Nutritionix natural language search
# ---------------------------------------------------------------------------

def _search_nutritionix(query):
    app_id = current_app.config.get('NUTRITIONIX_APP_ID')
    api_key = current_app.config.get('NUTRITIONIX_API_KEY')
    if not app_id or not api_key:
        return []

    try:
        resp = requests.post(NUTRITIONIX_URL,
            json={'query': query},
            headers={
                'x-app-id': app_id,
                'x-app-key': api_key,
                'Content-Type': 'application/json',
            },
            timeout=3,
        )
    except requests.RequestException:
        return []

    if resp.status_code != 200:
        return []

    results = []
    for food in resp.json().get('foods', []):
        serving_qty = food.get('serving_qty', 1)
        serving_unit = food.get('serving_unit', '')
        serving_weight = food.get('serving_weight_grams') or 100
        results.append({
            'name': food.get('food_name', '').title(),
            'brand': food.get('brand_name'),
            'source': 'nutritionix',
            'source_id': food.get('nix_item_id') or food.get('food_name', ''),
            'calories': round(food.get('nf_calories') or 0, 1),
            'protein_g': round(food.get('nf_protein') or 0, 1),
            'carbs_g': round(food.get('nf_total_carbohydrate') or 0, 1),
            'fat_g': round(food.get('nf_total_fat') or 0, 1),
            'fiber_g': round(food.get('nf_dietary_fiber') or 0, 1) or None,
            'serving_size': f"{serving_qty} {serving_unit}".strip(),
            'serving_weight_g': float(serving_weight),
        })
    return results


# ---------------------------------------------------------------------------
# Open Food Facts search
# ---------------------------------------------------------------------------

def _search_off(query, page, page_size):
    try:
        resp = requests.get(OFF_SEARCH_URL, params={
            'search_terms': query,
            'search_simple': 1,
            'action': 'process',
            'json': 1,
            'page': page,
            'page_size': page_size,
            'fields': 'code,product_name,brands,nutriments,serving_size,serving_quantity',
        }, headers=OFF_HEADERS, timeout=5)
    except requests.RequestException:
        return []

    if resp.status_code != 200:
        return []

    results = []
    for product in resp.json().get('products', []):
        name = (product.get('product_name') or '').strip()
        if not name:
            continue
        n = product.get('nutriments', {})
        # Prefer per-serving values, fall back to per-100g
        calories  = n.get('energy-kcal_serving') or n.get('energy-kcal_100g') or 0
        protein   = n.get('proteins_serving')    or n.get('proteins_100g')    or 0
        carbs     = n.get('carbohydrates_serving') or n.get('carbohydrates_100g') or 0
        fat       = n.get('fat_serving')         or n.get('fat_100g')         or 0
        fiber     = n.get('fiber_serving')       or n.get('fiber_100g')
        serving_size   = product.get('serving_size')
        serving_weight = product.get('serving_quantity')
        results.append({
            'name': name,
            'brand': (product.get('brands') or '').split(',')[0].strip() or None,
            'source': 'openfoodfacts',
            'source_id': product.get('code', ''),
            'calories': round(float(calories), 1),
            'protein_g': round(float(protein), 1),
            'carbs_g': round(float(carbs), 1),
            'fat_g': round(float(fat), 1),
            'fiber_g': round(float(fiber), 1) if fiber else None,
            'serving_size': serving_size or '100g',
            'serving_weight_g': float(serving_weight) if serving_weight else 100,
        })
    return results


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def search_foods(query, page=1, page_size=20):
    """Search local SR Legacy DB, then supplement with Nutritionix and FDC."""
    if not query.strip():
        return []

    # Preprocess: strip quantities, units, fillers; expand aliases
    clean = _parse_query(query)
    words = clean.split()
    if not words:
        return []

    offset = (page - 1) * page_size

    # Local search
    local = _search_local(words, offset, page_size)

    # Fall back to last word if AND query returned nothing (e.g. "everything bagel" → "bagel")
    if not local and len(words) > 1:
        local = _search_local([words[-1]], offset, page_size)

    seen_ids = {r['source_id'] for r in local}
    extra = []

    # Only call external APIs when local results are sparse — avoids waiting
    # for API timeouts on common foods that are already in the local DB.
    if len(local) < 5:
        # Nutritionix — natural language, surfaces branded/specific foods local DB lacks
        try:
            for r in _search_nutritionix(query):
                if r['source_id'] not in seen_ids:
                    seen_ids.add(r['source_id'])
                    extra.append(r)
        except Exception:
            pass

        # Open Food Facts — branded/packaged products
        try:
            for r in _search_off(query, page, page_size):
                if r['source_id'] not in seen_ids:
                    seen_ids.add(r['source_id'])
                    extra.append(r)
        except Exception:
            pass

        # FDC API — Foundation foods not in SR Legacy
        try:
            for r in _search_fdc(query, page, page_size):
                if r['source_id'] not in seen_ids:
                    seen_ids.add(r['source_id'])
                    extra.append(r)
        except Exception:
            pass

    return (local + extra)[:page_size]


def get_or_create_food_item(data):
    """Find existing cached FoodItem or create one from search result data."""
    if data.get('source') and data.get('source_id'):
        existing = FoodItem.query.filter_by(
            source=data['source'],
            source_id=data['source_id']
        ).first()
        if existing:
            return existing

    item = FoodItem(
        name=data['name'],
        brand=data.get('brand'),
        source=data.get('source', 'custom'),
        source_id=data.get('source_id'),
        calories=data.get('calories', 0),
        protein_g=data.get('protein_g', 0),
        carbs_g=data.get('carbs_g', 0),
        fat_g=data.get('fat_g', 0),
        fiber_g=data.get('fiber_g'),
        serving_size=data.get('serving_size'),
        serving_weight_g=data.get('serving_weight_g'),
    )
    db.session.add(item)
    db.session.commit()
    return item
