# FastApi application for leeblock.ru


* install requirenments
```
python3.12 -m venv .venv
source .venv/bin/activate

pip3 install -r requirenments.txt
```

* run redis for test
redis-server


* Run for production
gunicorn --bind=0.0.0.0:5000 --workers=4 --worker-class uvicorn.workers.UvicornWorker --threads=4 main:app


* Run test
wrk -t100 -c100 -d10s http://localhost:8000/requests/

-t12: Number of threads (12 threads in this case).
-c400: Number of concurrent connections (400 concurrent clients).
-d30s: Duration of the test (30 seconds).


* Run tests with coverage
pytest --cov=app

* View coverage reports in HTML
pytest --cov=app --cov-report=html
