from flask_wtf import FlaskForm
from wtforms import (FloatField, IntegerField, PasswordField, SelectField,
                     StringField, SubmitField)
from wtforms.validators import (DataRequired, Email, EqualTo, Length,
                                NumberRange, Optional, ValidationError)

from .models import User


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(), Length(min=3, max=80)
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(), Length(min=6)
    ])
    password_confirm = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password')
    ])
    submit = SubmitField('Create Account')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class GoalsForm(FlaskForm):
    daily_calorie_goal = IntegerField('Daily Calorie Goal', validators=[
        DataRequired(), NumberRange(min=500, max=10000)
    ])
    protein_goal_pct = IntegerField('Protein %', validators=[
        DataRequired(), NumberRange(min=0, max=100)
    ])
    carb_goal_pct = IntegerField('Carbs %', validators=[
        DataRequired(), NumberRange(min=0, max=100)
    ])
    fat_goal_pct = IntegerField('Fat %', validators=[
        DataRequired(), NumberRange(min=0, max=100)
    ])
    submit = SubmitField('Save Goals')

    def validate_protein_goal_pct(self, field):
        total = field.data + (self.carb_goal_pct.data or 0) + (self.fat_goal_pct.data or 0)
        if total != 100:
            raise ValidationError(f'Macro percentages must sum to 100 (currently {total}).')


class CustomFoodForm(FlaskForm):
    name = StringField('Food Name', validators=[DataRequired(), Length(max=200)])
    brand = StringField('Brand', validators=[Optional(), Length(max=200)])
    calories = FloatField('Calories', validators=[DataRequired(), NumberRange(min=0)])
    protein_g = FloatField('Protein (g)', validators=[Optional(), NumberRange(min=0)])
    carbs_g = FloatField('Carbs (g)', validators=[Optional(), NumberRange(min=0)])
    fat_g = FloatField('Fat (g)', validators=[Optional(), NumberRange(min=0)])
    fiber_g = FloatField('Fiber (g)', validators=[Optional(), NumberRange(min=0)])
    serving_size = StringField('Serving Size', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Save Food')
