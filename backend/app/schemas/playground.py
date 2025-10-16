"""
Playground schemas for chat interface
"""
from pydantic import BaseModel, Field
from typing import Optional


class PlaygroundChatRequest(BaseModel):
    """Request for sending a message to MemMachine"""
    message: str = Field(..., description="The message to send to MemMachine")
    context: Optional[str] = Field(None, description="Optional context for the message")


class PlaygroundChatResponse(BaseModel):
    """Response from MemMachine chat"""
    response: str = Field(..., description="The response from MemMachine")
    memory_count: int = Field(0, description="Number of related memories found")
    stored: bool = Field(True, description="Whether the message was stored successfully")