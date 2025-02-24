# Use an official lightweight Python image
FROM python:3.12

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy the project files
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

# Copy Django app
COPY . .

# Expose port for Django
EXPOSE 8000

# Run the application
CMD ["python", "sell_that_sheet/manage.py", "runserver", "0.0.0.0:8000"]

