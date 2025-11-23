[![CI - API & Webhook Tests](https://github.com/ZaatourRim/backend-api-webhook-tests/actions/workflows/tests.yml/badge.svg)](https://github.com/ZaatourRim/backend-api-webhook-tests/actions/workflows/tests.yml)

# Backend Test Automation Suite  
### Backend REST & Webhook API Test Automation Suite (Python + Pytest)

This project implements a small but realistic backend automation test suite covering:

- REST API testing (Reqres.in) 
- Webhook delivery validation (Webhook.site)
- Clean project structure  
- Configuration management  
- Logging & error handling  
- CI integration  
- HTML test reports  

All tests are implemented in **Python & Pytest** with reusable API clients, structured configuration and a clear test design.

---

## Tech Stack

- **Python 3.9+**
- **Pytest** – testing framework  
- **Requests** – HTTP client  
- **JSONSchema** – response validation  
- **pytest-html** – HTML report generation  
- **GitHub Actions** – CI pipeline  
- **Webhook.site** – webhook capture endpoint  

---
## Project Structure
```bash

project/
│
├─ config/
│ └─ settings.yaml
│
├─ utils/
│ ├─ api_client.py
│ ├─ webhook_utils.py
│ ├─ json_schemas.py
│ └─ config.py
│
├─ tests/
│ ├─ test_api_workflow.py
│ ├─ test_webhook_validation.py
│ └─ conftest.py
│
├─ .github/workflows/tests.yml
├─ pytest.ini
├─ requirements.txt
└─ README.md
```
---
# Setup & Run Instructions

### 1. Create a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate (for macOS and Linux)
````
### 2. Install dependencies
```bash
pip install -r requirements.txt
````
### 3. Export required environment variables
Reqres API token (public demo key)
```bash
export REQRES_API_TOKEN=reqres-free-v1
````
Go to https://webhook.site -> copy your unique URL:
```bash
export WEBHOOK_TARGET_URL="https://webhook.site/<your-uuid>"
````
### 4. Run the entire test suite
in Root directory run:
```bash
pytest -v
````
### 5. Run Tests & Generate HTML test report
in Root directory run:
```bash
pytest -v --html=reports/test_report.html --self-contained-html
````
The HTML report will appear in reports/, folder will be created if not existing, and overridden with new runs of tests.

---
# Test Suite overview:

### 1. API Workflow Tests (tests/test_api_workflow.py)
What's covered:

- GET single user (success)
- POST user creation
- DELETE user
- negative tests.
    - non-existent IDs (404)
    - invalid login payloads (400)
- JSONSchema validation of responses (for core requests)
- parametrized tests (@pytest.mark.parametrize) for data-driven negative tests

other few design features:

- Assertions stay only in the tests, not in client
- sharing ApiClient as a session scoped fixture (in /tests/conftest.py)
- schema validation for catching structural regressions


### 2. Webhook validation, end to end Test (tests/test_webhook_validation.py)
This test sends an event to webhook.site then retrieves is using their API, it follows this workflow:

1. build payload with:
    - unique event_id
    - nested data (dict)
    - custom field x-request-time (UTC ISOFORMAT)
2. send POST to webhook.site
3. Polls webhook.site API up to 5 times for the latest captured request
4. Asserts:
    - event_id matches
    - payload matches expectations
    - timestamp is valid, UTC timezoned and not older than 2 minutes

The test retry up to 5 times to handle the asynchronous webhook and avoid flaky tests.

---
# Architecture & Design:

### ApiClient

Responsibilities:

- Build request URLs
- merge default & per-call headers
- API token injection via x-api-key
- Log request details live (method, URL, payload, elapsed time)
- Wrap network issues in ApiClientError

Why this structure?

- Avoids duplicate code in tests
- Easy to grow test and share repo with a team
- Enables clear troubleshooting via logs
- Keeps test assertions separated from the HTTP Client features

### WebhookClient (webhook sending and retrieval)
Responsibilities:

- Post events to Webhook.site
- Retrieves latest request via Webhook.site API
- handles 404 when no webhook arrived yet
- Wrap failures in WebhookClientError
- Decode Webhook.site "content" field into JSON


Why this structure?

- Webhook delivery is asynchronous, and Webhook.site sometimes takes a moment to store the request.
Putting this logic here keeps the test itself simple and easier to understand.
---
# Risk base test deisgn decisions
### Decision: Use JSONSchema only where structural risk is high
I added schema validation for:
- GET user response
- POST create user response
- Error payloads

Not for simple 204 responses like DELETE, because regressions are more likely in complex objects like creating a user (POST) and GET user.

### Decision: Poll Webhook.site instead of assuming synchronous delivery
Prevents flakiness and reflects how real webhook systems behave

### Decision: Treat Webhook.site 404 as “no event yet” and not as failure

Failing immediately here would create unnecessary flakiness.

# Trade-Offs & Improvements
### Implemented

- Clean, reusable clients instead of over-fitted abstractions
- Detailed logging for debugging and CI visibility
- Timeout handling to prevent hanging tests
- Polling strategy for asynchronous webhook reliability

### What could be improved with more time

- Import OpenAPI schema for stricter contract-level validation
- Move polling logic into the WebhookClient
- Add Allure reporting (richer UI than pytest-html)
- Add parallel test execution
- Additional test data factories if the API were more complex


# About

This repository is a compact example of designing a reliable backend test framework, including:
- clean architecture
- extensibility
- error handling
- asynchronous webhook validation
- CI-friendly execution