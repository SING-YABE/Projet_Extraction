# Repository Guidelines

## Project Structure & Module Organization
- `main.py` defines the FastAPI app and wires routers.
- `routers/` contains API route modules (extraction, prediction, stats, aliments).
- `services/` holds business logic used by routers.
- `models/` contains Pydantic schemas.
- `db/` manages database setup and SQLAlchemy models.
- `ml/` stores training code and model artifacts (`ml/models/`).
- `utils/` provides configuration, logging, and shared helpers.
- Data artifacts like `prix_llm_enhanced.csv` may appear at repo root.

## Build, Test, and Development Commands
- `python -m venv venv` then `source venv/bin/activate` to create/activate a virtual environment.
- `pip install -r requirements.txt` to install dependencies.
- `createdb whatsapp_prices` to create the local PostgreSQL database.
- `uvicorn main:app --reload --host 0.0.0.0 --port 8000` to run the API in dev.
- `uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4` for production-style run.

## Coding Style & Naming Conventions
- Python style: 4-space indentation, PEP 8 conventions.
- Use `snake_case` for functions/variables, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants.
- Keep FastAPI routers focused; move heavy logic into `services/`.

## Testing Guidelines
- No automated test framework is configured in this repo.
- Use manual API checks with `curl` (see `README.md`) or the Swagger UI at `/docs`.
- If adding tests, place them under a new `tests/` directory and document how to run them.

## Commit & Pull Request Guidelines
- Recent commits use short, descriptive French phrases (e.g., “review pour …”). No strict convention is enforced.
- PRs should include a concise summary, any new environment variables, and API behavior changes.
- If you touch ML or DB behavior, include a small example request/response in the PR description.

## Security & Configuration Tips
- Configure secrets in `.env` (or `.env.local`) and never commit API keys.
- Required variables include `DATABASE_URL`, `GEMINI_API_KEY`, and `CORS_ORIGINS`.
