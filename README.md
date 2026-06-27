# 💧 AI-Enabled Smart Water Monitoring System

A production-quality IoT + ML + AI system for real-time water usage monitoring, leak detection, and cost optimisation.

---

## 🏗 Project Structure

```
smart_water_system/
├── backend/
│   ├── app.py                   ← Flask entry point
│   ├── config.py                ← All configuration / env vars
│   ├── requirements.txt
│   ├── .env.example             ← Copy to .env and fill in credentials
│   ├── database/
│   │   └── db.py                ← SQLite schema + connection helper
│   ├── routes/
│   │   ├── data_routes.py       ← /api/live-data, /api/analytics, etc.
│   │   ├── ml_routes.py         ← /api/leak-status, /api/leak-history
│   │   └── ai_routes.py         ← /api/generate-insight, /api/generate-report
│   ├── services/
│   │   ├── water_service.py     ← CRUD + analytics queries
│   │   ├── mqtt_service.py      ← HiveMQ MQTT subscriber
│   │   ├── cost_service.py      ← Dynamic cost + conservation score
│   │   └── ai_service.py        ← Gemini API integration
│   ├── models/
│   │   └── leak_detector.py     ← RF model loader + inference
│   └── ml/
│       ├── train_model.py       ← Dataset generation + training script
│       └── leak_detector.pkl    ← (generated after training)
├── frontend/
│   ├── index.html               ← Single-page dashboard
│   ├── css/style.css
│   └── js/
│       ├── api.js               ← Fetch wrapper for all API calls
│       ├── charts.js            ← Chart.js chart helpers
│       └── dashboard.js         ← Main controller / page router
└── esp32/
    └── water_monitor.ino        ← Arduino firmware for ESP32
```

---

## ⚡ Quick Start

### 1. Clone / extract the project

```bash
cd smart_water_system/backend
```

### 2. Create virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your HiveMQ and Gemini credentials
```

### 4. Train the ML model

```bash
python ml/train_model.py
# Outputs: ml/leak_detector.pkl
```

### 5. Run the Flask server

```bash
python app.py
# Server starts at http://localhost:5000
```

Open your browser at **http://localhost:5000**

---

## 🔌 ESP32 Setup

1. Open `esp32/water_monitor.ino` in Arduino IDE.
2. Install libraries: `PubSubClient`, `ArduinoJson` (via Library Manager).
3. Fill in your Wi-Fi and HiveMQ credentials at the top of the file.
4. Set `TANK_HEIGHT_CM` to match your actual tank depth.
5. Upload to ESP32.

**Wiring:**

| Component       | ESP32 Pin |
|-----------------|-----------|
| YF-S201 Signal  | GPIO 18   |
| YF-S201 VCC     | 5V        |
| YF-S201 GND     | GND       |
| HC-SR04 TRIG    | GPIO 5    |
| HC-SR04 ECHO    | GPIO 19   |
| HC-SR04 VCC     | 5V        |
| HC-SR04 GND     | GND       |

---

## 🌐 API Reference

| Method | Endpoint                 | Description                       |
|--------|--------------------------|-----------------------------------|
| GET    | `/api/live-data`         | Latest reading + all KPIs         |
| GET    | `/api/analytics`         | Chart datasets                    |
| GET    | `/api/monitoring`        | Recent raw readings (paginated)   |
| GET    | `/api/leak-status`       | Run ML inference + log result     |
| GET    | `/api/leak-history`      | Recent leak log entries           |
| GET    | `/api/cost`              | Current dynamic cost estimate     |
| GET    | `/api/conservation-score`| Conservation score breakdown      |
| POST   | `/api/generate-insight`  | Gemini real-time analysis         |
| POST   | `/api/generate-report`   | Gemini daily summary report       |
| POST   | `/api/calculate-savings` | What-if savings calculator        |

---

## 🔑 Credentials You Must Set

| Credential           | Where to get it                                      |
|----------------------|------------------------------------------------------|
| `MQTT_BROKER`        | HiveMQ Cloud → Cluster URL                          |
| `MQTT_USERNAME`      | HiveMQ Cloud → Access Management                    |
| `MQTT_PASSWORD`      | HiveMQ Cloud → Access Management                    |
| `GEMINI_API_KEY`     | https://aistudio.google.com/app/apikey               |

---

## 📊 Dashboard Pages

| Page            | Content                                              |
|-----------------|------------------------------------------------------|
| Overview        | 5 KPI cards + 2 mini charts                         |
| Live Monitoring | Auto-refreshing sensor data table                   |
| Analytics       | 4 Chart.js charts (hourly, daily, tank, cost)       |
| ML Insights     | Leak prediction badge + confidence + history log    |
| AI Advisor      | Gemini insights, daily report, savings calculator   |
