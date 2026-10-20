"""Entrypoint for local dev: `python -m backend.main`. In Docker/prod, run
uvicorn directly against backend.api.app:app instead (see Dockerfile).
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("backend.api.app:app", host="0.0.0.0", port=8000, reload=True)
