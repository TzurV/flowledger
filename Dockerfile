FROM python:3.12-slim

# Install Poetry
RUN pip install poetry

# Set working directory inside the container
WORKDIR /code

# Copy dependency files first (for better caching)
COPY pyproject.toml poetry.lock ./

# Install dependencies without creating a virtualenv
# Inside a container there's only one Python, so a venv adds no value
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction

# Copy the application code
COPY app ./app

# Expose the port FastAPI will listen on
EXPOSE 8000

# Start the API server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
