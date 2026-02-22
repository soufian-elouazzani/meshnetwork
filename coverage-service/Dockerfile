FROM python:3.11-slim

ENV HOME="/root"
ENV TERM=xterm
ENV PYTHONUNBUFFERED=1

# Install system dependencies (from Site Planner)
RUN apt-get update && apt-get install -y \
    build-essential \
    libbz2-dev \
    gdal-bin \
    libgdal-dev \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Site Planner repo (assuming it's in your build context)
COPY meshtastic-site-planner/ /opt/site-planner/

# Install Python dependencies from Site Planner
RUN pip install --no-cache-dir -r /opt/site-planner/requirements.txt

# Compile SPLAT! (using their build process)
WORKDIR /opt/site-planner/splat
RUN chmod +x build configure install && \
    sed -i.bak 's/-march=\$cpu/-march=native/g' build && \
    printf "8\n4\n" | ./configure && \
    ./install splat

# Compile SPLAT utilities
WORKDIR /opt/site-planner/splat/utils
RUN chmod +x build && \
    ./build all && \
    cp srtm2sdf /opt/site-planner/splat/ && \
    cp srtm2sdf-hd /opt/site-planner/splat/ 2>/dev/null || true && \
    chmod +x /opt/site-planner/splat/srtm2sdf

# Make sure all binaries are in PATH
ENV PATH="/opt/site-planner/splat:/opt/site-planner/splat/utils:${PATH}"

# Copy your daemon and requirements
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your daemon
COPY ./src/coverage_daemon.py .

# Create terrain cache directory
RUN mkdir -p /root/.splat

# Run your daemon
CMD ["python", "-u", "coverage_daemon.py"]
