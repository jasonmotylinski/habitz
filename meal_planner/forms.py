from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField, TextAreaField, SelectField, URLField
from wtforms.validators import DataRequired, Length, Optional, URL

class MealForm(FlaskForm):
    """Form for creating/editing meals"""
    MEAL_CATEGORIES = [
        ('', '-- Select Category --'),
        ('Breakfast', 'Breakfast'),
        ('Lunch', 'Lunch'),
        ('Dinner', 'Dinner'),
        ('Appetizer', 'Appetizer'),
        ('Side', 'Side Dish'),
        ('Dessert', 'Dessert'),
        ('Vegetarian', 'Vegetarian'),
        ('Vegan', 'Vegan'),
        ('Beef', 'Beef'),
        ('Chicken', 'Chicken'),
        ('Pork', 'Pork'),
        ('Seafood', 'Seafood'),
        ('Pasta', 'Pasta'),
        ('Soup', 'Soup'),
        ('Salad', 'Salad'),
        ('Other', 'Other'),
    ]

    name = StringField('Meal Name', validators=[
        DataRequired(),
        Length(min=3, max=255, message='Name must be between 3 and 255 characters')
    ])
    description = TextAreaField('Description', validators=[Length(max=500)])
    category = SelectField('Category', choices=MEAL_CATEGORIES, validators=[Optional()])
    ingredients = TextAreaField('Ingredients', validators=[
        DataRequired(),
        Length(min=5, message='Please add at least one ingredient')
    ])
    instructions = TextAreaField('Instructions', validators=[
        DataRequired(),
        Length(min=10, message='Please provide detailed instructions')
    ])
    image = FileField('Recipe Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only (.jpg, .jpeg, .png, .gif)')
    ])
    image_url = URLField('Image URL', validators=[Optional(), URL(message='Please enter a valid URL')])
    submit = SubmitField('Save Meal')

class MealPlanForm(FlaskForm):
    """Form for meal planning"""
    url = URLField('Recipe URL', validators=[Optional(), URL(message='Please enter a valid URL')])
    meal_id = SelectField('Select Meal', coerce=int, validators=[Optional()])
    custom_entry = StringField('Or Custom Entry', validators=[
        Length(max=255, message='Entry must be 255 characters or less')
    ])
    submit = SubmitField('Save')

class ShoppingListForm(FlaskForm):
    """Form for creating shopping lists"""
    store_name = StringField('Store Name', validators=[
        DataRequired(),
        Length(min=2, max=255, message='Store name must be between 2 and 255 characters')
    ])
    submit = SubmitField('Create List')

class ShoppingListItemForm(FlaskForm):
    """Form for adding items to shopping list"""
    item_name = StringField('Item Name', validators=[
        DataRequired(),
        Length(min=1, max=255)
    ])
    quantity = StringField('Quantity', validators=[Optional(), Length(max=50)])
    unit = StringField('Unit', validators=[Optional(), Length(max=50)])
    submit = SubmitField('Add Item')

class RecipeImportForm(FlaskForm):
    """Form for importing recipe from URL"""
    url = URLField('Recipe URL', validators=[
        DataRequired(),
        URL(message='Please enter a valid URL')
    ])
    submit = SubmitField('Import Recipe')
