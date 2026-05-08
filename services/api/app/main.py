from fastapi import FastAPI

from app.routers import agents

app = FastAPI(title="KisnLab API", version="0.2.0")

app.include_router(agents.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
