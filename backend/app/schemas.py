from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class InteractionType(str, Enum):
    MEETING = "Meeting"
    CALL = "Call"
    EMAIL = "Email"
    CONFERENCE = "Conference"
    OTHER = "Other"


class SentimentType(str, Enum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"


# HCP Schemas
class HCPBase(BaseModel):
    name: str
    specialty: str
    organization: str
    email: EmailStr
    phone: str


class HCPCreate(HCPBase):
    pass


class HCP(HCPBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Interaction Schemas
class InteractionBase(BaseModel):
    hcp_id: int
    interaction_type: InteractionType = InteractionType.MEETING
    date: datetime
    time: str
    attendees: str
    topics_discussed: str
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None


class InteractionCreate(InteractionBase):
    raw_text: Optional[str] = None  # For chat-based input


class InteractionUpdate(BaseModel):
    interaction_type: Optional[InteractionType] = None
    time: Optional[str] = None
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    materials_shared: Optional[str] = None
    samples_distributed: Optional[str] = None


class Interaction(InteractionBase):
    id: int
    hcp_name: Optional[str] = None
    ai_summary: Optional[str] = None
    sentiment: SentimentType = SentimentType.NEUTRAL
    key_entities: Optional[str] = None
    materials_shared: Optional[str] = None
    samples_distributed: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Material Schemas
class MaterialBase(BaseModel):
    name: str
    category: str
    description: str


class MaterialCreate(MaterialBase):
    pass


class Material(MaterialBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Chat Message Schema
class ChatMessage(BaseModel):
    user_id: Optional[str] = None
    message: str
    interaction_data: Optional[dict] = None


class ChatResponse(BaseModel):
    response: str
    suggested_tools: List[str] = []
    interaction_id: Optional[int] = None


# Extraction Schema (for LangGraph orchestration)
class ExtractionRequest(BaseModel):
    message: str
    hcp_context: Optional[dict] = None


# AI Summary Schema
class AISummaryRequest(BaseModel):
    raw_text: str
    interaction_type: InteractionType


class AISummaryResponse(BaseModel):
    summary: str
    sentiment: SentimentType
    key_entities: dict
    follow_up_suggestions: List[str]
