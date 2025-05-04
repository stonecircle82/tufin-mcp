# Stage 1: Build Environment
FROM python:3.10-slim AS builder

# Set working directory
WORKDIR /app

# Install build dependencies if any (e.g., for packages that need compilation)
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc

# Install Poetry (or pip if preferred)
# Using pip for simplicity here based on requirements.txt
# RUN pip install --upgrade pip
# RUN pip install poetry

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir --prefix="/install" -r requirements.txt

# Stage 2: Runtime Environment
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1001 python && \
    useradd --uid 1001 --gid python --shell /bin/bash --create-home python

# Copy installed dependencies from builder stage
COPY --from=builder /install /usr/local

# Copy application code
# Ensure permissions are set correctly before copying if needed
COPY ./src/app ./src/app

# Set ownership to non-root user
RUN chown -R python:python /app

# Switch to non-root user
USER python

# Expose the port the app runs on (should match MCP_PORT in .env)
# Note: This is documentation; the actual port mapping happens during `docker run`
EXPOSE 8000

# Command to run the application
# Use the host 0.0.0.0 to accept connections from outside the container
# The port here should match the EXPOSE port and the expected MCP_PORT value
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"] 