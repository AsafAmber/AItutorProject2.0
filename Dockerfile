FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch \
    && pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY material/ material/
COPY db/ db/
COPY .streamlit/config.toml .streamlit/config.toml
RUN useradd --create-home --uid 10001 tutor \
    && mkdir -p db/homework_progress \
    && chmod 700 db/homework_progress \
    && chown -R tutor:tutor db

ENV AUTO_BUILD_INDEX=1 \
    EMBED_DEVICE=cpu \
    LLM_PROVIDER=openai \
    HOMEWORK_PROGRESS_DIR=/app/db/homework_progress

USER tutor
EXPOSE 8501
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.headless=true"]
