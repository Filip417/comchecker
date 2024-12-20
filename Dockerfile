# Set the Python version as a build-time argument 
ARG PYTHON_VERSION=3.12-slim-bullseye
FROM python:${PYTHON_VERSION}

# Create a virtual environment
RUN python -m venv /opt/venv

# Set the virtual environment as the current PATH
ENV PATH=/opt/venv/bin:$PATH

# Upgrade pip
RUN pip install --upgrade pip

# Set Python-related environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install OS dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    libjpeg-dev \
    libcairo2 \
    chromium \
    chromium-driver \
    fonts-noto-color-emoji \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create the application directory
RUN mkdir -p /code

# Set the working directory
WORKDIR /code

# Copy requirements file into the container
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install -r /tmp/requirements.txt

# Copy the project code into the container
COPY ./src /code

# Set the Django default project name
ARG PROJ_NAME="comchecker"

# Create a startup script for runtime operations
RUN printf "#!/bin/bash\n" > ./start.sh && \
    printf "RUN_PORT=\"\${PORT:-8000}\"\n" >> ./start.sh && \
    printf "python manage.py wait_for_db\n" >> ./start.sh && \
    printf "python manage.py migrate --no-input\n" >> ./start.sh && \
    printf "python manage.py runcrons\n" >> ./start.sh && \
    printf "gunicorn ${PROJ_NAME}.wsgi:application --bind \"0.0.0.0:\$RUN_PORT\"\n" >> ./start.sh

# Make the startup script executable
RUN chmod +x start.sh

# Clean up apt cache to reduce image size
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Command to run the application
CMD ["./start.sh"]
