FROM python:3.9-slim

WORKDIR /app
COPY . /app

RUN python -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"

RUN pip install --upgrade \
        pip
RUN pip install .
RUN pip install build
RUN python -m build

ENTRYPOINT ["python3", "-u"]
CMD [ "main.py" ]