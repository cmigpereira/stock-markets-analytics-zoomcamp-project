FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.7.9 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY config ./config
RUN uv sync --frozen --no-dev
COPY app.py ./
COPY .streamlit ./.streamlit
COPY reports ./reports
COPY docs ./docs
EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.headless=true"]
