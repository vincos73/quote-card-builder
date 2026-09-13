# Cloud Run-ready image for the single Quote Card Builder MCP service.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --create-home app

COPY requirements-mcp.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements-mcp.txt

COPY scripts/mcp_server.py \
     scripts/mcp_quote_card.py \
     scripts/mcp_app.py \
     scripts/render_quote_card.py \
     scripts/quote_card_contract.py \
     scripts/rasterize.py \
     ./scripts/
COPY assets/card-editor/vincos-lockup-white.svg ./assets/card-editor/
COPY assets/card-editor/quote-card-builder-wordmark.svg ./assets/card-editor/
COPY assets/card-editor/fonts/ ./assets/card-editor/fonts/

USER app
EXPOSE 8080

CMD ["python", "scripts/mcp_server.py", "--transport", "streamable-http", "--host", "0.0.0.0"]
