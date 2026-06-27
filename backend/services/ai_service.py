"""
AI Service — integrates Google Gemini API for water advisor and daily reports.
"""

import logging
import google.generativeai as genai
from config import Config

logger = logging.getLogger(__name__)

# Configure Gemini once at import time
genai.configure(api_key=Config.GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-1.5-flash")


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

def _insight_prompt(flow_rate, tank_level, leak_status,
                    conservation_score, cost_info) -> str:
    return f"""
You are an expert water management advisor for a smart building system.
Analyze the following real-time water monitoring data and provide actionable advice.

## Current Readings
- Flow Rate       : {flow_rate:.2f} L/min
- Tank Level      : {tank_level:.1f}%
- Leak Status     : {leak_status}
- Conservation Score : {conservation_score}/100
- Estimated Cost  : ₹{cost_info['estimated_cost']:.4f}/min  ({cost_info['category']})
- Peak Hour Active: {cost_info['is_peak_hour']}

## Instructions
1. **Usage Analysis** — interpret the current data in plain language.
2. **Water-Saving Recommendations** — provide 3–5 specific, actionable tips.
3. **Risk Assessment** — identify any immediate risks (leak, tank depletion, high cost).
4. **Priority Actions** — list 2–3 things the user should do right now.

Keep the tone professional but friendly. Use bullet points. Max 300 words.
""".strip()


def _report_prompt(avg_flow, peak_hour, leak_incidents,
                   conservation_score, daily_data) -> str:
    return f"""
You are a water management system generating an automated daily report.

## Today's Summary Data
- Average Flow Rate   : {avg_flow:.2f} L/min
- Peak Usage Hour     : {peak_hour}:00
- Leak Incidents      : {leak_incidents}
- Conservation Score  : {conservation_score}/100
- Hourly Data Points  : {len(daily_data)} readings

## Report Requirements
Generate a structured daily report with these sections:

### 1. Executive Summary (2–3 sentences)
### 2. Usage Patterns
### 3. Leak & Safety Analysis
### 4. Cost Assessment
### 5. Recommendations for Tomorrow
### 6. Conservation Rating

Be concise, data-driven, and actionable. Max 400 words.
""".strip()


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def generate_water_insight(flow_rate: float, tank_level: float,
                            leak_status: str, conservation_score: int,
                            cost_info: dict) -> dict:
    """Call Gemini to generate a real-time water insight."""
    try:
        prompt = _insight_prompt(flow_rate, tank_level, leak_status,
                                 conservation_score, cost_info)
        response = _model.generate_content(prompt)
        return {
            "success":    True,
            "insight":    response.text,
            "type":       "real_time_insight"
        }
    except Exception as exc:
        logger.error("Gemini insight generation failed: %s", exc)
        return {
            "success": False,
            "insight": "AI advisor is temporarily unavailable. Please try again later.",
            "type":    "error"
        }


def generate_daily_report(avg_flow: float, peak_hour: str,
                           leak_incidents: int, conservation_score: int,
                           daily_data: list) -> dict:
    """Call Gemini to generate a structured daily summary report."""
    try:
        prompt = _report_prompt(avg_flow, peak_hour, leak_incidents,
                                conservation_score, daily_data)
        response = _model.generate_content(prompt)
        return {
            "success": True,
            "report":  response.text,
            "type":    "daily_report"
        }
    except Exception as exc:
        logger.error("Gemini report generation failed: %s", exc)
        return {
            "success": False,
            "report":  "Daily report generation failed. Please check your API key.",
            "type":    "error"
        }
