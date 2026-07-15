"""
LangGraph Tools for AI-First CRM HCP Module
Implements 5+ tools for sales-related activities with HCPs
"""

from typing import Optional
import json
from datetime import datetime
from sqlalchemy.orm import Session
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import Interaction, HCP, Material
from services.groq_service import GroqService

groq_service = GroqService()


def _parse_date(date: str) -> datetime:
    """Parse ISO date strings, including trailing Z."""
    normalized = date.replace("Z", "+00:00") if date.endswith("Z") else date
    return datetime.fromisoformat(normalized)


def _build_raw_text(
    topics_discussed: str,
    attendees: str,
    raw_text: Optional[str] = None,
    outcomes: Optional[str] = None,
    follow_up_actions: Optional[str] = None,
) -> str:
    if raw_text and raw_text.strip():
        return raw_text.strip()

    parts = [
        f"Topics: {topics_discussed}" if topics_discussed else None,
        f"Attendees: {attendees}" if attendees else None,
        f"Outcomes: {outcomes}" if outcomes else None,
        f"Follow-up: {follow_up_actions}" if follow_up_actions else None,
    ]
    return "\n".join(part for part in parts if part)


class InteractionTools:
    """Tools for managing HCP interactions"""

    @staticmethod
    def log_interaction(
        hcp_id: int,
        interaction_type: str,
        date: Optional[str] = None,
        time: Optional[str] = None,
        attendees: Optional[str] = None,
        topics_discussed: Optional[str] = None,
        raw_text: Optional[str] = None,
        outcomes: Optional[str] = None,
        follow_up_actions: Optional[str] = None,
        materials_shared: Optional[str] = None,
        samples_distributed: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> dict:
        """
        Tool 1: Log Interaction
        Captures interaction data with LLM-powered summarization and entity extraction.

        Args:
            hcp_id: Healthcare Professional ID
            interaction_type: Type of interaction (Meeting, Call, Email, etc.)
            date: Date of interaction
            time: Time of interaction
            attendees: People who attended
            topics_discussed: Topics discussed
            raw_text: Raw conversation text for LLM analysis
            db: Database session

        Returns:
            Dictionary with interaction details and LLM analysis
        """
        try:
            combined_text = _build_raw_text(
                topics_discussed,
                attendees,
                raw_text,
                outcomes,
                follow_up_actions,
            )

            ai_summary = None
            sentiment = "Neutral"
            key_entities = {}

            if combined_text:
                summary_result = groq_service.summarize_interaction(combined_text)
                ai_summary = summary_result.get("summary", "")
                sentiment = summary_result.get("sentiment", "Neutral")
                key_entities = groq_service.extract_entities(combined_text)

            if db:
                kwargs = {
                    "hcp_id": hcp_id,
                    "interaction_type": interaction_type,
                    "time": time,
                    "attendees": attendees,
                    "topics_discussed": topics_discussed,
                    "outcomes": outcomes,
                    "follow_up_actions": follow_up_actions,
                    "materials_shared": materials_shared,
                    "samples_distributed": samples_distributed,
                    "ai_summary": ai_summary,
                    "sentiment": sentiment,
                    "key_entities": json.dumps(key_entities),
                }
                # Only pass date if provided (let DB use default otherwise)
                if date:
                    kwargs["date"] = _parse_date(date)
                interaction = Interaction(**kwargs)
                db.add(interaction)
                db.commit()
                db.refresh(interaction)

                return {
                    "status": "success",
                    "interaction_id": interaction.id,
                    "message": f"Interaction logged successfully for HCP {hcp_id}",
                    "ai_summary": ai_summary,
                    "sentiment": sentiment,
                    "entities": key_entities,
                }

            return {
                "status": "success",
                "message": "Interaction validated",
                "ai_summary": ai_summary,
                "sentiment": sentiment,
                "entities": key_entities,
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def edit_interaction(
        interaction_id: int,
        updates: dict,
        db: Optional[Session] = None,
    ) -> dict:
        """
        Tool 2: Edit Interaction
        Allows modification of previously logged interaction data.

        Args:
            interaction_id: ID of interaction to edit
            updates: Dictionary of fields to update
            db: Database session

        Returns:
            Dictionary with updated interaction details
        """
        try:
            if not db:
                return {"status": "error", "message": "Database session required"}

            interaction = db.query(Interaction).filter(
                Interaction.id == interaction_id
            ).first()

            if not interaction:
                return {
                    "status": "error",
                    "message": f"Interaction {interaction_id} not found",
                }

            # Update allowed fields
            allowed_fields = [
                "interaction_type",
                "time",
                "attendees",
                "topics_discussed",
                "outcomes",
                "follow_up_actions",
                "materials_shared",
                "samples_distributed",
                "sentiment",
            ]

            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(interaction, field, value)

            # If topics changed, regenerate summary
            if "topics_discussed" in updates and interaction.topics_discussed:
                summary_result = groq_service.summarize_interaction(
                    interaction.topics_discussed
                )
                interaction.ai_summary = summary_result.get("summary")
                interaction.sentiment = summary_result.get("sentiment", "Neutral")

            db.commit()
            db.refresh(interaction)

            return {
                "status": "success",
                "message": f"Interaction {interaction_id} updated successfully",
                "updated_fields": list(updates.keys()),
                "interaction_id": interaction_id,
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def search_hcp(
        query: str,
        search_type: str = "name",
        db: Optional[Session] = None,
    ) -> dict:
        """
        Tool 3: Search HCP
        Searches for Healthcare Professionals by name, specialty, or organization.

        Args:
            query: Search query
            search_type: Type of search (name, specialty, organization)
            db: Database session

        Returns:
            List of matching HCPs
        """
        try:
            if not db:
                return {"status": "error", "message": "Database session required"}

            if search_type == "name":
                hcps = (
                    db.query(HCP).filter(HCP.name.ilike(f"%{query}%")).limit(10).all()
                )
            elif search_type == "specialty":
                hcps = (
                    db.query(HCP)
                    .filter(HCP.specialty.ilike(f"%{query}%"))
                    .limit(10)
                    .all()
                )
            elif search_type == "organization":
                hcps = (
                    db.query(HCP)
                    .filter(HCP.organization.ilike(f"%{query}%"))
                    .limit(10)
                    .all()
                )
            else:
                return {"status": "error", "message": f"Unknown search type: {search_type}"}

            results = [
                {
                    "id": hcp.id,
                    "name": hcp.name,
                    "specialty": hcp.specialty,
                    "organization": hcp.organization,
                    "email": hcp.email,
                }
                for hcp in hcps
            ]

            return {
                "status": "success",
                "query": query,
                "search_type": search_type,
                "results_count": len(results),
                "results": results,
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_interaction_history(
        hcp_id: int,
        limit: int = 10,
        db: Optional[Session] = None,
    ) -> dict:
        """
        Tool 4: Get Interaction History
        Retrieves past interactions with a specific HCP.

        Args:
            hcp_id: Healthcare Professional ID
            limit: Maximum number of records to return
            db: Database session

        Returns:
            List of past interactions with HCP details
        """
        try:
            if not db:
                return {"status": "error", "message": "Database session required"}

            # Get HCP details
            hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
            hcp_name = hcp.name if hcp else "Unknown"
            hcp_specialty = hcp.specialty if hcp else "Unknown"
            hcp_organization = hcp.organization if hcp else "Unknown"

            interactions = (
                db.query(Interaction)
                .filter(Interaction.hcp_id == hcp_id)
                .order_by(Interaction.date.desc())
                .limit(limit)
                .all()
            )

            results = [
                {
                    "id": interaction.id,
                    "type": interaction.interaction_type,
                    "date": interaction.date.isoformat(),
                    "time": interaction.time,
                    "topics": interaction.topics_discussed,
                    "summary": interaction.ai_summary,
                    "sentiment": interaction.sentiment,
                    "outcomes": interaction.outcomes,
                    "follow_up": interaction.follow_up_actions,
                    "attendees": interaction.attendees,
                    "hcp_name": hcp_name,
                    "hcp_specialty": hcp_specialty,
                    "hcp_organization": hcp_organization,
                }
                for interaction in interactions
            ]

            return {
                "status": "success",
                "hcp_id": hcp_id,
                "hcp_name": hcp_name,
                "total_interactions": len(results),
                "interactions": results,
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def suggest_follow_up_actions(
        interaction_id: int,
        db: Optional[Session] = None,
    ) -> dict:
        """
        Tool 5: Suggest Follow-up Actions
        AI-powered tool that suggests next steps based on interaction content.

        Args:
            interaction_id: ID of the interaction
            db: Database session

        Returns:
            List of suggested follow-up actions
        """
        try:
            if not db:
                return {"status": "error", "message": "Database session required"}

            interaction = db.query(Interaction).filter(
                Interaction.id == interaction_id
            ).first()

            if not interaction:
                return {
                    "status": "error",
                    "message": f"Interaction {interaction_id} not found",
                }

            # Generate suggestions using LLM
            prompt = f"""Based on this HCP interaction, suggest 3-5 specific follow-up actions:

Topics Discussed: {interaction.topics_discussed}
Outcomes: {interaction.outcomes or 'Not specified'}
Sentiment: {interaction.sentiment}
Summary: {interaction.ai_summary or 'Not summarized'}

Provide actionable, specific follow-up suggestions."""

            suggestion_text = groq_service.generate_chat_response(prompt)

            # Parse suggestions
            suggestions = [s.strip() for s in suggestion_text.split("\n") if s.strip()]

            return {
                "status": "success",
                "interaction_id": interaction_id,
                "suggestions": suggestions,
                "full_response": suggestion_text,
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_recommended_materials(
        topic: str,
        db: Optional[Session] = None,
    ) -> dict:
        """
        Tool 6: Get Recommended Materials
        Suggests relevant materials/samples to share based on interaction topics.

        Args:
            topic: Topic or disease area
            db: Database session

        Returns:
            List of recommended materials
        """
        try:
            if not db:
                return {"status": "error", "message": "Database session required"}

            # Search materials by category/topic
            materials = (
                db.query(Material)
                .filter(
                    (Material.category.ilike(f"%{topic}%"))
                    | (Material.name.ilike(f"%{topic}%"))
                )
                .limit(10)
                .all()
            )

            results = [
                {
                    "id": material.id,
                    "name": material.name,
                    "category": material.category,
                    "description": material.description,
                }
                for material in materials
            ]

            return {
                "status": "success",
                "topic": topic,
                "materials_count": len(results),
                "materials": results,
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}
