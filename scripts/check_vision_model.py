"""
Check and print the status of the configured Groq vision model against the live Groq models API.
"""

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from groq import Groq
from backend.config import GROQ_API_KEY, VISION_MODEL


def check_vision_model():
    client = Groq(api_key=GROQ_API_KEY)
    models = [m.id for m in client.models.list().data]
    exists = VISION_MODEL in models
    vision_matches = [m for m in models if "qwen" in m or "vision" in m]

    print(f"Configured VISION_MODEL: {VISION_MODEL}")
    print(f"Exists on Groq: {exists}")
    print(f"Available vision/Qwen models: {vision_matches}")
    return exists


if __name__ == "__main__":
    check_vision_model()
