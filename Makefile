.PHONY: setup research refresh app test snapshot
setup:
	uv sync --extra dev --python 3.12
research:
	uv run etf-pressure run --mode cached
refresh:
	uv run etf-pressure run --mode download
app:
	uv run streamlit run app.py
test:
	uv run ruff check src tests scripts app.py
	uv run pytest -q
snapshot:
	uv run etf-pressure snapshot
