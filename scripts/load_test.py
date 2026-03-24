from locust import HttpUser, task, between, events
import time

# List of test users - each gets unique Bitrix user ID
TEST_USERS = [
    {"id": "354", "name": "Ильнур Гумеров", "question": "Что такое искусственный интеллект?"},
    {"id": "354a", "name": "Тестовый Пользователь 1", "question": "Как работает машинное обучение?"},
    {"id": "354b", "name": "Тестовый Пользователь 2", "question": "Объясни нейронные сети простым языком"},
    {"id": "354c", "name": "Тестовый Пользователь 3", "question": "Что такое GPT модель?"},
    {"id": "354d", "name": "Тестовый Пользователь 4", "question": "Расскажи про обработку естественного языка"},
    {"id": "354s", "name": "Тестовый Пользователь 5", "question": "Как создать чат-бота?"},
    {"id": "354q", "name": "Тестовый Пользователь 6", "question": "Что такое deep learning?"},
    {"id": "354w", "name": "Тестовый Пользователь 7", "question": "Объясни supervised learning"},
    {"id": "354e", "name": "Тестовый Пользователь 8", "question": "Как обучаются языковые модели?"},
    {"id": "354r", "name": "Тестовый Пользователь 9", "question": "Что такое API?"},
    {"id": "354t", "name": "Тестовый Пользователь 10", "question": "Расскажи про FastAPI"},
    {"id": "354y", "name": "Тестовый Пользователь 11", "question": "Как работает асинхронный код?"},
    {"id": "354u", "name": "Тестовый Пользователь 12", "question": "Объясни REST API"},
    {"id": "354i", "name": "Тестовый Пользователь 13", "question": "Что такое токены в LLM?"},
    {"id": "354o", "name": "Тестовый Пользователь 14", "question": "Как оптимизировать API запросы?"},
]

# Global tracking for custom metrics
request_count = 0
total_response_time = 0
response_times = []

# Event hooks for detailed logging
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Print every single request with detailed timing."""
    global request_count, total_response_time, response_times
    
    request_count += 1
    
    if exception:
        print(
            f"❌ Request #{request_count} FAILED | "
            f"Time: {response_time:.2f}ms | "
            f"Error: {exception}"
        )
    else:
        response_times.append(response_time)
        total_response_time += response_time
        avg_time = total_response_time / len(response_times)
        
        print(
            f"✅ Request #{request_count} SUCCESS | "
            f"Time: {response_time:.2f}ms | "
            f"Running Average: {avg_time:.2f}ms | "
            f"Min: {min(response_times):.2f}ms | "
            f"Max: {max(response_times):.2f}ms"
        )

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Print when test starts."""
    print("=" * 80)
    print("🚀 LOAD TEST STARTED")
    print(f"📊 Configuration: {environment.parsed_options.num_users} users, "
          f"spawn rate: {environment.parsed_options.spawn_rate}/s")
    print("=" * 80)

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print final statistics when test completes."""
    print("=" * 80)
    print("🏁 LOAD TEST COMPLETED")
    print(f"📈 Total Requests: {request_count}")
    
    if response_times:
        avg = sum(response_times) / len(response_times)
        sorted_times = sorted(response_times)
        median_idx = len(sorted_times) // 2
        median = sorted_times[median_idx]
        
        # Calculate percentiles
        p95_idx = int(len(sorted_times) * 0.95)
        p99_idx = int(len(sorted_times) * 0.99)
        
        print(f"⏱️  Average Response Time: {avg:.2f}ms")
        print(f"📊 Median Response Time: {median:.2f}ms")
        print(f"⚡ Min Response Time: {min(response_times):.2f}ms")
        print(f"🐌 Max Response Time: {max(response_times):.2f}ms")
        print(f"📈 95th Percentile: {sorted_times[p95_idx]:.2f}ms")
        print(f"📈 99th Percentile: {sorted_times[p99_idx]:.2f}ms")
    
    print("=" * 80)


class BitrixWebhookUser(HttpUser):
    # wait_time = between(2, 5)  # Wait 2-5 seconds between requests
    wait_time = between(0, 0.5)
    
    user_id = "NOT_FOUND"
    user_name = "NOT_FOUND"
    
    def on_start(self):
        """Assign unique user credentials to each simulated user."""
        if len(TEST_USERS) > 0:
            user = TEST_USERS.pop()
            self.user_id = user["id"]
            self.user_name = user["name"]
            self.question = user["question"]
            print(f"👤 User spawned: ID={self.user_id}, Name={self.user_name}")
        else:
            print('⚠️  Ran out of test users! Using default values.')
    
    @task
    def send_bitrix_message(self):
        """Simulate Bitrix webhook POST request with form data."""
        
        # Generate unique message ID for each request
        message_id = int(time.time() * 1000)
        
        # Form data matching Bitrix webhook format
        form_data = {
            'event': 'ONIMBOTMESSAGEADD',
            'data[PARAMS][MESSAGE]': self.question,
            'data[PARAMS][MESSAGE_ID]': str(message_id),
            'data[PARAMS][DIALOG_ID]': self.user_id,
            'data[USER][ID]': self.user_id,
            'data[USER][NAME]': self.user_name,
            'data[BOT][357][BOT_ID]': '357',
            'auth[domain]': 'crm.clever-trading.ru',
            'auth[member_id]': '51d813302214768af6edc537d9e3eb90',
            'auth[application_token]': '354',
        }
        
        # Track start time for this specific request
        start_time = time.time()
        
        with self.client.post(
            "/api/v1/message/bitrix/webhook",
            data=form_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            catch_response=True,
            name="Bitrix Webhook"
        ) as response:
            elapsed = (time.time() - start_time) * 1000  # Convert to ms
            
            if response.status_code == 200:
                print(f"✔️  User {self.user_id}: OpenAI completed in {elapsed:.2f}ms ({elapsed/1000:.2f}s)")
                response.success()
            elif response.status_code == 429:
                print(f"🔒 User {self.user_id}: Rate limited (429) in {elapsed:.2f}ms")
                response.failure("Rate limit hit")
            else:
                print(
                    f"✖️  User {self.user_id}: Request FAILED "
                    f"(status {response.status_code}) after {elapsed:.2f}ms"
                )
                response.failure(f"Got status code {response.status_code}")
