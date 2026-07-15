"""
API Router for Structured Data Extraction from Natural Language
Extracts structured form fields from user messages for auto-population
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from services.groq_service import GroqService
from app.schemas import ExtractionRequest
import json
import re
from datetime import date, timedelta

router = APIRouter(prefix="/extract", tags=["extraction"])
groq_service = GroqService()


class ExtractionResponse(BaseModel):
    hcp_name: Optional[str] = None
    hcp_id: Optional[int] = None
    interaction_type: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[str] = None
    samples_distributed: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    sentiment: Optional[str] = None
    ai_summary: Optional[str] = None
    suggested_tools: list = []


@router.post("", response_model=ExtractionResponse)
async def extract_form_data(request: ExtractionRequest):
    """
    Extract structured form data from a natural language message.
    Returns fields for auto-populating the InteractionForm.
    Uses Groq LLM for intelligent extraction with strict no-hallucination rules.
    """
    try:
        message = request.message

        # Pre-extract with regex for reliable fast-path fields
        hcp_name = _extract_hcp_name_regex(message)
        interaction_type = _extract_interaction_type_regex(message)
        date_str = _extract_date_regex(message)
        materials_shared = _extract_materials_regex(message)
        samples_distributed = _extract_samples_regex(message)

        # Use Groq for full structured extraction with strict rules
        prompt = f"""Extract structured data from this HCP interaction message. Return ONLY valid JSON.

CRITICAL RULES - Follow exactly:
1. Do NOT hallucinate values. If a field is not mentioned, use null.
2. If the user explicitly states a value, use it exactly as stated.
3. "Today" → Use the current system date: {date.today().isoformat()}
4. If no time is mentioned → Set "time" to null (do NOT guess a default).
5. Do NOT treat the HCP name as an attendee unless explicitly mentioned.
6. "I shared brochures" → Populate materials_shared = "Brochures"
7. "product samples" → Populate samples_distributed with the product name
8. For sentiment: Only populate if user explicitly says "positive", "neutral", or "negative".
   Map directly. If not mentioned, set to null.
9. Do NOT create an outcome unless the user explicitly provides one.
10. Do NOT create a follow_up_actions unless the user explicitly mentions one.

Message: {message}

Extract these fields:
- hcp_name: Full name of the Healthcare Professional (e.g. "Dr. John Smith"). null if not found.
- interaction_type: One of "Meeting", "Call", "Email", "Conference", "Other". null if unclear.
- date: Date in YYYY-MM-DD format. Use today's date ONLY if the user says "today". null otherwise.
- time: Time in HH:MM format. null if not mentioned.
- attendees: Comma-separated list. null if not mentioned.
- topics_discussed: What was discussed (concise). null if not mentioned.
- materials_shared: Materials shared (e.g. "Brochures"). null if not mentioned.
- samples_distributed: Product samples distributed. null if not mentioned.
- outcomes: Any outcomes or agreements. null if not mentioned.
- follow_up_actions: Follow-up actions. null if not mentioned.
- sentiment: "Positive", "Neutral", or "Negative". null if not explicitly stated.

Return ONLY valid JSON, no other text. Example:
{{
  "hcp_name": "Dr. John Smith",
  "interaction_type": "Meeting",
  "date": "2026-07-15",
  "time": null,
  "attendees": null,
  "topics_discussed": "CardioPlus medication",
  "materials_shared": "Brochures",
  "samples_distributed": null,
  "outcomes": null,
  "follow_up_actions": null,
  "sentiment": "Positive",
  "ai_summary": "Met with Dr. Smith to discuss CardioPlus."
}}

