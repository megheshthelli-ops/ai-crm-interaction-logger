"""
LangGraph Orchestration Module
Routes structured extraction results to the appropriate tools
Executes tools in an intelligent pipeline based on intent
"""
import json
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from local_langgraph.tools import InteractionTools
from app.models import HCP

logger = logging.getLogger(__name__)


class ToolOrchestrator:
    """
    LangGraph-style orchestration for tool execution.
    
    Pipeline:
    1. Receive extraction results + intent
    2. Resolve entities (HCP IDs, etc.)
    3. Execute primary tool
    4. Execute secondary/recommended tools
    5. Aggregate results
    6. Return structured output
    """

    def __init__(self, db: Session = None):
        self.db = db

    def orchestrate(
        self,
        extraction: Dict[str, Any],
        message: str,
    ) -> Dict[str, Any]:
        """
        Main orchestration pipeline.
        
        Args:
            extraction: Structured extraction dict from /extract endpoint
            message: Original user message
        
        Returns:
            Dict with:
            - primary_result: Result from the main tool
            - secondary_results: Results from recommended tools
            - aggregated_data: Combined structured data
            - suggested_actions: List of suggested next actions
        """
        intent = self._detect_primary_intent(extraction, message)
        logger.info(f"Orchestrating with intent: {intent}")

        # Step 1: Resolve HCP
        hcp_data = self._resolve_hcp(extraction)

        # Step 2: Execute primary tool
        primary_result = self._execute_primary_tool(intent, extraction, hcp_data, message)

        # Step 3: Execute secondary tools based on context
        secondary_results = self._execute_secondary_tools(intent, primary_result, extraction, hcp_data)

        # Step 4: Aggregate
        aggregated = self._aggregate_results(extraction, primary_result, secondary_results)

        return {
            "intent": intent,
            "primary_result": primary_result,
            "secondary_results": secondary_results,
            "aggregated_data": aggregated,
            "suggested_actions": aggregated.get("suggested_actions", []),
        }

    def _detect_primary_intent(self, extraction: Dict[str, Any], message: str) -> str:
        """Detect primary intent from extraction results and original message."""
        msg = message.lower()
        
        # Strong log indicators
        log_indicators = ["i met", "i had a", "i attended", "i spoke with", "i called",
                          "i visited", "just met", "just had", "we discussed",
                          "we talked about", "i discussed", "the meeting went",
                          "log this", "record this", "save this"]
        
        if any(indicator in msg for indicator in log_indicators):
            return "log_interaction"
        
        if any(w in msg for w in ["log", "record", "add", "new interaction"]):
            return "log_interaction"
        
        # Check extraction for topics/attendees which indicate a log intent
        if extraction.get("topics_discussed") and extraction.get("interaction_type"):
            return "log_interaction"
        
        # Search
        if any(w in msg for w in ["search", "find", "look for"]):
            return "search_hcp"
        
        # History
        if any(w in msg for w in ["history", "past", "previous", "what happened", "show me"]):
            return "get_interaction_history"
        
        # Follow-up
        if any(w in msg for w in ["follow", "suggest", "next step", "next action"]):
            return "suggest_follow_up"
        
        # Materials
        if any(w in msg for w in ["recommend", "material", "brochure", "sample"]):
            return "get_recommended_materials"
        
        return "log_interaction"

    def _resolve_hcp(self, extraction: Dict[str, Any]) -> Optional[Dict]:
        """Resolve HCP from extraction data using the database."""
        if not self.db:
            return None
        
        hcp_name = extraction.get("hcp_name")
        if not hcp_name:
            return None
        
        try:
            # Clean name for search
            clean_name = hcp_name.replace("Dr.", "").replace("Dr ", "").strip()
            
            # Try exact match
            hcp = self.db.query(HCP).filter(HCP.name.ilike(f"%{clean_name}%")).first()
            if hcp:
                return {"id": hcp.id, "name": hcp.name, "specialty": hcp.specialty, "organization": hcp.organization}
            
            # Try with Dr prefix
            hcp = self.db.query(HCP).filter(HCP.name.ilike(f"%{hcp_name}%")).first()
            if hcp:
                return {"id": hcp.id, "name": hcp.name, "specialty": hcp.specialty, "organization": hcp.organization}
        
        except Exception as e:
            logger.error(f"HCP resolution error: {e}")
        
        return None

    def _execute_primary_tool(
        self,
        intent: str,
        extraction: Dict[str, Any],
        hcp_data: Optional[Dict],
        message: str,
    ) -> Dict[str, Any]:
        """Execute the primary tool based on detected intent."""
        if not self.db:
            return {"status": "error", "message": "Database not available"}

        try:
            if intent == "log_interaction":
                return self._execute_log_interaction(extraction, hcp_data, message)
            elif intent == "search_hcp":
                return InteractionTools.search_hcp(query=message, db=self.db)
            elif intent == "get_interaction_history":
                if hcp_data:
                    return InteractionTools.get_interaction_history(hcp_id=hcp_data["id"], db=self.db)
                return {"status": "error", "message": "No HCP identified for history lookup"}
            elif intent == "suggest_follow_up":
                return {"status": "info", "message": "Follow-up suggestions require an existing interaction ID"}
            elif intent == "get_recommended_materials":
                topic = extraction.get("topics_discussed", message)
                return InteractionTools.get_recommended_materials(topic=topic, db=self.db)
            else:
                return {"status": "error", "message": f"Unknown intent: {intent}"}
        
        except Exception as e:
            logger.error(f"Primary tool execution error: {e}")
            return {"status": "error", "message": str(e)}

    def _execute_log_interaction(
        self,
        extraction: Dict[str, Any],
        hcp_data: Optional[Dict],
        message: str,
    ) -> Dict[str, Any]:
        """Execute the log_interaction tool with extracted data."""
        if not hcp_data:
            return {
                "status": "error",
                "message": "Could not identify HCP. Please specify the HCP name.",
            }
        
        result = InteractionTools.log_interaction(
            hcp_id=hcp_data["id"],
            interaction_type=extraction.get("interaction_type", "Meeting"),
            date=extraction.get("date", ""),
            time=extraction.get("time", "09:00"),
            attendees=extraction.get("attendees", ""),
            topics_discussed=extraction.get("topics_discussed", ""),
            raw_text=message,
            outcomes=extraction.get("outcomes", ""),
            follow_up_actions=extraction.get("follow_up_actions", ""),
            db=self.db,
        )
        
        return result

    def _execute_secondary_tools(
        self,
        intent: str,
        primary_result: Dict[str, Any],
        extraction: Dict[str, Any],
        hcp_data: Optional[Dict],
    ) -> List[Dict[str, Any]]:
        """
        Execute secondary/recommended tools after the primary tool.
        For example, after logging an interaction, suggest follow-ups and materials.
        """
        secondary_results = []
        
        if not self.db:
            return secondary_results
        
        try:
            # After logging, suggest follow-ups and materials
            if intent == "log_interaction" and primary_result.get("status") == "success":
                interaction_id = primary_result.get("interaction_id")
                
                # Get follow-up suggestions
                if interaction_id:
                    try:
                        followup = InteractionTools.suggest_follow_up_actions(
                            interaction_id=interaction_id, db=self.db
                        )
                        if followup.get("status") == "success":
                            secondary_results.append({
                                "tool": "suggest_follow_up_actions",
                                "result": followup,
                            })
                    except Exception as e:
                        logger.error(f"Follow-up suggestion error: {e}")
                
                # Get material recommendations
                topic = extraction.get("topics_discussed", "")
                if topic:
                    try:
                        materials = InteractionTools.get_recommended_materials(
                            topic=topic, db=self.db
                        )
                        if materials.get("status") == "success" and materials.get("materials_count", 0) > 0:
                            secondary_results.append({
                                "tool": "get_recommended_materials",
                                "result": materials,
                            })
                    except Exception as e:
                        logger.error(f"Material recommendation error: {e}")
        
        except Exception as e:
            logger.error(f"Secondary tools error: {e}")
        
        return secondary_results

    def _aggregate_results(
        self,
        extraction: Dict[str, Any],
        primary_result: Dict[str, Any],
        secondary_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Aggregate all results into a structured output."""
        aggregated = {
            "extracted_fields": {
                "hcp_name": extraction.get("hcp_name"),
                "interaction_type": extraction.get("interaction_type"),
                "date": extraction.get("date"),
                "time": extraction.get("time"),
                "attendees": extraction.get("attendees"),
                "topics_discussed": extraction.get("topics_discussed"),
                "outcomes": extraction.get("outcomes"),
                "follow_up_actions": extraction.get("follow_up_actions"),
                "sentiment": extraction.get("sentiment"),
                "ai_summary": extraction.get("ai_summary"),
            },
            "primary_status": primary_result.get("status"),
            "primary_message": primary_result.get("message", ""),
            "interaction_id": primary_result.get("interaction_id"),
            "suggested_actions": [],
        }
        
        # Build suggested actions from secondary results
        for sec in secondary_results:
            tool_name = sec.get("tool", "")
            result = sec.get("result", {})
            
            if tool_name == "suggest_follow_up_actions" and result.get("status") == "success":
                suggestions = result.get("suggestions", [])
                aggregated["suggested_actions"].extend(
                    [{"type": "follow_up", "action": s} for s in suggestions]
                )
            
            if tool_name == "get_recommended_materials" and result.get("status") == "success":
                materials = result.get("materials", [])
                aggregated["suggested_actions"].extend(
                    [{"type": "material", "action": f"Share {m['name']} — {m['description']}"} for m in materials[:3]]
                )
        
        return aggregated


# Singleton instance
_orchestrator = None


def get_orchestrator(db: Optional[Session] = None) -> ToolOrchestrator:
    """Get or create the ToolOrchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ToolOrchestrator(db)
    _orchestrator.db = db
    return _orchestrator