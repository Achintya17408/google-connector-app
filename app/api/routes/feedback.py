import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.db.connection import get_pool

router = APIRouter()


class FeedbackRequest(BaseModel):
    session_id: str
    rating: int


@router.post("/feedback")
async def feedback(req: FeedbackRequest, request: Request):
    if req.rating not in (-1, 1):
        raise HTTPException(422, "rating must be +1 or -1")
    pool = await get_pool()
    async with pool.acquire() as conn, conn.transaction():
        assistant = await conn.fetchrow(
            """SELECT content,created_at,tool_results FROM conversation_history
               WHERE session_id=$1 AND role='assistant'
               ORDER BY created_at DESC LIMIT 1""",
            req.session_id,
        )
        if not assistant:
            raise HTTPException(404, "No assistant response found for session")
        question = await conn.fetchval(
            """SELECT content FROM conversation_history
               WHERE session_id=$1 AND role='user' AND created_at <= $2
               ORDER BY created_at DESC LIMIT 1""",
            req.session_id,
            assistant["created_at"],
        )
        assignment = await conn.fetchrow(
            """SELECT id,prompt_id FROM prompt_assignments
               WHERE session_id=$1 ORDER BY assigned_at DESC LIMIT 1""",
            req.session_id,
        )
        retrieved_docs = assistant["tool_results"] or []
        if isinstance(retrieved_docs, str):
            retrieved_docs = json.loads(retrieved_docs)
        await conn.execute(
            """INSERT INTO feedback
               (session_id,user_id,user_question,agent_response,retrieved_docs,
                rating,prompt_id,assignment_id)
               VALUES($1,$2,$3,$4,$5::jsonb,$6,$7,$8)""",
            req.session_id,
            request.state.user_id,
            question,
            assistant["content"],
            json.dumps(retrieved_docs, default=str),
            req.rating,
            assignment["prompt_id"] if assignment else None,
            assignment["id"] if assignment else None,
        )
    return {"status": "recorded"}
