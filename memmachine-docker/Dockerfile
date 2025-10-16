# MemMachine Custom Image with PostgreSQL Support
# CRITICAL: Install psycopg2 to .venv site-packages for MemMachine's Python to find it

FROM memmachine/memmachine:latest

USER root

# Install PostgreSQL client libraries and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# CRITICAL: Install psycopg2-binary to the EXACT location where venv Python looks
# MemMachine uses /app/.venv/bin/python which is a symlink to /usr/local/bin/python3
# But Python's sys.path includes /app/.venv/lib/python3.12/site-packages
RUN /usr/local/bin/python3 -m pip install --no-cache-dir \
    --target=/app/.venv/lib/python3.12/site-packages \
    psycopg2-binary

# Verify installation with the venv Python (the one MemMachine actually uses)
RUN /app/.venv/bin/python -c "import psycopg2; print('✅ psycopg2 installed:', psycopg2.__version__)"

# Copy startup script
COPY startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

USER appuser
WORKDIR /app

# Use startup script as entrypoint
ENTRYPOINT ["/app/startup.sh"]
