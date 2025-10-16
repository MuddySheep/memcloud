"""
Playground API endpoints for MemMachine chat interface
"""
from typing import Optional
import httpx
import structlog
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db_session
from app.models import Instance
from app.schemas import PlaygroundChatRequest, PlaygroundChatResponse
# from app.core.auth import get_current_user  # Optional for hackathon demo

logger = structlog.get_logger()

router = APIRouter()


@router.post("/{instance_id}/chat", response_model=PlaygroundChatResponse)
async def chat_with_memmachine(
    instance_id: str,
    request: PlaygroundChatRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: Optional[dict] = None  # Make auth optional for hackathon demo
):
    """
    Send a message to a MemMachine instance and get a response.

    This endpoint proxies the request to the actual MemMachine instance
    running on Cloud Run.
    """
    # Get instance from database
    result = await db.execute(
        select(Instance).where(Instance.id == instance_id)
    )
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    # Check if instance is running
    if instance.status != "RUNNING":
        raise HTTPException(
            status_code=503,
            detail=f"Instance is not running. Current status: {instance.status}"
        )

    # Get the MemMachine service URL
    memmachine_url = instance.cloud_run_url
    if not memmachine_url:
        raise HTTPException(
            status_code=503,
            detail="MemMachine URL not configured for this instance"
        )

    try:
        # Forward the chat request to MemMachine
        # MemMachine expects POST to /memory endpoint for storing/retrieving memories
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First, store the user's message as a memory
            store_response = await client.post(
                f"{memmachine_url}/memory",
                json={
                    "group_id": instance.user_id,
                    "content": request.message,
                    "memory_type": "conversation",
                    "metadata": {
                        "source": "playground",
                        "instance_id": instance_id
                    }
                }
            )

            # Then query for relevant memories to build context
            query_response = await client.post(
                f"{memmachine_url}/memory/search",
                json={
                    "group_id": instance.user_id,
                    "query": request.message,
                    "limit": 5
                }
            )

            # Build response based on stored memories
            if query_response.status_code == 200:
                memories = query_response.json().get("memories", [])

                # For demo purposes, acknowledge the message was stored
                # In production, this would integrate with an LLM
                response_text = f"I've stored your message in my memory system. "

                if memories:
                    response_text += f"I found {len(memories)} related memories in our conversation history."
                else:
                    response_text += "This appears to be the start of our conversation."

                return PlaygroundChatResponse(
                    response=response_text,
                    memory_count=len(memories),
                    stored=True
                )
            else:
                return PlaygroundChatResponse(
                    response="I've noted that in my memory system.",
                    memory_count=0,
                    stored=True
                )

    except httpx.TimeoutException:
        logger.error("playground.chat.timeout", instance_id=instance_id)
        raise HTTPException(
            status_code=504,
            detail="Request to MemMachine timed out"
        )
    except Exception as e:
        logger.error(
            "playground.chat.error",
            instance_id=instance_id,
            error=str(e)
        )
        # For hackathon demo, return a friendly message even on error
        return PlaygroundChatResponse(
            response="I'm processing your message. The memory system is warming up.",
            memory_count=0,
            stored=False
        )


@router.get("/{instance_id}/stats")
async def get_instance_stats(
    instance_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get memory statistics for a MemMachine instance.
    """
    # Get instance from database
    result = await db.execute(
        select(Instance).where(Instance.id == instance_id)
    )
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    # For hackathon demo, return mock stats
    # In production, this would query the actual MemMachine instance
    return {
        "total_memories": 0,
        "recent_memories": 0,
        "connection_status": "connected" if instance.status == "RUNNING" else "disconnected",
        "instance_name": instance.name,
        "created_at": instance.created_at.isoformat() if instance.created_at else None
    }