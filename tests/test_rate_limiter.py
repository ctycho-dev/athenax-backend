# test_rate_limiter.py
import httpx
import asyncio
import time

BASE_URL = "http://localhost:8000"
ENDPOINTS = [
    "/",
    "/api/v1/users/me/",
    "/api/v1/users/",
    "/public/data"
]

async def make_requests(endpoint: str, num_requests: int):
    async with httpx.AsyncClient() as client:
        successes = 0
        failures = 0
        
        for _ in range(num_requests):
            try:
                response = await client.get(f"{BASE_URL}{endpoint}")
                if response.status_code == 429:
                    failures += 1
                    # print(f"Rate limited on {endpoint}")
                else:
                    successes += 1
                    # print(f"Success on {endpoint}: {response.json()}")
            except Exception as e:
                print(f"Error: {e}")
                failures += 1
        
        print(f"\nResults for {endpoint}:")
        print(f"  Successes: {successes}")
        print(f"  Failures: {failures}")
        print(f"  Success rate: {successes/num_requests:.1%}")


async def main():
    # Test each endpoint with 120 requests (should hit limits)
    tasks = []
    for endpoint in ENDPOINTS:
        tasks.append(make_requests(endpoint, 120))
        await asyncio.sleep(0.1)  # Small delay between starting tasks
    
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
