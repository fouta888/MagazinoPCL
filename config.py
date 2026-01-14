import os

SECRET_KEY = os.environ.get("SECRET_KEY", "default_key_per_sviluppo")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "magazzino")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "PClungoni")
