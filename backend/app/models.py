from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class InteractionType(str, enum.Enum):
    MEETING = "Meeting"
    CALL = "Call"
    EMAIL = "Email"
    CONFERENCE = "Conference"
    OTHER = "Other"


class SentimentType(str, enum.Enum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"


class HCP(Base):
    __tablename__ = "hcps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    specialty = Column(String(255))
    organization = Column(String(255))
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    interactions = relationship("Interaction", back_populates="hcp")


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id"), index=True)
    interaction_type = Column(SQLEnum(InteractionType), default=InteractionType.MEETING)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    time = Column(String(50))
    attendees = Column(Text)  # JSON or comma-separated
    topics_discussed = Column(Text)
    ai_summary = Column(Text)  # LLM-generated summary
    sentiment = Column(SQLEnum(SentimentType), default=SentimentType.NEUTRAL)
    key_entities = Column(Text)  # JSON format
    outcomes = Column(Text)
    follow_up_actions = Column(Text)
    materials_shared = Column(Text)  # JSON format
    samples_distributed = Column(Text)  # JSON format
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    category = Column(String(100))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"

    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id"), index=True)
    task_description = Column(Text)
    due_date = Column(DateTime)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
