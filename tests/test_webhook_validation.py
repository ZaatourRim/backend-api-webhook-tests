from datetime import datetime, timezone
from uuid import uuid4
import time
import pytest

def test_e2e_timestamp_delivery_and_validation(webhook_client):

    # 1. build payload with current UTC timestamp
    now_utc = datetime.now(timezone.utc)
    event_id = str(uuid4())

    payload = {
        "event": "qa_automation_test",
        "event_id": event_id,
        "data": {
            "source": "pytest",
            "description": "Webhook validation end-to-end"
        },
        "x-request-time": now_utc.isoformat()
    }

    # 2. send POST to webhook URL
    post_response = webhook_client.send_event(payload=payload)

    assert 200 <= post_response.status_code < 300, (f"unexpected status code from webhook: {post_response.status_code}, body: {post_response.text}")

    # 3. Ping webhook.site API briefly for the latest request
    latest_body = None
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        latest_body = webhook_client.retrieve_latest_request_content()
        # check if it is our event (matching event_id)
        if latest_body.get("event_id") == event_id:
            break
        # if not , wait a bit before retrying
        time.sleep(1)

    assert latest_body is not None, "Did not receive any webhook request body"
    assert latest_body.get("event_id") == event_id, (f"Latest webhook request does not match our event_id, body was: {latest_body}")

    # 4. validate some fields in the payload
    assert latest_body.get("event") == "qa_automation_test"
    assert "data" in latest_body and isinstance(latest_body["data"], dict)
   
    # 5. validate x-request-time field not older than 2 minutes

    # ensure x-request-time field exists, is a valid timestamp, and is timezoned UTC
    assert "x-request-time" in latest_body, "Missing 'x-request-time' in webhook payload"
    ts_str = latest_body["x-request-time"]
    try:
        ts = datetime.fromisoformat(ts_str)
    except ValueError as exp:
        pytest.fail(f"x-request-time is not a valid ISO timestamp: {ts_str}, error: {exp}")
    
    if ts.tzinfo is None:
        pytest.fail("x-request-time must be timezone aware: include UTC offset")

    ts_utc = ts.astimezone(timezone.utc)

    now_after = datetime.now(timezone.utc)
    req_age_seconds = (now_after - ts_utc).total_seconds()

    # Validate if age is non negative and not older than 2 minutes (120 seconds)
    assert 0 <= req_age_seconds <= 120, (
        f"x-request-time too old: age={req_age_seconds} seconds."
        f"Event sent at {ts_str}, received at: {now_after.isoformat()}"
        )
    
    


