import os
import requests
import logging

logger = logging.getLogger(__name__)

MODERATION_URL = os.environ.get("MODERATION_API_URL", "")


def check_moderation(text: str, topic_context: str = None) -> dict:
    if not MODERATION_URL:
        # Moderation is disabled; default to pass
        return {
            "status": "pass",
            "similarity_score": None,
            "classification_score": None,
        }

    payload = {"message": text}
    if topic_context:
        payload["topic_context"] = topic_context

    try:
        response = requests.post(MODERATION_URL, json=payload, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Moderation API request failed: {e}")
        return {
            "status": "delete",
            "reason": "Moderation API unavailable at this time.",
            "similarity_score": None,
            "classification_score": None,
        }
