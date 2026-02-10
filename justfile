# Run tests
test *args:
    uv run pytest tests/ {{args}}

# Run tests with verbose output
test-v *args:
    uv run pytest tests/ -v {{args}}

# Start dev server (hot reload enabled)
dev:
    uv run python main.py

# Build Docker image
build:
    docker build -t bathymetry-tool .

# Start container
up: build
    docker run -p 8000:8000 bathymetry-tool

# Start container in background
up-d: build
    docker run -d --name bathymetry -p 8000:8000 bathymetry-tool

# Stop background container
down:
    docker stop bathymetry && docker rm bathymetry

# Run the Spirit pipeline extraction script
spirit:
    uv sync --extra spirit
    uv run python extract_bathymetry.py
