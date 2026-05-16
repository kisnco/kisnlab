from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.dev import build_dev_graph
from app.agents.reviewer import build_reviewer_graph, reviewer_metadata
from app.agents.state import (
    AgentRequest,
    AgentResponse,
    DevState,
    ReviewerState,
    TeamState,
    read_field,
)
from app.agents.team import build_team_graph
from app.auth import verify_token

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    dependencies=[Depends(verify_token)],
)

dev_graph = build_dev_graph()
reviewer_graph = build_reviewer_graph()
team_graph = build_team_graph(dev_graph=dev_graph, reviewer_graph=reviewer_graph)


@router.post("/dev/run", response_model=AgentResponse)
def run_dev_agent(req: AgentRequest) -> AgentResponse:
    result = dev_graph.invoke(DevState(task=req.task))
    return AgentResponse(agent="dev", response=read_field(result, "response"))


@router.post("/reviewer/run", response_model=AgentResponse)
def run_reviewer_agent(req: AgentRequest) -> AgentResponse:
    try:
        result = reviewer_graph.invoke(ReviewerState(task=req.task))
    except ValueError as exc:
        # PR ref parse error → 422 (semantic), not 500.
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return AgentResponse(
        agent="reviewer",
        response=read_field(result, "response"),
        metadata=reviewer_metadata(read_field(result, "perspectives")),
    )


@router.post("/team/run", response_model=AgentResponse)
def run_team_agent(req: AgentRequest) -> AgentResponse:
    try:
        result = team_graph.invoke(TeamState(task=req.task))
    except ValueError as exc:
        # Sub-graph parse error (e.g. reviewer PR ref) → 422.
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return AgentResponse(
        agent="team",
        response=read_field(result, "response"),
        metadata={"routed_to": read_field(result, "routed_to")},
    )
