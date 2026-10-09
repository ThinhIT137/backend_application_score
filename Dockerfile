FROM python:3.12-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY src/ ./src/
RUN python -c "from src.services.conversion_service import convert_to_thpt; assert convert_to_thpt('hoc_ba', 30) == 30"

FROM base AS test
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt
COPY tests/ ./tests/
ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
CMD ["python", "-B", "-m", "pytest", "-p", "no:cacheprovider", "tests", "-q"]

FROM base AS runtime
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
