"""
Configuration — environment variables for SmartTap.
Copy .env.example → .env and fill in your values.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    DEBUG      = os.getenv("DEBUG", "True") == "True"

    # PostgreSQL — accepts either a full URL or individual parts
    DATABASE_URL = os.getenv("DATABASE_URL", "")   # Render/Railway inject this
    DB_HOST      = os.getenv("DB_HOST",     "localhost")
    DB_PORT      = os.getenv("DB_PORT",     "5432")
    DB_NAME      = os.getenv("DB_NAME",     "water_monitor")
    DB_USER      = os.getenv("DB_USER",     "postgres")
    DB_PASSWORD  = os.getenv("DB_PASSWORD", "")
    DB_SSLMODE   = os.getenv("DB_SSLMODE",  "prefer")

    # MQTT – HiveMQ Cloud
    MQTT_BROKER   = os.getenv("MQTT_BROKER",   "YOUR_HIVEMQ_BROKER_URL")
    MQTT_PORT     = int(os.getenv("MQTT_PORT", "8883"))
    MQTT_USERNAME = os.getenv("MQTT_USERNAME", "YOUR_HIVEMQ_USERNAME")
    MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "YOUR_HIVEMQ_PASSWORD")
    MQTT_TOPIC    = os.getenv("MQTT_TOPIC",    "water/data")

    # Gemini AI
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")

    # ML Model
    MODEL_PATH = os.getenv("MODEL_PATH", "ml/leak_detector.pkl")
