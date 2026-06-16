# Project 14: Ghana Maternal & Reproductive Health — 261 Districts
# Dockerfile — reproducible computational environment (Tenet 8)

FROM python:3.11-slim

LABEL maintainer="Valentine Golden Ghanem <valentineghanem@gmail.com>"
LABEL version="1.0"
LABEL description="Spatial epidemiology & ML pipeline — Ghana maternal health, 261 districts"

# System dependencies for geospatial libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libgdal-dev \
    libproj-dev \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY scripts/ scripts/
COPY tests/ tests/
COPY docs/ docs/

# Create data directories
RUN mkdir -p data/raw data/processed outputs/data outputs/figures outputs/tables

# Default entrypoint: print usage instructions
CMD ["python", "-c", "print('Ghana Maternal Health Pipeline — Project 14\\n'\
'Usage:\\n'\
'  python scripts/01_data_cleaning.py\\n'\
'  python scripts/02_spatial_analysis.py\\n'\
'  python scripts/03_ml_pipeline.py\\n'\
'  python scripts/04_visualisations.py\\n'\
'  python scripts/build_final_dataset.py\\n'\
'  pytest tests/ -v\\n'\
'Place ghana_districts_261.geojson in data/raw/ before running.')"]
