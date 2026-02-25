FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (e.g. for some pip packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY pyproject.toml README.md ./
# We don't have a lock file yet, so install from pyproject.toml
# Installing optional dependencies as well
RUN pip install --no-cache-dir .[all,mcp]
# Or explicitly install requirements generated
# For this quickstart, we install the package in editable mode or just dependencies

# Install the project
COPY . .
RUN pip install --no-cache-dir .
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

# Create non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "safeclaw.main:app", "--host", "0.0.0.0", "--port", "8000"]
