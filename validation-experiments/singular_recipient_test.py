import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")

CALLE_API_KEY = os.environ.get("CALLE_API_KEY", "")
CALLE_API_BASE_URL = os.environ.get("CALLE_API_BASE_URL", "https://api.heycall-e.com").rstrip("/")

if not CALLE_API_KEY:
    raise SystemExit(
        "CALLE_API_KEY not found. This script reads the same .env file the "
        "production app uses — make sure you're running this from the "
        "careflow-ai project root, or that careflow-ai/.env exists and has "
        "a real key set."
    )

TASK_PROMPT = (
    "You are calling the recipient for a controlled engineering validation "
    "test. This is NOT a real patient call. It is important that you obtain "
    "a clear, unambiguous answer to EVERY question below before ending the "
    "call — if an answer is unclear, ask a brief follow-up to clarify it "
    "rather than moving on. Ask the following questions, one at a time, in "
    "a natural conversational order:\n"
    "- On a scale of 0 to 10, how would you rate your pain right now?\n"
    "- Have you had a fever since you got home?\n"
    "- Were you able to pick up all of your prescribed medications?\n"
    "- Have you been taking your medications as prescribed?\n"
    "- Are you experiencing any unexpected bleeding?\n"
    "- Have you noticed any unusual swelling?\n"
    "- Are you having any difficulty breathing?\n"
    "- Overall, how would you describe how your recovery is going?"
)

RESULT_SCHEMA = {
    "type": "object",
    "required": [
        "pain_level", "fever", "medication_collected", "medication_taken",
        "bleeding", "swelling", "difficulty_breathing", "general_recovery",
    ],
    "properties": {
        "pain_level": {"type": "number"},
        "fever": {"type": "boolean"},
        "medication_collected": {"type": "boolean"},
        "medication_taken": {"type": "boolean"},
        "bleeding": {"type": "boolean"},
        "swelling": {"type": "boolean"},
        "difficulty_breathing": {"type": "boolean"},
        "general_recovery": {"type": "string"},
    },
    "additionalProperties": False,
}


def build_payload(phone_number: str) -> dict:
    return {
        "task": TASK_PROMPT,
        "recipient": {"phone": phone_number},
        "result_schema": RESULT_SCHEMA,
        "metadata": {
            "experiment": "singular_recipient_validation",
            "variant": "singular_recipient_no_region_locale",
        },
    }


def place_call(payload: dict, idempotency_key: str) -> dict:
    headers = {
        "Authorization": f"Bearer {CALLE_API_KEY}",
        "Content-Type": "application/json",
        "Idempotency-Key": idempotency_key,
    }
    response = requests.post(f"{CALLE_API_BASE_URL}/v1/calls", json=payload, headers=headers, timeout=30)
    result = {
        "http_status_code": response.status_code,
        "ok": response.ok,
    }
    try:
        result["body"] = response.json()
    except ValueError:
        result["body"] = response.text
    return result


def poll_until_terminal(call_id: str, max_wait_seconds: int = 600, poll_interval_seconds: int = 10) -> dict:
    headers = {"Authorization": f"Bearer {CALLE_API_KEY}"}
    waited = 0
    while waited < max_wait_seconds:
        response = requests.get(f"{CALLE_API_BASE_URL}/v1/calls/{call_id}", headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        status = data.get("status")
        print(f"  [{waited}s] status = {status}")
        if status in ("completed", "failed"):
            return data
        time.sleep(poll_interval_seconds)
        waited += poll_interval_seconds
    raise TimeoutError(f"Call {call_id} did not reach a terminal status within {max_wait_seconds}s")


def main():
    phone_number = input("Enter the phone number to call (E.164 format, e.g. +234...): ").strip()
    if not phone_number.startswith("+"):
        raise SystemExit("Phone number must be in E.164 format, starting with +")

    payload = build_payload(phone_number)

    print("\n" + "=" * 60)
    print("SINGULAR RECIPIENT VALIDATION — single real call")
    print("=" * 60)
    print("Request body about to be sent:")
    print(json.dumps(payload, indent=2))
    print(
        "\nNote: 'region' and 'locale' are intentionally absent from the "
        "recipient object above — this is the experimental condition being "
        "tested, not a missing value."
    )

    confirm = input("\nType 'yes' to actually place this REAL call now (rings the phone, spends 1 credit): ").strip().lower()
    if confirm != "yes":
        print("Not confirmed. No call placed. Exiting.")
        return

    idempotency_key = f"careflow_validation_singular_recipient_{int(time.time())}"
    creation_result = place_call(payload, idempotency_key)

    creation_output_path = SCRIPT_DIR / "singular_recipient_creation_response.json"
    with open(creation_output_path, "w") as f:
        json.dump(creation_result, f, indent=2)
    print(f"\nCreation response (HTTP {creation_result['http_status_code']}) saved to {creation_output_path}")
    print(json.dumps(creation_result, indent=2))

    if not creation_result["ok"]:
        print(
            "\nRequest was REJECTED by CALL-E. This is itself a valid, "
            "reportable experimental outcome (see interpretation guide) — "
            "not a script failure. No call was placed; no further polling "
            "will occur."
        )
        return

    call_id = creation_result["body"].get("id")
    if not call_id:
        print("\nUnexpected: request succeeded but no 'id' field was found in the response body. Stopping.")
        return

    print(f"\nCall created: id={call_id}")
    print("Polling until terminal (this will take a few minutes)...")

    final_result = poll_until_terminal(call_id)

    final_output_path = SCRIPT_DIR / "singular_recipient_final_result.json"
    with open(final_output_path, "w") as f:
        json.dump(final_result, f, indent=2)
    print(f"\nFull final result saved to {final_output_path}")
    print(json.dumps(final_result, indent=2))


if __name__ == "__main__":
    main()
