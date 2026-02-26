import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

_pkg_dir = os.path.abspath(os.path.dirname(__file__))
_shared_instance = os.path.join(os.path.dirname(_pkg_dir), 'instance')
_HABITZ_DB = f'sqlite:///{os.path.join(_shared_instance, "habitz.db")}'


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', _HABITZ_DB)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    USDA_API_KEY = os.environ.get('USDA_API_KEY', '')
    NUTRITIONIX_APP_ID = os.environ.get('NUTRITIONIX_APP_ID', '')
    NUTRITIONIX_API_KEY = os.environ.get('NUTRITIONIX_API_KEY', '')
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
