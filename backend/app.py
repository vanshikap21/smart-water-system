"""
Smart Water Monitoring System - Flask Application Entry Point
"""

import threading
import logging
from flask import Flask
from flask_cors import CORS

from database.db import init_db
from routes.data_routes import data_bp
from routes.ml_routes import ml_bp
from routes.ai_routes import ai_bp
from services.mqtt_service import start_mqtt_client


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)


def create_app():
    """Application factory pattern."""

    app = Flask(
        __name__,
        static_folder="../frontend",
        static_url_path="/"
    )

    CORS(app)

    # Load configuration
    app.config.from_object("config.Config")

    # Initialize database
    with app.app_context():
        init_db()
        logger.info("Database initialized.")

    # Register API blueprints
    app.register_blueprint(
        data_bp,
        url_prefix="/api"
    )

    app.register_blueprint(
        ml_bp,
        url_prefix="/api"
    )

    app.register_blueprint(
        ai_bp,
        url_prefix="/api"
    )

    # Serve frontend
    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    return app


# Create global app instance for Gunicorn
app = create_app()


# Start MQTT listener
mqtt_thread = threading.Thread(
    target=start_mqtt_client,
    daemon=True
)

mqtt_thread.start()

logger.info("MQTT client thread started.")


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False
    )