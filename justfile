set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]
# Default command to list all available recipes
default:
	@just --list

# Run type checking and linting
lint:
	uv run ruff check src tests
	uv run ty check src tests

# Format code
format:
	uv run ruff format src tests

# Run tests
test:
	uv run pytest -v tests

# Build the package
build:
	uv build

# Clean up build artifacts and cache directories
clean:
	Remove-Item -Path "dist", "build", "*.egg-info", ".pytest_cache", ".mypy_cache", ".ruff_cache" -Recurse -Force -ErrorAction SilentlyContinue; exit 0
	Get-ChildItem -Path . -Filter __pycache__ -Recurse -Directory -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force; exit 0
