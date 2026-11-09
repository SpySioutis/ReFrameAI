from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..ai.muse_spark import MuseSparkProvider
from ..db import get_db
from ..models import Project, User
from ..schemas import AssistantRequest, AssistantResponse
from .deps import current_user

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantResponse)
def chat(body: AssistantRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    context = ""
    if body.project_id:
        project = db.get(Project, body.project_id)
        if project and project.user_id == user.id:
            context = (f"project={project.name} duration={project.duration:.1f}s "
                       f"fps={project.fps:.1f} res={project.resolution}")
    provider = MuseSparkProvider()
    last_user = next((m.content for m in reversed(body.messages) if m.role == "user"), "")
    plan = provider.plan(last_user, context=context)
    if plan.needs_clarification:
        return AssistantResponse(reply=plan.question or "Could you clarify the target object and operation?",
                                 plan={"operation": plan.operation, "target": plan.target},
                                 suggested_tool=None)
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    try:
        reply = provider.chat(messages, context=context)
    except Exception as e:
        reply = f"The AI planner is unavailable: {e}"
    return AssistantResponse(
        reply=reply,
        plan={"operation": plan.operation, "target": plan.target, "prompt": plan.prompt, "args": plan.args},
        suggested_tool=plan.tool,
    )
