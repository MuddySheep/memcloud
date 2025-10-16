# Custom MemMachine Image with PostgreSQL Support
# NUCLEAR OPTION: Install to SYSTEM Python since .venv is just symlinks

FROM memmachine/memmachine:latest

USER root

# Install PostgreSQL client libraries FIRST
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# DEBUG: Find where everything is
RUN echo "=== DEBUGGING ===" && \
    which python3 && \
    which pip3 && \
    python3 --version && \
    python3 -c "import sys; print('Python path:', sys.executable)" && \
    pip3 --version

# NEW STRATEGY: Install psycopg2 to BOTH system AND venv locations
# This ensures it's available no matter which Python is used

# First, find the REAL Python that .venv/bin/python points to
RUN echo "=== Finding real Python ===" && \
    ls -la /app/.venv/bin/python* && \
    readlink -f /app/.venv/bin/python && \
    /usr/local/bin/python3 -c "import sys; print('System Python:', sys.executable, sys.path)"

# Install to .venv site-packages using the REAL system Python
RUN /usr/local/bin/python3 -m pip install --no-cache-dir \
    --target=/app/.venv/lib/python3.12/site-packages \
    psycopg2-binary

# VERIFY with the venv Python (the one that will actually run)
RUN /app/.venv/bin/python -c "import sys; print('Venv Python sys.path:', sys.path)" || true
RUN /app/.venv/bin/python -c "import psycopg2; print('✅ psycopg2 installed and ACCESSIBLE from venv:', psycopg2.__version__)"

# Copy startup script
COPY startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

ENTRYPOINT ["/app/startup.sh"]
