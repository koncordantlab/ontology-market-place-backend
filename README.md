# Ontology Marketplace Backend
FastAPI Server for serving the Ontology Marketplace API.

## Methodology
- Can be run as a single server or as multiple Google Cloud Run functions
- Calls are split into separate files, each able to be uploaded as individual Google Cloud Run functions
    - Auth is handled within each separate endpoint to support this

## Running as a single server
Using [uv](https://github.com/astral-sh/uv) for dependency management
```
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```


