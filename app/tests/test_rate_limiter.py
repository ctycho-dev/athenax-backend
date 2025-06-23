import httpx
import time
from datetime import datetime


# ----------------------------
# Configuration
# ----------------------------

BASE_URL = "http://localhost:8000/api/v1"  # change if needed
AUTH_TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IlUtMGJ1Y3U0VjJEUkZoTTJRN1VERTZCYXlKWWpwTFJ4enFDZGlKNUFQN2sifQ.eyJzaWQiOiJjbWFqYmV0ajQwMDQwankwbWE4MGFnZmp5IiwiaXNzIjoicHJpdnkuaW8iLCJpYXQiOjE3NDY5NDc0NTgsImF1ZCI6ImNtOTV0Z2JtMDAxbG5rdjBrODN3c2NrZDMiLCJzdWIiOiJkaWQ6cHJpdnk6Y205ZmxyYjZuMDBnY2xkMG11MWR5bnkwYyIsImV4cCI6MTc0Njk1MTA1OH0.p5b8E9gAEq2Ci4ivv-hBTiU6m7qQW4UDYqsvFuZB7c0ZZhqVTrz_uwYbbZLV0SIm70VMbLhMSeNOcUx6oWk7pQ"

# List of endpoints to test
ENDPOINTS = [
    # {
    #     "path": "/health",
    #     "method": "GET",
    #     "calls": 10
    # },
    # {
    #     "path": "/api/v1/users/me/",
    #     "method": "GET",
    #     "calls": 15,
    # },
    # {
    #     "path": f"/s3/{'audit-form'}",
    #     "method": "POST",
    #     "calls": 7,
    #     "is_upload": True
    # },
    # Wishlist endpoints
    {
        "path": "/wishlist/",
        "method": "GET",
        "calls": 2,
        "rate_limit": "100/minute",  # optional, for logging only
    },
    {
        "path": "/wishlist/",
        "method": "POST",
        "calls": 6,
        "rate_limit": "5/minute",
        "body": {"email": "user@example.com"},
    },
    # Audit endpoints
    {
        "path": "/api/v1/audit/",
        "method": "GET",
        "calls": 2,
        "rate_limit": "100/minute",
    },
    {
        "path": "/api/v1/audit/invalid_id",
        "method": "GET",
        "calls": 3,
        "expect_status": 404
    },
    {
        "path": "/api/v1/audit/valid_id",
        "method": "PATCH",
        "calls": 6,
        "rate_limit": "5/minute",
        "body": {"name": "Updated Name"}
    },
    # {
    #     "path": "/api/v1/audit/download/",
    #     "method": "POST",
    #     "calls": 2,
    #     "body": {"bucket": "test-bucket", "key": "test-file.txt", "original_filename": "file.txt"}
    # }
]

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}"
}

# ----------------------------
# Request Sender
# ----------------------------

def send_request(client, endpoint):
    method = endpoint["method"].lower()
    url = f"{BASE_URL}{endpoint['path']}"

    kwargs = {
        "url": url,
        "headers": HEADERS
    }

    if endpoint.get("is_upload"):
        # Mimic multipart/form-data upload without actual file
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        kwargs["headers"]["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        kwargs["content"] = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="fake.txt"\r\n'
            f"Content-Type: text/plain\r\n\r\n\r\n"
            f"--{boundary}--\r\n"
        )

    if endpoint.get("body") and method == "post":
        kwargs["headers"]["Content-Type"] = "application/json"
        kwargs["json"] = endpoint["body"]

    try:
        response = getattr(client, method)(**kwargs)
        return response
    except Exception as e:
        print(f"Error sending request: {e}")
        return None


# ----------------------------
# Main Test Runner
# ----------------------------

def run_tests():
    with httpx.Client(timeout=10) as client:
        for idx, endpoint in enumerate(ENDPOINTS, start=1):
            path = endpoint["path"]
            method = endpoint["method"]
            total_calls = endpoint.get("calls", 1)
            expected_status = endpoint.get("expect_status")
            rate_limit = endpoint.get("rate_limit")

            print(f"\n[{idx}] Testing {method} {path}")
            print(f"  ➤ Making {total_calls} requests")

            too_many_requests_count = 0
            success_count = 0
            error_count = 0

            for i in range(1, total_calls + 1):
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"  [{i}/{total_calls}] {timestamp}", end="... ")

                response = send_request(client, endpoint)

                if not response:
                    print("Request failed ❌")
                    error_count += 1
                    continue

                status_code = response.status_code
                try:
                    json_resp = response.json()
                except Exception:
                    json_resp = {}

                # Handle detail message if present
                if isinstance(json_resp, dict):
                    detail = json_resp.get("detail", "")
                elif isinstance(json_resp, list):
                    detail = f"List with {len(json_resp)} items returned"
                else:
                    detail = "Unknown response format"

                if status_code == 429:
                    print("429 Too Many Requests 🚫")
                    too_many_requests_count += 1
                elif expected_status and status_code != expected_status:
                    print(f"{status_code} | Expected {expected_status} ❌")
                    error_count += 1
                else:
                    print(f"{status_code} | {detail} ✅")
                    success_count += 1

                print(f"{response.status_code} | {detail}")

                time.sleep(.5)

    print("\n✅ All tests completed.")


# ----------------------------
# Run It
# ----------------------------

if __name__ == "__main__":
    run_tests()