import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

load_dotenv()

API_KEY = os.getenv("LLM_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

if not API_KEY:
    raise RuntimeError("LLM_API_KEY is not configured.")

client = genai.Client(api_key=API_KEY)


class Diagnosis(BaseModel):
    risk_level: str = Field(description="LOW, MEDIUM, or HIGH")
    likely_cause: str
    recommended_recovery_strategy: str
    explanation: str
    confidence: int = Field(ge=0, le=100)


def analyze_transaction(tx):
    """Gemini is diagnosis-only. It never authorizes or executes a payment action."""
    prompt = f"""
You are the diagnosis layer of RecoverAI, an AI-powered revenue recovery system.

Analyze this synthetic payment transaction:
- Transaction ID: {tx.transaction_id}
- Amount: INR {tx.amount:.2f}
- Status: {tx.status}
- Failure reason: {tx.failure_reason or 'none'}
- Attempt count: {tx.attempt_count}
- Previous successful payments: {tx.previous_successes}

Return a concise diagnostic assessment with:
1. Risk level: LOW, MEDIUM, or HIGH
2. Likely cause
3. Recommended recovery strategy
4. Short explanation
5. Confidence from 0 to 100

Safety rules:
- Diagnose only. Never claim money was recovered.
- Do not authorize, initiate, or execute payments.
- Do not invent transaction facts.
- The deterministic policy engine decides the final action.
"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=Diagnosis,
            ),
        )
        diagnosis = response.parsed
        if diagnosis is None:
            diagnosis = Diagnosis.model_validate_json(response.text)

        return {
            "success": True,
            "model": MODEL_NAME,
            "diagnosis": diagnosis.model_dump(),
        }
    except Exception as exc:
        return {
            "success": False,
            "model": MODEL_NAME,
            "analysis": "Gemini analysis unavailable.",
            "error": str(exc),
        }
