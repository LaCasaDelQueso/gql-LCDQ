FROM python:3.10.11-slim-buster

# install Dependencies
RUN apt-get update && apt-get install -y curl && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    apt-get remove -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Add Poetry to the PATH
ENV PATH="/root/.local/bin:$PATH"

# Set the working directory
WORKDIR /app

# Copy the pyproject.toml and poetry.lock files to the working directory
COPY pyproject.toml poetry.lock ./

# Install dependencies without dev dependencies
RUN poetry install --no-dev --no-root

# Copy the rest of the application code to the working directory
COPY . .

# Expose the correct port for Render
EXPOSE 8000

# Start the app using Render's $PORT environment variable
CMD ["poetry", "run", "python", "-m", "gqlapi.main", "serve"]