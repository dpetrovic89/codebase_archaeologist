FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create tmp directory for clones
RUN mkdir -p tmp_repos && chmod 777 tmp_repos

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port (HF Spaces uses 7860 by default)
EXPOSE 7860

# Command to run the Gradio app
CMD ["python", "app.py"]
