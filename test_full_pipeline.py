#!/usr/bin/env python3
"""
End-to-end test of the full Nomeda pipeline without real sensors.
Simulates FER + SER + STT inputs → RAG → TTS.
"""

import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.model.inference import FusionAgent

# ── Simulated test scenarios ──────────────────────────────────────────────────
TEST_CASES = [
    {
        "name": "Positive check-in",
        "face": "Happy",
        "voice": "Neutral",
        "bio": "HR: 72",
        "stt": "Hey Nomeda, I actually had a really good day today. I finished my project.",
    },
    {
        "name": "Anxiety about exams",
        "face": "Fear",
        "voice": "High Arousal",
        "bio": "HR: 95",
        "stt": "I've been feeling really anxious about my exams. I can't sleep at night.",
    },
    {
        "name": "Sadness / grief",
        "face": "Sad",
        "voice": "Sad",
        "bio": "HR: 65",
        "stt": "I lost someone close to me recently. I don't know how to cope.",
    },
    {
        "name": "Anger / frustration",
        "face": "Angry",
        "voice": "Angry",
        "bio": "HR: 110",
        "stt": "I'm so angry at my boss. He took credit for my work.",
    },
    {
        "name": "Calm gratitude",
        "face": "Neutral",
        "voice": "Neutral",
        "bio": "HR: 68",
        "stt": "Thanks for being here. Just talking helps.",
    },
]


def main():
    print("=" * 55)
    print("  NOMEDA — Full Pipeline Test")
    print("=" * 55)

    agent = FusionAgent()

    for case in TEST_CASES:
        print(f"\n{'─' * 55}")
        print(f"  Scenario: {case['name']}")
        print(f"{'─' * 55}")
        print(f"  Face: {case['face']:>10} | Voice: {case['voice']:>15} | HR: {case['bio']}")
        print(f"  User: {case['stt']}")

        t0 = time.time()
        result = agent.fuse_inputs(
            face_emotion=case["face"],
            voice_emotion=case["voice"],
            biometric=case["bio"],
            stt_text=case["stt"],
        )
        elapsed = time.time() - t0

        print(f"  ──")
        print(f"  Distress: {result['distress']}/100")
        print(f"  Nomeda:  {result['response']}")
        print(f"  ⏱ {elapsed:.2f}s")
        print()

    print("=" * 55)
    print("  Pipeline test complete.")
    print("=" * 55)


if __name__ == "__main__":
    main()
