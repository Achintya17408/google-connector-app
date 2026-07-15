import os
import json
import uuid

import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="set RUN_INTEGRATION_TESTS=1 with PostgreSQL available",
)


def test_health_auth_and_route_protection():
    from app.api.main import app

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        preflight = client.options(
            "/chat",
            headers={
                "Origin": "https://google-agent-preview.vercel.app",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == (
            "https://google-agent-preview.vercel.app"
        )
        assert client.post(
            "/chat", json={"message": "hi", "session_id": "test"}
        ).status_code == 401
        token = client.post(
            "/auth/token", json={"email": "user@example.com"}
        ).json()["access_token"]
        assert client.get(
            "/admin/prompts", headers={"Authorization": f"Bearer {token}"}
        ).status_code == 403
        admin = client.post(
            "/auth/token", json={"email": "achintyat256@gmail.com"}
        ).json()["access_token"]
        response = client.get(
            "/admin/prompts", headers={"Authorization": f"Bearer {admin}"}
        )
        assert response.status_code == 200
        assert len(response.json()["prompts"]) >= 2


def test_feedback_preserves_retrieved_context():
    from app.api.main import app
    from app.db.connection import get_pool

    session_id = f"feedback-test-{uuid.uuid4()}"
    context = [{"source": "gmail", "content": "Budget meeting", "score": 0.9}]

    with TestClient(app) as client:
        token = client.post(
            "/auth/token", json={"email": "user@example.com"}
        ).json()["access_token"]

        async def seed_and_read(read=False):
            pool = await get_pool()
            async with pool.acquire() as conn:
                if read:
                    return await conn.fetchval(
                        "SELECT retrieved_docs FROM feedback WHERE session_id=$1",
                        session_id,
                    )
                await conn.execute(
                    """INSERT INTO conversation_history
                       (session_id,user_id,role,content)
                       VALUES($1,'user@example.com','user','What is the budget?')""",
                    session_id,
                )
                await conn.execute(
                    """INSERT INTO conversation_history
                       (session_id,user_id,role,content,tool_results)
                       VALUES($1,'user@example.com','assistant','It is in the email.',
                              $2::jsonb)""",
                    session_id,
                    json.dumps(context),
                )
        client.portal.call(seed_and_read)
        response = client.post(
            "/feedback",
            json={"session_id": session_id, "rating": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "recorded"}
        assert json.loads(client.portal.call(seed_and_read, True)) == context
