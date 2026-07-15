"""
LangGraph Agent for AI-First CRM HCP Module
Optimized pipeline: DB first → Groq only with context

FIXES IMPLEMENTED:
1. Session state management - persists selected_hcp, selected_interaction_id across messages
2. Follow-up context reuse - automatically uses previous HCP/interaction for follow-ups
3. Date filtering fix - proper datetime comparison instead of string concatenation
4. Intent detection improvement - recognizes follow-ups without HCP mentions
5. Session_id support throughout pipeline
6. Error handling and logging improvements
7. Conversation memory check before clarification questions
"""

from typing import Any, Dict, List, Optional
import json
import re
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from local_langgraph.tools import InteractionTools
from app.models import HCP, Interaction
from services.groq_service import GroqService

logger = logging.getLogger(__name__)
groq_service = GroqService()

# Raw conversation history per session (messages only)
conversation_memory: Dict[str, List[Dict]] = {}

# Structured session state per session - persists HCP, interaction, date context
# FIX: Added session_state dict to track current context across messages
session_state: Dict[str, Dict[str, Any]] = {}


class HCPInteractionAgent:
    """Optimized agent: Extract → DB → Build context → Groq (only if needed)"""

    def __init__(self):
        self.groq_service = groq_service

    # ── Conversation Memory ──────────────────────────────────────

    def _get_history(self, session_id: str, limit: int = 5) -> List[Dict]:
        if session_id not in conversation_memory:
            return []
        return conversation_memory[session_id][-limit:]

    def _add_memory(self, session_id: str, role: str, content: str):
        if session_id not in conversation_memory:
            conversation_memory[session_id] = []
        conversation_memory[session_id].append({
            "role": role, "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        if len(conversation_memory[session_id]) > 50:
            conversation_memory[session_id] = conversation_memory[session_id][-50:]

    def _format_history(self, history: List[Dict]) -> str:
        if not history:
            return ""
        lines = ["Previous conversation:"]
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    # ── Session State Management (NEW) ────────────────────────────
    # FIX: Added persistent session state to track selected HCP, interaction, date
    # This ensures follow-up questions automatically use the previous context.

    def _get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get the structured state for a session, initializing if needed."""
        if session_id not in session_state:
            session_state[session_id] = {
                "selected_hcp_name": None,        # Last HCP name the user asked about
                "selected_hcp_id": None,           # Last HCP database ID
                "selected_interaction_id": None,   # Last interaction ID retrieved
                "selected_date": None,             # Last date filter used
                "interaction_type": None,           # Last interaction type
                "selected_interaction_data": None,  # Full last interaction data for follow-ups
            }
        return session_state[session_id]

    def _update_session_state(self, session_id: str, **kwargs):
        """Update session state with new values."""
        state = self._get_session_state(session_id)
        for key, value in kwargs.items():
            if value is not None:
                state[key] = value
        logger.debug(f"Session {session_id} state updated: {kwargs}")

    def _clear_hcp_context(self, session_id: str):
        """Clear HCP-specific context when user explicitly switches HCP."""
        state = self._get_session_state(session_id)
        state["selected_interaction_id"] = None
        state["selected_interaction_data"] = None
        state["selected_date"] = None

    # ── Entity Extraction (No Groq - pure regex) ────────────────

    def _extract_hcp_name(self, message: str, session_id: str = "default") -> Optional[str]:
        """Extract HCP name from message using regex only. Fast, no LLM call.
        
        FIX: First checks if a new HCP is mentioned in current message.
             If not found, checks session state for previously selected HCP.
             Only checks raw conversation memory as last resort.
        """
        # Pattern 1: "Dr. John Smith" / "Dr John Smith"
        # IMPORTANT: No re.IGNORECASE - [A-Z] must be uppercase to avoid matching "today", "at", etc.
        m = re.search(r'(\bDr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', message)
        if m:
            name = m.group(1).strip()
            return name

        # Pattern 1b: "Dr. John" (single last name)
        m = re.search(r'(\bDr\.?\s+[A-Z][a-z]+)', message)
        if m:
            return m.group(1).strip()

        # Pattern 2: "with John Smith" - extract person name after keyword
        m = re.search(r'(?:with|to|for|meet)\s+((?:[A-Z][a-z]+(?:\s+|$)){1,3})', message)
        if m:
            name = m.group(1).strip()
            # Ignore short words like "the" or "a" or "at"
            words = name.split()
            if len(words) >= 2 or (len(words) == 1 and len(words[0]) > 2):
                return name

        # FIX: Check session state for previously selected HCP BEFORE checking raw memory
        state = self._get_session_state(session_id)
        if state["selected_hcp_name"]:
            logger.debug(f"Using session state HCP: {state['selected_hcp_name']}")
            return state["selected_hcp_name"]

        # Pattern 3: Check conversation memory for last mentioned HCP
        # (Only as last resort fallback)
        memory = self._get_history(session_id)
        for msg in reversed(memory):
            m = re.search(r'(Dr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', msg.get("content", ""), re.IGNORECASE)
            if m:
                return m.group(1).strip()

        return None

    def _extract_date_filters(self, message: str) -> tuple:
        """Parse date phrases from message. Returns (date_from, date_to) ISO strings."""
        msg = message.lower()
        today = date.today()
        today_str = today.isoformat()

        if "today" in msg:
            return (today_str, today_str)
        if "yesterday" in msg:
            y = (today - timedelta(days=1)).isoformat()
            return (y, y)
        if "this week" in msg:
            start = (today - timedelta(days=today.weekday())).isoformat()
            return (start, today_str)
        if "this month" in msg:
            start = today.replace(day=1).isoformat()
            return (start, today_str)
        if "last week" in msg:
            end = (today - timedelta(days=today.weekday() + 1)).isoformat()
            start = (today - timedelta(days=today.weekday() + 7)).isoformat()
            return (start, end)
        if "last month" in msg:
            first_of_this = today.replace(day=1)
            end = (first_of_this - timedelta(days=1)).isoformat()
            start = end[:8] + "01"
            return (start, end)

        return (None, None)

    def _extract_interaction_type(self, message: str) -> Optional[str]:
        """Extract interaction type from message."""
        msg = message.lower()
        if "meeting" in msg or "met" in msg:
            return "Meeting"
        if "call" in msg or "phone" in msg:
            return "Call"
        if "email" in msg:
            return "Email"
        if "conference" in msg:
            return "Conference"
        return None

    # ── Database Retrieval (Always first, before Groq) ──────────

    def _find_hcp(self, name_hint: str, db: Session) -> Optional[dict]:
        """Find HCP by name in database."""
        if not db or not name_hint:
            return None
        try:
            # Try exact match first
            hcp = db.query(HCP).filter(HCP.name.ilike(name_hint)).first()
            if hcp:
                return {"id": hcp.id, "name": hcp.name, "specialty": hcp.specialty, "organization": hcp.organization}

            # Try partial match
            hcps = db.query(HCP).filter(HCP.name.ilike(f"%{name_hint.replace('Dr.', '').replace('Dr ', '').strip()}%")).limit(3).all()
            if hcps:
                hcp = hcps[0]
                return {"id": hcp.id, "name": hcp.name, "specialty": hcp.specialty, "organization": hcp.organization}

            # Try without "Dr." prefix
            simple = re.sub(r'^Dr\.?\s*', '', name_hint, flags=re.IGNORECASE).strip()
            if simple != name_hint:
                hcp = db.query(HCP).filter(HCP.name.ilike(f"%{simple}%")).first()
                if hcp:
                    return {"id": hcp.id, "name": hcp.name, "specialty": hcp.specialty, "organization": hcp.organization}
        except Exception as e:
            logger.error(f"HCP lookup error: {e}")
        return None

    def _get_interactions(self, hcp_id: int, db: Session, date_from: str = None, date_to: str = None, limit: int = 10) -> List[dict]:
        """Get interactions from DB with optional date filtering. Returns raw data for direct answering.
        
        FIX: Fixed date filtering to use proper datetime comparison instead of string concatenation.
             SQLite compares DateTime with string inconsistently - we now parse to datetime objects.
        """
        try:
            query = db.query(Interaction).filter(Interaction.hcp_id == hcp_id)

            # FIX: Convert date strings to proper datetime objects for reliable comparison
            if date_from:
                try:
                    dt_from = datetime.fromisoformat(date_from)
                    query = query.filter(Interaction.date >= dt_from)
                except ValueError:
                    query = query.filter(Interaction.date >= date_from)
            if date_to:
                try:
                    dt_to = datetime.fromisoformat(date_to)
                    # Set to end of day for inclusive comparison
                    dt_to = dt_to.replace(hour=23, minute=59, second=59)
                    query = query.filter(Interaction.date <= dt_to)
                except ValueError:
                    query = query.filter(Interaction.date <= date_to + " 23:59:59")

            interactions = query.order_by(Interaction.date.desc()).limit(limit).all()
            return [
                {
                    "id": i.id,
                    "type": i.interaction_type,
                    "date": i.date.isoformat() if hasattr(i.date, 'isoformat') else str(i.date),
                    "time": i.time or "",
                    "attendees": i.attendees or "",
                    "topics": i.topics_discussed or "",
                    "summary": i.ai_summary or "",
                    "outcomes": i.outcomes or "",
                    "follow_up": i.follow_up_actions or "",
                    "sentiment": i.sentiment or "Neutral",
                    "hcp_id": i.hcp_id,  # FIX: Include hcp_id for session state
                }
                for i in interactions
            ]
        except Exception as e:
            logger.error(f"Interaction query error: {e}")
            return []

    def _format_interactions(self, hcp_name: str, interactions: List[dict]) -> str:
        """Format interactions into a readable context string."""
        if not interactions:
            return ""

        lines = [f"Interactions with {hcp_name}:"]
        for i, ix in enumerate(interactions, 1):
            lines.append(f"\n{i}. [{ix['type']}] {ix['date']} at {ix['time']}")
            if ix['attendees']:
                lines.append(f"   Attendees: {ix['attendees']}")
            if ix['topics']:
                lines.append(f"   Topics: {ix['topics']}")
            if ix['summary']:
                lines.append(f"   Summary: {ix['summary']}")
            if ix['outcomes']:
                lines.append(f"   Outcomes: {ix['outcomes']}")
            if ix['follow_up']:
                lines.append(f"   Follow-up: {ix['follow_up']}")
            lines.append(f"   Sentiment: {ix['sentiment']}")

        return "\n".join(lines)

    # ── Direct Answer Builder (No Groq when data suffices) ──────

    def _answer_from_data(self, message: str, interactions: List[dict], hcp_name: str) -> Optional[str]:
        """Try to answer common questions directly from DB data without calling Groq.
        
        FIX: Handles "first one" / "first" references for conversation like
             "Show today's meetings" → "Summarize the first one"
        """
        if not interactions:
            return None

        msg = message.lower()
        latest = interactions[0]  # Most recent

        # FIX: Handle "the first one" or "first" reference
        if "first" in msg:
            target = interactions[0]
            if "summarize" in msg or "summary" in msg:
                if target.get("summary"):
                    return f"**Summary of {target['type']} with {hcp_name} on {target['date']}:**\n{target['summary']}"
                return None  # Let Groq handle
            if "who attended" in msg or "attendee" in msg:
                if target.get("attendees"):
                    return f"The attendees for the {target['type'].lower()} on {target['date']} with {hcp_name} were: **{target['attendees']}**."

        # "Who attended" questions
        if "who attended" in msg or "who was there" in msg or "who else was" in msg:
            if latest.get("attendees"):
                return f"The attendees for the {latest['type'].lower()} on {latest['date']} with {hcp_name} were: **{latest['attendees']}**."
            else:
                return f"No attendees were recorded for the latest {latest['type'].lower()} with {hcp_name}."

        # "What topics" / "What was discussed"
        if any(p in msg for p in ["topics", "discussed", "talk about", "what did you discuss"]):
            if latest.get("topics"):
                return f"The following topics were discussed with {hcp_name} on {latest['date']}: {latest['topics']}."
            else:
                return f"No topics were recorded for the latest interaction with {hcp_name}."

        # "What outcomes" / "What was agreed"
        if any(p in msg for p in ["outcome", "agreed", "agreement", "result"]):
            if latest.get("outcomes"):
                return f"The outcomes from the {latest['type'].lower()} with {hcp_name} on {latest['date']} were: {latest['outcomes']}."
            else:
                return "No specific outcomes were recorded for this interaction."

        # "Follow-up" / "Next steps"
        if any(p in msg for p in ["follow", "next step", "next action"]):
            if latest.get("follow_up"):
                return f"The follow-up actions from the {latest['type'].lower()} with {hcp_name} were: {latest['follow_up']}."
            else:
                return "No follow-up actions were recorded for the latest interaction."

        # "When was" / "What date"
        if any(p in msg for p in ["when was", "what date", "what time"]):
            return f"The latest {latest['type'].lower()} with {hcp_name} was on {latest['date']} at {latest['time']}."

        # "Summarize" / "Summary" - needs Groq for good summary
        if "summarize" in msg or "summary" in msg:
            return None  # Let Groq handle

        # "How many" / "List all"
        if "how many" in msg or "list all" in msg or "count" in msg:
            count = len(interactions)
            return f"There are {count} recorded interactions with {hcp_name}."

        return None  # Fall through to Groq

    # ── Main Processing Pipeline ────────────────────────────────

    def process_interaction(
        self,
        user_message: str,
        interaction_context: Optional[Dict[str, Any]] = None,
        db: Session = None,
        session_id: str = "default",
    ) -> Dict[str, Any]:
        """Pipeline: Extract → DB → Answer directly → Groq only as fallback.
        
        FIX: Properly passes session_id throughout the entire pipeline.
             Ensures session state is checked before asking clarifying questions.
        """
        try:
            self._add_memory(session_id, "user", user_message)
            history = self._get_history(session_id)
            conv_ctx = self._format_history(history[:-1])

            # Step 1: Extract entities (pure regex, no Groq)
            hcp_name = self._extract_hcp_name(user_message, session_id)
            date_from, date_to = self._extract_date_filters(user_message)
            ix_type = self._extract_interaction_type(user_message)

            # Step 2: Determine intent
            intent = self._analyze_intent(user_message, session_id)

            # Step 3: Execute
            if intent == "log_interaction":
                result = self._handle_log_interaction(user_message, db, session_id)
            elif intent == "edit_interaction":
                result = self._handle_edit_interaction(user_message, db, session_id)
            elif intent == "search":
                result = self._handle_search(user_message, db)
            elif intent in ("history", "general"):
                result = self._handle_query(user_message, hcp_name, date_from, date_to, ix_type, db, conv_ctx, session_id)
            elif intent == "follow_up":
                result = self._handle_follow_up(user_message, hcp_name, db, session_id)
            else:
                result = self._handle_general_query(user_message, db, conv_ctx, session_id)

            response_text = (
                result.get("response", "")
                or result.get("message", "")
                or str(result.get("extracted", {}))
            )
            if response_text:
                self._add_memory(session_id, "assistant", response_text)

            return {"status": "success", "intent": intent, "result": result}

        except Exception as e:
            logger.exception(f"Error: {e}")
            return {"status": "error", "message": str(e)}

    def _analyze_intent(self, message: str, session_id: str = "default") -> str:
        """Smart intent detection.
        
        FIX: Recognizes follow-up questions that reference previous context
             even when no explicit HCP or query indicator is present.
             For example: "What was discussed?" after "Who attended meeting with Dr. Smith?"
        """
        msg = message.lower()

        # Strong log indicators: user is describing a past interaction they participated in
        log_indicators = ["i met", "i had a", "i attended", "i spoke with", "i called",
                          "i visited", "just met", "just had", "we discussed",
                          "we talked about", "i discussed", "the meeting went",
                          "log this", "record this", "save this interaction"]
        if any(indicator in msg for indicator in log_indicators):
            return "log_interaction"

        # Explicit log commands
        if any(w in msg for w in ["log", "record", "add", "new interaction"]):
            return "log_interaction"

        # Edit/update - also detect "Actually" + field changes
        if any(w in msg for w in ["edit", "update", "change", "modify"]):
            return "edit_interaction"
        
        # Detect edits like "Actually, X should be Y" or "Make X = Y" or "Set X to Y"
        if msg.startswith("actually") or "should be" in msg or "should have" in msg:
            return "edit_interaction"
        
        # Detect removals like "remove X", "delete X", "drop X"
        if any(w in msg for w in ["remove", "delete", "drop"]) and any(
            f in msg for f in ["samples", "material", "follow", "attendee", "topic", "outcome"]
        ):
            return "edit_interaction"

        # Search
        if any(w in msg for w in ["search for", "search", "find", "look for"]):
            return "search"

        # Follow-up
        if any(w in msg for w in ["follow", "suggest", "next step", "next action"]):
            return "follow_up"

        # History / query indicators (asking about past events, not reporting them)
        query_indicators = ["who attended", "what was discussed", "summarize", "summary",
                           "tell me about", "what happened", "show me",
                           "what did we discuss", "what were the",
                           "when was", "what date", "what time",
                           "how many", "list all",
                           "what are the follow"]
        if any(indicator in msg for indicator in query_indicators):
            return "history"

        # FIX: If message mentions doctor name and sounds like a question
        if any(w in msg for w in ["dr.", "dr ", "doctor"]):
            # If it's a question or request for info, it's history
            if any(q in msg for q in ["what", "who", "when", "where", "how", "?"]):
                return "history"
            # If it's describing a meeting ("met Dr. X" or "visited Dr. X"), it's log
            if any(v in msg for v in ["met", "visited", "saw", "called", "spoke"]):
                return "log_interaction"
            return "history"

        # FIX: Check session state - if we have a selected HCP/interaction, 
        # treat short follow-ups as history queries
        state = self._get_session_state(session_id)
        if state["selected_hcp_name"] and state["selected_interaction_id"]:
            # Short questions without HCP names are likely follow-ups
            if len(message.split()) <= 8:
                return "history"

        return "general"

    # ── Query Handler (The core fix) ───────────────────────────

    def _handle_query(self, message: str, hcp_name: Optional[str],
                      date_from: Optional[str], date_to: Optional[str],
                      ix_type: Optional[str], db: Session,
                      conv_ctx: str, session_id: str) -> Dict:
        """DB-first query handler. Only calls Groq when necessary.
        
        FIX: 
        1. Always checks session state for previously selected HCP
        2. Caches retrieved interaction data in session state BEFORE returning direct answer
        3. Handles follow-up questions using cached context
        4. Fixed date filtering to work with datetime objects
        5. Summarize queries ignore date filters - always use the latest interaction
        """
        if not db:
            return {"response": "Database is not connected."}

        state = self._get_session_state(session_id)

        # Step 1: Find HCP - check current message, then session state
        hcp_data = None
        if hcp_name:
            hcp_data = self._find_hcp(hcp_name, db)
            if hcp_data:
                # FIX: If user mentioned a NEW HCP, clear old context
                if state["selected_hcp_name"] and state["selected_hcp_name"] != hcp_data["name"]:
                    self._clear_hcp_context(session_id)

        # FIX: If no HCP in current message, use session state
        if not hcp_data:
            if state["selected_hcp_id"]:
                hcp = db.query(HCP).filter(HCP.id == state["selected_hcp_id"]).first()
                if hcp:
                    hcp_data = {"id": hcp.id, "name": hcp.name, "specialty": hcp.specialty, "organization": hcp.organization}
                    logger.debug(f"Using session state HCP: {hcp.name}")

        # FIX: Check conversation memory for HCP context as last resort
        if not hcp_data:
            memory = self._get_history(session_id)
            for msg in reversed(memory):
                m = re.search(r'(Dr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', msg.get("content", ""), re.IGNORECASE)
                if m:
                    hcp_name = m.group(1).strip()
                    hcp_data = self._find_hcp(hcp_name, db)
                    if hcp_data:
                        break

        if not hcp_data:
            # No HCP found - list available HCPs
            hcps = db.query(HCP).order_by(HCP.name).limit(10).all()
            if hcps:
                hcp_list = "\n".join([f"- {h.name} ({h.specialty})" for h in hcps])
                return {
                    "response": f"I couldn't identify which HCP you're asking about. Here are the available HCPs:\n\n{hcp_list}\n\nPlease specify one, e.g. 'What was discussed with Dr. John Smith?'"
                }
            return {"response": "There are no HCPs registered in the system yet."}

        # Step 1b: For summarize/summary queries, ignore date filters and use latest interaction
        msg_lower = message.lower()
        if "summarize" in msg_lower or "summary" in msg_lower:
            date_from = None
            date_to = None
            logger.debug(f"Summarize query detected - ignoring date filters to get latest interaction for {hcp_data['name']}")

        # Step 2: Get interactions from DB
        interactions = self._get_interactions(hcp_data["id"], db, date_from, date_to)

        if not interactions:
            # FIX: More helpful message with logging for debugging
            logger.debug(f"No interactions found for HCP {hcp_data['id']} with date_from={date_from}, date_to={date_to}")
            return {
                "response": f"There are no recorded interactions with **{hcp_data['name']}**"
                           + (f" in the specified time period." if date_from else " yet.")
            }

        # FIX: CRITICAL - Update session state BEFORE trying direct answer
        # Previously this was AFTER the direct answer return, which meant
        # follow-up questions would lose context when direct answers were used.
        # Now the state is always updated before returning.
        self._update_session_state(
            session_id,
            selected_hcp_name=hcp_data["name"],
            selected_hcp_id=hcp_data["id"],
            selected_interaction_id=interactions[0]["id"],
            selected_interaction_data=interactions[0],  # Cache for follow-ups
            selected_date=date_from or date_to,
            interaction_type=interactions[0].get("type"),
        )

        # Step 3: Try to answer directly from data (no Groq)
        direct_answer = self._answer_from_data(message, interactions, hcp_data["name"])
        if direct_answer:
            return {"response": direct_answer}

        # Step 4: Build context and use Groq only if needed
        context = self._format_interactions(hcp_data["name"], interactions)
        prompt = (
            f"You are an AI CRM assistant for healthcare field representatives. "
            f"You are currently discussing {hcp_data['name']}. "
            f"Answer the user's question based ONLY on the interaction records below.\n\n"
            f"{conv_ctx}\n"
            f"Interaction History Context:\n{context}\n\n"
            f"User Question: {message}\n\n"
            f"Answer concisely and cite specific data from the records."
        )
        response = self.groq_service.generate_chat_response(prompt)
        return {"message": context, "response": response}

    # ── Log Interaction Handler ─────────────────────────────────

    def _handle_log_interaction(self, message: str, db: Session, session_id: str) -> Dict:
        """Log an interaction from chat with minimal Groq calls."""
        if not db:
            return {"response": "Database is not connected."}

        # Extract HCP from message
        hcp_name = self._extract_hcp_name(message, session_id)
        if not hcp_name:
            hcps = db.query(HCP).order_by(HCP.name).limit(10).all()
            if hcps:
                hcp_list = "\n".join([f"- {h.name} ({h.specialty})" for h in hcps])
                return {
                    "response": f"I couldn't identify the HCP. Available doctors:\n{hcp_list}\n\nPlease specify, e.g. 'I met Dr. John Smith and we discussed...'"
                }
            return {"response": "No HCPs registered yet."}

        hcp_data = self._find_hcp(hcp_name, db)
        if not hcp_data:
            return {"response": f"Could not find {hcp_name} in the system. Please check the name and try again."}

        # Extract details using a single Groq call with strict rules
        prompt = (
            f"Extract structured data from this HCP interaction message. Return ONLY valid JSON.\n"
            f"\n"
            f"CRITICAL RULES - Follow exactly:\n"
            f"1. Do NOT hallucinate values. If a field is not mentioned, use null.\n"
            f"2. If the user explicitly states a value, use it exactly as stated.\n"
            f'3. "Today" → Use the current system date: {date.today().isoformat()}\n'
            f"4. If no time is mentioned → Set time to null (do NOT guess a default).\n"
            f"5. Do NOT treat the HCP name as an attendee unless explicitly mentioned.\n"
            f'6. "I shared brochures" → Populate materials_shared = "Brochures"\n'
            f"7. For sentiment: Only populate if user explicitly says \"positive\", \"neutral\", or \"negative\".\n"
            f"   Map directly. If not mentioned, set to null.\n"
            f"8. Do NOT create an outcome unless the user explicitly provides one.\n"
            f"9. Do NOT create a follow_up_actions unless the user explicitly mentions one.\n"
            f"\n"
            f"Fields to extract:\n"
            f"- interaction_type: \"Meeting\", \"Call\", \"Email\", \"Conference\", or \"Other\". null if unclear.\n"
            f"- date: YYYY-MM-DD. Use today's date ONLY if the user says \"today\". null otherwise.\n"
            f"- time: HH:MM. null if not mentioned.\n"
            f"- attendees: comma-separated list. null if not mentioned.\n"
            f"- topics_discussed: what was discussed. null if not mentioned.\n"
            f"- materials_shared: materials or brochures shared. null if not mentioned.\n"
            f"- samples_distributed: product samples distributed. null if not mentioned.\n"
            f"- outcomes: any outcomes. null if not mentioned.\n"
            f"- follow_up_actions: any follow-ups. null if not mentioned.\n"
            f"- sentiment: \"Positive\", \"Neutral\", or \"Negative\". null if not explicitly stated.\n"
            f"\n"
            f"Text: {message}\n\n"
            f"Return ONLY valid JSON."
        )
        response = self.groq_service.generate_chat_response(prompt)
        try:
            details = json.loads(response)
        except (json.JSONDecodeError, ValueError):
            # Attempt to extract JSON from the response if it contains markdown fences
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    details = json.loads(json_match.group())
                except (json.JSONDecodeError, ValueError):
                    return {"response": "I couldn't parse the interaction details. Please use the form instead."}
            else:
                # Fallback: extract fields using regex from the text response
                details = {}
                type_match = re.search(r'interaction_type["\s:]+([A-Za-z]+)', response)
                if type_match: details["interaction_type"] = type_match.group(1)
                date_match = re.search(r'date["\s:]+(\d{4}-\d{2}-\d{2})', response)
                if date_match: details["date"] = date_match.group(1)
                time_match = re.search(r'time["\s:]+(\d{2}:\d{2})', response)
                if time_match: details["time"] = time_match.group(1)
                attendees_match = re.search(r'attendees["\s:]+(.*?)(?:,|\n|$)', response)
                if attendees_match: details["attendees"] = attendees_match.group(1).strip()
                topics_match = re.search(r'topics_discussed["\s:]+(.*?)(?:,|\n|$)', response)
                if topics_match: details["topics_discussed"] = topics_match.group(1).strip()
                if not details:
                    return {"response": "I couldn't parse the interaction details. Please use the form instead."}

        # Save to DB - only pass fields that were explicitly extracted (not null)
        try:
            log_kwargs = {
                "hcp_id": hcp_data["id"],
                "interaction_type": details.get("interaction_type") or "Meeting",
                "raw_text": message,
                "db": db,
            }
            # Only include date if explicitly extracted
            if details.get("date"):
                log_kwargs["date"] = details["date"]
            # Only include time if explicitly extracted
            if details.get("time"):
                log_kwargs["time"] = details["time"]
            # Only include attendees if mentioned
            if details.get("attendees"):
                log_kwargs["attendees"] = details["attendees"]
            # Only include topics if mentioned
            if details.get("topics_discussed"):
                log_kwargs["topics_discussed"] = details["topics_discussed"]
            # Only include outcomes if mentioned
            if details.get("outcomes"):
                log_kwargs["outcomes"] = details["outcomes"]
            # Only include follow_up if mentioned
            if details.get("follow_up_actions"):
                log_kwargs["follow_up_actions"] = details["follow_up_actions"]
            # Only include materials if mentioned
            if details.get("materials_shared"):
                log_kwargs["materials_shared"] = details["materials_shared"]
            # Only include samples if mentioned
            if details.get("samples_distributed"):
                log_kwargs["samples_distributed"] = details["samples_distributed"]
            
            result = InteractionTools.log_interaction(**log_kwargs)
            if result["status"] == "error":
                return {"response": f"Error saving: {result['message']}"}
            
            # FIX: Update session state with the logged interaction
            self._update_session_state(
                session_id,
                selected_hcp_name=hcp_data["name"],
                selected_hcp_id=hcp_data["id"],
                selected_interaction_id=result.get("interaction_id"),
                interaction_type=details.get("interaction_type") or "Meeting",
            )
            
            # Build detailed response only from explicitly extracted fields
            field_lines = []
            field_lines.append(f"• HCP: {hcp_data['name']}")
            field_lines.append(f"• Interaction Type: {details.get('interaction_type') or 'Meeting'}")
            # Only show date if it was explicitly provided
            extracted_date = details.get("date")
            if extracted_date:
                field_lines.append(f"• Date: {extracted_date}")
            # Only show time if explicitly mentioned
            extracted_time = details.get("time")
            if extracted_time:
                field_lines.append(f"• Time: {extracted_time}")
            if details.get("attendees"):
                field_lines.append(f"• Attendees: {details['attendees']}")
            if details.get("topics_discussed"):
                field_lines.append(f"• Topics: {details['topics_discussed']}")
            if details.get("materials_shared"):
                field_lines.append(f"• Materials Shared: {details['materials_shared']}")
            if details.get("samples_distributed"):
                field_lines.append(f"• Samples Distributed: {details['samples_distributed']}")
            if details.get("outcomes"):
                field_lines.append(f"• Outcomes: {details['outcomes']}")
            if details.get("follow_up_actions"):
                field_lines.append(f"• Follow-up: {details['follow_up_actions']}")
            if details.get("sentiment"):
                field_lines.append(f"• Sentiment: {details['sentiment']}")
            
            response_text = (
                f"✅ Interaction logged successfully.\n\n"
                f"I updated the following fields:\n"
                + "\n".join(field_lines)
            )
            
            return {
                "response": response_text,
                "interaction_id": result.get("interaction_id"),
                "extracted": details,
            }
        except Exception as e:
            logger.exception(f"Log error: {e}")
            return {"response": f"Error logging: {str(e)}"}

    # ── Handlers ────────────────────────────────────────────────

    def _handle_edit_interaction(self, message: str, db: Session, session_id: str = "default") -> Dict:
        """Handle edit/update requests by parsing the message and applying changes."""
        if not db:
            return {"response": "Database is not connected."}
        
        # Get the current session state to find which interaction to edit
        state = self._get_session_state(session_id)
        interaction_id = state.get("selected_interaction_id")
        
        if not interaction_id:
            # Try to find the most recent interaction
            hcp_name = self._extract_hcp_name(message, session_id)
            if hcp_name:
                hcp_data = self._find_hcp(hcp_name, db)
                if hcp_data:
                    interactions = self._get_interactions(hcp_data["id"], db, limit=1)
                    if interactions:
                        interaction_id = interactions[0]["id"]
            
            if not interaction_id:
                return {"response": "I need to know which interaction to edit. Please specify the HCP name."}
        
        # Use Groq to extract the changes from the message
        prompt = (
            f"Extract the changes the user wants to make to an existing interaction. "
            f"Return ONLY valid JSON with the fields to update.\n\n"
            f"User message: {message}\n\n"
            f"Possible fields to update:\n"
            f"- hcp_name: The HCP's full name (e.g. \"Dr. Michael Brown\"). ONLY use this when the user explicitly changes the doctor/HCP name. Do NOT use this for attendees.\n"
            f"- interaction_type: \"Meeting\", \"Call\", \"Email\", \"Conference\", or \"Other\"\n"
            f"- time: HH:MM\n"
            f"- attendees: comma-separated list of people. ONLY use this when the user explicitly mentions \"attendees\" or \"attendance\". Do NOT use this for doctor name changes.\n"
            f"- topics_discussed: what was discussed\n"
            f"- outcomes: any outcomes\n"
            f"- follow_up_actions: any follow-ups\n"
            f"- materials_shared: materials provided. Use empty string to remove.\n"
            f"- samples_distributed: samples provided. Use empty string to remove.\n"
            f"- sentiment: \"Positive\", \"Neutral\", or \"Negative\"\n\n"
            f"CRITICAL: \"hcp_name\" is for changing the doctor's name. \"attendees\" is for meeting participants. They are DIFFERENT fields.\n\n"
            f"Example: 'change the sentiment to Negative' → {{\"sentiment\": \"Negative\"}}\n"
            f"Example: 'Change the doctor name to Dr. Smith' → {{\"hcp_name\": \"Dr. Smith\"}}\n"
            f"Example: 'Add John as an attendee' → {{\"attendees\": \"John\"}}\n"
            f"Example: 'remove the product samples' → {{\"samples_distributed\": \"\"}}\n"
            f"Return ONLY valid JSON. If no changes can be identified, return {{}}."
        )
        response = self.groq_service.generate_chat_response(prompt)
        try:
            changes = json.loads(response)
        except (json.JSONDecodeError, ValueError):
            return {"response": "I couldn't understand what changes to make. Please be specific."}
        
        if not changes:
            return {"response": "No changes were identified in your message. Please specify what to update."}
        
        # Handle hcp_name change separately - update the HCP record, not the interaction
        hcp_name_changed = None
        if "hcp_name" in changes:
            hcp_name_changed = changes.pop("hcp_name")
            # Find the new HCP in the database
            new_hcp_data = self._find_hcp(hcp_name_changed, db)
            if new_hcp_data:
                # Update the interaction's hcp_id to point to the new HCP
                interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
                if interaction:
                    interaction.hcp_id = new_hcp_data["id"]
                    db.commit()
                    # Update session state with new HCP
                    self._update_session_state(
                        session_id,
                        selected_hcp_name=new_hcp_data["name"],
                        selected_hcp_id=new_hcp_data["id"],
                    )
            else:
                # HCP not found - return error but still process other changes
                logger.warning(f"New HCP '{hcp_name_changed}' not found in database")
        
        # Apply the remaining changes using the edit_interaction tool
        try:
            result = InteractionTools.edit_interaction(
                interaction_id=interaction_id,
                updates=changes,
                db=db,
            )
            
            if result["status"] == "error":
                return {"response": f"Error updating: {result['message']}"}
            
            # Build detailed response from the actual changes made
            updated_fields = result.get("updated_fields", list(changes.keys()))
            change_lines = []
            
            # Add hcp_name change first if it happened
            if hcp_name_changed:
                new_hcp_data = self._find_hcp(hcp_name_changed, db)
                if new_hcp_data:
                    change_lines.append(f"• HCP changed to: {new_hcp_data['name']}")
                else:
                    change_lines.append(f"• HCP changed to: {hcp_name_changed}")
            
            for field in updated_fields:
                field_name = field.replace("_", " ").title()
                new_value = changes.get(field, "")
                if new_value == "" or new_value is None:
                    change_lines.append(f"• {field_name} removed")
                else:
                    change_lines.append(f"• {field_name} changed to: {new_value}")
            
            response_text = (
                f"✅ Interaction updated successfully.\n\n"
                f"Changes made:\n"
                + "\n".join(change_lines)
            )
            
            return {
                "response": response_text,
                "interaction_id": interaction_id,
                "updated_fields": updated_fields,
            }
        except Exception as e:
            logger.exception(f"Edit error: {e}")
            return {"response": f"Error updating interaction: {str(e)}"}

    def _handle_search(self, message: str, db: Session) -> Dict:
        if not db:
            return {"response": "Database is not connected."}
        query = message
        for prefix in ["search for", "search", "find", "look for", "show me"]:
            if query.lower().startswith(prefix):
                query = query[len(prefix):].strip()
                break
        for t in ["name", "specialty", "organization"]:
            r = InteractionTools.search_hcp(query=query, search_type=t, db=db)
            if r.get("status") == "success" and r.get("results_count", 0) > 0:
                results = "\n".join([f"- {h['name']} ({h['specialty']})" for h in r["results"]])
                return {"response": f"Found {r['results_count']} HCPs:\n{results}"}
        hcps = db.query(HCP).order_by(HCP.name).limit(10).all()
        if hcps:
            hcp_list = "\n".join([f"- {h.name} ({h.specialty})" for h in hcps])
            return {"response": f"No matches. Available HCPs:\n{hcp_list}"}
        return {"response": "No HCPs in the system."}

    def _handle_follow_up(self, message: str, hcp_name: Optional[str], db: Session, session_id: str = "default") -> Dict:
        """Handle follow-up action requests.
        
        FIX: Checks session state for HCP context if not provided in current message.
        """
        if not db:
            return {"response": "Database is not connected."}
        
        # FIX: Check session state for HCP if not in message
        if not hcp_name:
            state = self._get_session_state(session_id)
            if state["selected_hcp_name"]:
                hcp_name = state["selected_hcp_name"]
        
        if not hcp_name:
            return {"response": "Which HCP would you like follow-up suggestions for? (e.g., 'suggest follow-up for Dr. John Smith')"}
        
        hcp_data = self._find_hcp(hcp_name, db)
        if not hcp_data:
            return {"response": f"Could not find {hcp_name}."}
        
        # FIX: Use cached interaction_id if available for more accurate follow-ups
        state = self._get_session_state(session_id)
        if state["selected_interaction_id"] and state["selected_hcp_id"] == hcp_data["id"]:
            interaction_id = state["selected_interaction_id"]
        else:
            interactions = self._get_interactions(hcp_data["id"], db, limit=1)
            if not interactions:
                return {"response": f"No interactions found for {hcp_data['name']}."}
            interaction_id = interactions[0]["id"]
        
        result = InteractionTools.suggest_follow_up_actions(interaction_id=interaction_id, db=db)
        if result.get("status") == "success":
            suggestions = "\n".join([f"- {s}" for s in result.get("suggestions", [])])
            return {"response": f"**Follow-up suggestions for {hcp_data['name']}:**\n{suggestions}"}
        return {"response": "Could not generate suggestions."}

    def _handle_general_query(self, message: str, db: Session, conv_ctx: str, session_id: str = "default") -> Dict:
        """General query - still tries DB first if HCP mentioned.
        
        FIX: Passes session_id for context extraction.
        """
        if db:
            hcp_name = self._extract_hcp_name(message, session_id)
            if hcp_name:
                return self._handle_query(message, hcp_name, None, None, None, db, conv_ctx, session_id)
        prompt = (
            f"You are an AI CRM assistant for healthcare field representatives.\n"
            f"{conv_ctx}\n"
            f"User: {message}"
        )
        response = self.groq_service.generate_chat_response(prompt)
        return {"response": response}


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = HCPInteractionAgent()
    return _agent