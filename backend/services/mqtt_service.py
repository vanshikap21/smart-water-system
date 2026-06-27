"""
MQTT Service — connects to HiveMQ Cloud over TLS and processes
incoming sensor payloads from the ESP32.
"""

import json
import logging
import ssl

import paho.mqtt.client as mqtt

from config import Config
from services.water_service import insert_sensor_reading

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MQTT callbacks
# ---------------------------------------------------------------------------

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected. Subscribing to '%s'", Config.MQTT_TOPIC)
        client.subscribe(Config.MQTT_TOPIC)
    else:
        logger.error("MQTT connection failed with code %d", rc)


def on_message(client, userdata, msg):
    """Parse incoming JSON payload and persist to database."""
    try:
        payload = json.loads(msg.payload.decode("utf-8"))

        flow_rate = float(payload.get("flow_rate", 0.0))
        tank_level = float(payload.get("tank_level", 0.0))

        # Basic validation
        if not (0 <= flow_rate <= 100):
            logger.warning("flow_rate out of range: %s", flow_rate)
            return

        if not (0 <= tank_level <= 100):
            logger.warning("tank_level out of range: %s", tank_level)
            return

        row_id = insert_sensor_reading(flow_rate, tank_level)

        logger.info(
            "Saved sensor reading id=%d flow=%.2f tank=%.1f%%",
            row_id,
            flow_rate,
            tank_level,
        )

    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        logger.error(
            "Invalid MQTT payload: %s | error: %s",
            msg.payload,
            exc,
        )


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning(
            "Unexpected MQTT disconnection (rc=%d). Will auto-reconnect.",
            rc,
        )


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

def start_mqtt_client():
    """Create, configure, and start the blocking MQTT loop."""

    client = mqtt.Client(
        client_id="water-monitor-backend",
        clean_session=True
    )

    # HiveMQ Cloud credentials
    client.username_pw_set(
        Config.MQTT_USERNAME,
        Config.MQTT_PASSWORD
    )

    # TLS configuration
    client.tls_set(
        cert_reqs=ssl.CERT_NONE,
        tls_version=ssl.PROTOCOL_TLS
    )

    # Disable certificate verification
    client.tls_insecure_set(True)

    # Callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    logger.info(
        "Connecting to MQTT broker %s:%d ...",
        Config.MQTT_BROKER,
        Config.MQTT_PORT
    )

    client.connect(
        Config.MQTT_BROKER,
        Config.MQTT_PORT,
        keepalive=60
    )

    # Blocks forever (runs in daemon thread from app.py)
    client.loop_forever()