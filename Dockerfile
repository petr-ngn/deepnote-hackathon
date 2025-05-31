FROM python:3.13-slim

WORKDIR /app

COPY poetry.lock /app/
COPY pyproject.toml /app/

COPY src/ /app/src/
COPY config/ /app/config/
COPY app.py /app/

RUN pip install --no-cache-dir poetry
RUN poetry install --no-root

EXPOSE 8501
CMD ["poetry", "run", "streamlit", "run", "app.py", "--server.address=0.0.0"]