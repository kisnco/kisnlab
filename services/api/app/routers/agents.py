from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents.dev import build_dev_graph
from app.auth import verify_token

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    dependencies=[Depends(verify_token)],
)

dev_graph = build_dev_graph()


class RunRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=8000)


class RunResponse(BaseModel):
    agent: str
    response: str


@router.post("/dev/run", response_model=RunResponse)
def run_dev_agent(req: RunRequest) -> RunResponse:
    result = dev_graph.invoke({"task": req.task, "response": ""})
    return RunResponse(agent="dev", response=result["response"])
