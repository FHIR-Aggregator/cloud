# Builder stage
FROM python:3.12 AS builder

# Install necessary packages
RUN apt-get update && \
    apt-get install -y vim curl jq && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements.txt
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.12


# Set the working directory
WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the application code
COPY . .

# Expose the port on which the server will listen
EXPOSE 8080

# Command to run the application using Uvicorn
CMD ["uvicorn", "fhir_proxy.proxy:app", "--host", "0.0.0.0", "--port", "8080"]