If a field cannot be determined from the message, use null. Do NOT fabricate data."""
        
        raw_response = groq_service.generate_chat_response(prompt)
        
        # Clean response - extract JSON
        cleaned = raw_response.strip()
        # Remove markdown code fences if present
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        
        try:
            extracted = json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback: try to find JSON in the response
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                try:
                    extracted = json.loads(json_match.group())
                except json.JSONDecodeError:
                    extracted = {}
            else:
                extracted = {}
        
        # Also get suggested tools based on intent
        suggested_tools = _detect_tools(message)
        
        # If regex found HCP name but LLM didn't, use regex result
        if not extracted.get("hcp_name") and hcp_name:
            extracted["hcp_name"] = hcp_name
        if not extracted.get("interaction_type") and interaction_type:
            extracted["interaction_type"] = interaction_type
        if not extracted.get("date") and date_str:
            extracted["date"] = date_str
        # Regex for materials/samples is more reliable than LLM
        if not extracted.get("materials_shared") and materials_shared:
            extracted["materials_shared"] = materials_shared
        if not extracted.get("samples_distributed") and samples_distributed:
            extracted["samples_distributed"] = samples_distributed

        # If we have hcp_context, try to resolve hcp_name to hcp_id
        hcp_id = None
        if request.hcp_context and extracted.get("hcp_name"):
            hcp_name_from_msg = extracted["hcp_name"].lower()
            ctx_name = request.hcp_context.get("name", "").lower()
            if hcp_name_from_msg in ctx_name or ctx_name in hcp_name_from_msg:
                hcp_id = request.hcp_context.get("id")
        
        return ExtractionResponse(
            hcp_name=extracted.get("hcp_name"),
            hcp_id=hcp_id,
            interaction_type=extracted.get("interaction_type"),
            date=extracted.get("date"),
            time=extracted.get("time"),
            attendees=extracted.get("attendees"),
            topics_discussed=extracted.get("topics_discussed"),
            materials_shared=extracted.get("materials_shared"),
            samples_distributed=extracted.get("samples_distributed"),
            outcomes=extracted.get("outcomes"),
            follow_up_actions=extracted.get("follow_up_actions"),
            sentiment=extracted.get("sentiment"),
            ai_summary=extracted.get("ai_summary"),
            suggested_tools=suggested_tools,
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting data: {str(e)}",
        )


def _extract_hcp_name_regex(message: str) -> Optional[str]:
    """Fast regex-based HCP name extraction."""
    # Pattern 1: Dr. Name Surname
    m = re.search(r'(Dr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', message)
    if m:
        return m.group(1).strip()
    # Pattern 2: Dr. Name
    m = re.search(r'(Dr\.?\s+[A-Z][a-z]+)', message)
    if m:
        return m.group(1).strip()
    return None


def _extract_interaction_type_regex(message: str) -> Optional[str]:
    """Fast regex-based interaction type extraction."""
    msg = message.lower()
    if "meeting" in msg or " met " in msg or " met" in msg.split() or "met with" in msg or "visited" in msg:
        return "Meeting"
    if "call" in msg or "phone" in msg or "called" in msg:
        return "Call"
    if "email" in msg:
        return "Email"
    if "conference" in msg:
        return "Conference"
    return None


def _extract_date_regex(message: str) -> Optional[str]:
    """Fast regex-based date extraction."""
    msg = message.lower()
    today = date.today()
    
    if "today" in msg:
        return today.isoformat()
    if "yesterday" in msg:
        return (today - timedelta(days=1)).isoformat()
    
    # Try to find YYYY-MM-DD
    m = re.search(r'(\d{4}-\d{2}-\d{2})', message)
    if m:
        return m.group(1)
    
    return None


def _extract_materials_regex(message: str) -> Optional[str]:
    """Extract materials shared mentions."""
    msg = message.lower()
    if "brochure" in msg or "brochures" in msg:
        return "Brochures"
    if "material" in msg or "materials" in msg:
        return "Materials"
    return None


def _extract_samples_regex(message: str) -> Optional[str]:
    """Extract samples distributed mentions."""
    msg = message.lower()
    if "sample" in msg or "samples" in msg:
        # Try to extract the specific product name before "samples"
        # Match up to 2 words before "samples" to capture "product samples"
        m = re.search(r'((?:\w+\s+)?\w+)\s+samples?\b', msg)
        if m:
            captured = m.group(1).strip()
            # Ignore common noise words (verbs, articles, prepositions)
            noise_words = {"some", "the", "a", "any", "gave", "provided", "shared", "with", "of", "i", "had", "have", "has"}
            words = captured.split()
            # Filter out noise words from the captured phrase
            filtered = [w for w in words if w not in noise_words]
            if filtered:
                return " ".join(filtered).title()
            return "Product Samples"
        return "Product Samples"
    return None


def _detect_tools(message: str) -> list:
    """Detect which tools might be relevant based on message intent."""
    msg = message.lower()
    tools = ["log_interaction"]
    
    log_indicators = ["i met", "i had a", "i attended", "i spoke with", "i called",
                      "i visited", "just met", "just had", "we discussed",
                      "we talked about", "i discussed", "the meeting went"]
    
    if any(indicator in msg for indicator in log_indicators):
        tools = ["log_interaction"]
    
    if any(w in msg for w in ["follow", "suggest", "next step", "next action"]):
        tools.append("suggest_follow_up")
    
    if any(w in msg for w in ["search", "find", "look for"]):
        tools = ["search_hcp"]
    
    if any(w in msg for w in ["recommend", "material", "brochure", "sample"]):
        tools.append("get_recommended_materials")
    
    if any(w in msg for w in ["history", "past", "previous", "what happened", "show me"]):
        tools.append("get_interaction_history")
    
    return tools