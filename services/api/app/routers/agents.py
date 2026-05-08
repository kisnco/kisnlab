from fastapi import APIRouter, Depends

from app.agents.dev import build_dev_graph
from app.agents.state import AgentRequest, AgentResponse, DevState
from app.auth import verify_token

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    dependencies=[Depends(verify_token)],
)

dev_graph = build_dev_graph()


@router.post("/dev/run", response_model=AgentResponse)
def run_dev_agent(req: AgentRequest) -> AgentResponse:
    result = dev_graph.invoke(DevState(task=req.task))
    response_text = result["response"] if isinstance(result, dict) else result.response
    return AgentResponse(agent="dev", response=response_text)
