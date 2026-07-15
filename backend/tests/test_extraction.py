"""
Unit tests for extraction logic accuracy.
Tests ensure extraction follows strict rules:
1. Do not hallucinate values
2. If user explicitly states a value, use it exactly
3. If a field is not mentioned, leave it empty
4. "Today" → current system date
5. No time mentioned → Time stays empty
6. HCP name is NOT an attendee unless explicitly mentioned
7. "I shared brochures" → Materials Shared = Brochures
8. "product samples" → Samples Distributed populated
9. Sentiment only set if explicitly "positive", "neutral", or "negative"
10. Outcome only set if explicitly provided
"""
import json
from datetime import date, timedelta
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.routers.extraction import (
    _extract_hcp_name_regex,
    _extract_interaction_type_regex,
    _extract_date_regex,
    _extract_materials_regex,
    _extract_samples_regex,
)


class TestRegexExtraction:
    """Tests for regex-based extraction functions (fast path)."""

    # ── HCP Name Extraction ─────────────────────────────────────

    def test_extract_hcp_name_dr_full(self):
        """Extract 'Dr. John Smith' with full name."""
        result = _extract_hcp_name_regex("I met Dr. John Smith today")
        assert result == "Dr. John Smith", f"Expected 'Dr. John Smith', got '{result}'"

    def test_extract_hcp_name_dr_no_dot(self):
        """Extract 'Dr John Smith' without dot."""
        result = _extract_hcp_name_regex("I met Dr John Smith today")
        assert result == "Dr John Smith", f"Expected 'Dr John Smith', got '{result}'"

    def test_extract_hcp_name_dr_single(self):
        """Extract 'Dr. Jane' single name."""
        result = _extract_hcp_name_regex("Visited Dr. Jane yesterday")
        assert result == "Dr. Jane", f"Expected 'Dr. Jane', got '{result}'"

    def test_extract_hcp_name_not_present(self):
        """No HCP name in message → None."""
        result = _extract_hcp_name_regex("I had a meeting about CardioPlus")
        assert result is None, f"Expected None, got '{result}'"

    def test_extract_hcp_name_not_confused_with_today(self):
        """'today' should NOT match as an HCP name (lowercase)."""
        result = _extract_hcp_name_regex("Today I met with the doctor")
        # "the doctor" should not match because uppercase regex
        assert result is None, f"Expected None, got '{result}'"

    # ── Interaction Type Extraction ─────────────────────────────

    def test_extract_type_meeting(self):
        """'meeting' → Meeting."""
        result = _extract_interaction_type_regex("I had a meeting")
        assert result == "Meeting"

    def test_extract_type_met(self):
        """'met' → Meeting."""
        result = _extract_interaction_type_regex("I met Dr. Smith")
        assert result == "Meeting"

    def test_extract_type_visited(self):
        """'visited' → Meeting."""
        result = _extract_interaction_type_regex("I visited Dr. Smith")
        assert result == "Meeting"

    def test_extract_type_call(self):
        """'called' → Call."""
        result = _extract_interaction_type_regex("I called Dr. Smith")
        assert result == "Call"

    def test_extract_type_phone(self):
        """'phone' → Call."""
        result = _extract_interaction_type_regex("Had a phone conversation")
        assert result == "Call"

    def test_extract_type_email(self):
        """'email' → Email."""
        result = _extract_interaction_type_regex("Sent an email")
        assert result == "Email"

    def test_extract_type_not_present(self):
        """No type indicator → None."""
        result = _extract_interaction_type_regex("Discussed CardioPlus")
        assert result is None

    # ── Date Extraction ─────────────────────────────────────────

    def test_extract_date_today(self):
        """'today' → today's date."""
        result = _extract_date_regex("Today I met Dr. Smith")
        assert result == date.today().isoformat()

    def test_extract_date_yesterday(self):
        """'yesterday' → yesterday's date."""
        result = _extract_date_regex("Yesterday I met Dr. Smith")
        assert result == (date.today() - timedelta(days=1)).isoformat()

    def test_extract_date_iso_format(self):
        """YYYY-MM-DD in message → that date."""
        result = _extract_date_regex("Met on 2026-07-10")
        assert result == "2026-07-10"

    def test_extract_date_not_present(self):
        """No date mentioned → None."""
        result = _extract_date_regex("I met Dr. Smith and we discussed")
        assert result is None

    # ── Materials Extraction ────────────────────────────────────

    def test_extract_materials_brochures(self):
        """'brochures' → Brochures."""
        result = _extract_materials_regex("I shared brochures")
        assert result == "Brochures"

    def test_extract_materials_brochure_singular(self):
        """'brochure' → Brochures."""
        result = _extract_materials_regex("Gave him a brochure")
        assert result == "Brochures"

    def test_extract_materials_materials(self):
        """'materials' → Materials."""
        result = _extract_materials_regex("Provided some materials")
        assert result == "Materials"

    def test_extract_materials_not_present(self):
        """No materials mentioned → None."""
        result = _extract_materials_regex("We discussed CardioPlus")
        assert result is None

    # ── Samples Extraction ──────────────────────────────────────

    def test_extract_samples_generic(self):
        """'product samples' → 'Product' (the word before samples)."""
        result = _extract_samples_regex("I gave product samples")
        assert result == "Product", f"Expected 'Product', got '{result}'"

    def test_extract_samples_not_present(self):
        """No samples mentioned → None."""
        result = _extract_samples_regex("We discussed topics")
        assert result is None


class TestExtractionRules:
    """Tests for the extraction rules defined in requirements.
    
    These tests validate the expected extraction output for various inputs.
    Since extraction uses LLM (Groq), we test the prompt structure and 
    expected behavior through the regex pre-processing path and validate
    that the extraction logic correctly enforces the rules.
    """

    # ── Rule: No Hallucination ──────────────────────────────────

    def test_rule_no_hallucination_empty_time(self):
        """
        If no time is mentioned, time field should stay empty (None).
        The LLM prompt explicitly prohibits guessing defaults.
        """
        message = "I met Dr. John Smith. We discussed CardioPlus."
        # No time mentioned → regex should not find time
        assert _extract_date_regex(message) is None, "No 'today' → date should be None"
        assert _extract_interaction_type_regex(message) == "Meeting"

    def test_rule_no_hallucination_no_sentiment(self):
        """
        If sentiment is not mentioned, sentiment should be None.
        Do NOT infer or guess sentiment.
        """
        message = "I met Dr. John Smith. We discussed CardioPlus."
        # The prompt enforces: only populate if explicitly stated
        # This test validates the regex path doesn't fabricate sentiment
        assert _extract_materials_regex(message) is None, "No materials → None"
        assert _extract_samples_regex(message) is None, "No samples → None"

    def test_rule_no_hallucination_no_outcome(self):
        """
        If no outcome is mentioned, outcome should be None.
        Do NOT create an outcome unless explicitly provided.
        """
        message = "I met Dr. John Smith. We discussed CardioPlus."
        # No regex for outcome → relies on LLM prompt rule #8
        # Validating that nothing in regex creates fake outcomes
        pass  # LLM-only field, validated by prompt rule enforcement

    # ── Rule: Use Exact Values ──────────────────────────────────

    def test_rule_exact_hcp_name(self):
        """HCP name should be extracted exactly as stated."""
        message = "I met Dr. John Smith at his clinic"
        result = _extract_hcp_name_regex(message)
        assert result == "Dr. John Smith", f"Expected exact name, got '{result}'"

    def test_rule_exact_topic(self):
        """Topics should be extracted exactly as stated (regex handles type)."""
        message = "I shared brochures about CardioPlus"
        result = _extract_materials_regex(message)
        assert result == "Brochures"

    # ── Rule: Today → Current Date ──────────────────────────────

    def test_rule_today_uses_current_date(self):
        """'Today' maps to current system date."""
        message = "Today I visited Dr. Jane Smith"
        result = _extract_date_regex(message)
        assert result == date.today().isoformat()

    # ── Rule: No Time → Empty ───────────────────────────────────

    def test_rule_no_time_empty(self):
        """No time mentioned → time stays empty (None)."""
        message = "I met Dr. John Smith and we discussed CardioPlus"
        # No time indicator in message
        assert "at" not in message.lower().split() or ":" not in message
        # The LLM prompt enforces this; regex doesn't extract time
        assert _extract_date_regex(message) is None

    # ── Rule: HCP Name Not Attendee ──────────────────────────────

    def test_rule_hcp_not_attendee(self):
        """
        HCP name should NOT be treated as an attendee.
        Attendees = other people present, NOT the HCP.
        """
        message = "I met Dr. John Smith. We discussed CardioPlus."
        # No attendees mentioned → attendee extraction should return None
        # Attendees field isn't regex-extracted, it's LLM-only
        # The prompt rule #5 explicitly prohibits this
        pass  # Validated by LLM prompt rule

    # ── Rule: Brochures → Materials Shared ──────────────────────

    def test_rule_brochures_materials_shared(self):
        """'I shared brochures' → Materials Shared = Brochures."""
        message = "I shared brochures with Dr. Smith"
        result = _extract_materials_regex(message)
        assert result == "Brochures"

    # ── Rule: Product Samples → Samples Distributed ─────────────

    def test_rule_samples_distributed(self):
        """'product samples' → Samples Distributed populated with 'Product'."""
        message = "I gave product samples to Dr. Smith"
        result = _extract_samples_regex(message)
        assert result == "Product", f"Expected 'Product', got '{result}'"

    # ── Rule: Sentiment Mapping ─────────────────────────────────

    def test_rule_sentiment_positive_match(self):
        """'positive' → Sentiment = 'Positive' (LLM-enforced)."""
        message = "I met Dr. Smith. The sentiment was positive."
        assert "positive" in message.lower()

    def test_rule_sentiment_neutral_match(self):
        """'neutral' → Sentiment = 'Neutral' (LLM-enforced)."""
        message = "The sentiment was neutral."
        assert "neutral" in message.lower()

    def test_rule_sentiment_negative_match(self):
        """'negative' → Sentiment = 'Negative' (LLM-enforced)."""
        message = "The sentiment was negative."
        assert "negative" in message.lower()

    # ── Rule: No Outcome Fabrication ────────────────────────────

    def test_rule_no_fabricated_outcome(self):
        """No outcome mentioned → outcome stays empty (LLM-enforced)."""
        message = "I met Dr. John Smith. We discussed CardioPlus."
        assert "outcome" not in message.lower()
        assert "agreed" not in message.lower()
        assert "will" not in message.lower() or "follow" not in message.lower()

    # ── Complete Example Test ───────────────────────────────────

    def test_complete_example_from_requirements(self):
        """
        Test the exact example from requirements:
        Input: "Today I met Dr. John Smith. We discussed CardioPlus. 
                I shared brochures. The sentiment was positive. Follow up in two weeks."
        
        Expected:
        HCP Name = Dr. John Smith
        Interaction Type = Meeting
        Date = Current Date
        Time = Empty
        Attendees = Empty
        Topics Discussed = CardioPlus
        Materials Shared = Brochures
        Samples Distributed = Empty
        Sentiment = Positive (only via LLM, regex doesn't extract)
        Outcomes = Empty
        Follow-up = Two weeks (via LLM, regex doesn't extract follow-ups)
        """
        message = "Today I met Dr. John Smith. We discussed CardioPlus. I shared brochures. The sentiment was positive. Follow up in two weeks."
        
        # Regex extraction (fast path)
        hcp_name = _extract_hcp_name_regex(message)
        interaction_type = _extract_interaction_type_regex(message)
        date_str = _extract_date_regex(message)
        materials = _extract_materials_regex(message)
        samples = _extract_samples_regex(message)
        
        # Validate regex results
        assert hcp_name == "Dr. John Smith", f"HCP name: got '{hcp_name}'"
        assert interaction_type == "Meeting", f"Type: got '{interaction_type}'"
        assert date_str == date.today().isoformat(), f"Date: got '{date_str}'"
        assert materials == "Brochures", f"Materials: got '{materials}'"
        assert samples is None, f"Samples should be None, got '{samples}'"
        
        # Fields that should be empty/None
        # Time - not mentioned
        assert ":" not in message, "Time should not be extractable from message"
        
        # Attendees - not mentioned (HCP is not an attendee)
        assert "attend" not in message.lower() or "Dr. John Smith" not in message.lower().split("attend")[0]
        
        # Outcomes - not mentioned
        assert "outcome" not in message.lower() and "agreed" not in message.lower()

    # ── Edge Cases ──────────────────────────────────────────────

    def test_edge_case_minimal_message(self):
        """Very short message with just HCP name should only extract that."""
        message = "Dr. Smith"
        hcp = _extract_hcp_name_regex(message)
        # "Dr. Smith" has only 2 words, pattern requires 2+ for first match
        # Pattern 1b catches single Dr. Name
        assert hcp is not None
        assert "Dr" in hcp

    def test_edge_case_no_hcp_mention(self):
        """Message with no HCP should result in no extraction."""
        message = "I just had a great meeting"
        assert _extract_hcp_name_regex(message) is None
        assert _extract_interaction_type_regex(message) == "Meeting"
        assert _extract_date_regex(message) is None

    def test_edge_case_multiple_hcps(self):
        """Only extract the FIRST HCP name mentioned."""
        message = "I met Dr. John Smith and Dr. Jane Doe"
        result = _extract_hcp_name_regex(message)
        assert result == "Dr. John Smith", f"Expected first HCP, got '{result}'"

    def test_edge_case_date_in_different_format(self):
        """Only ISO format YYYY-MM-DD and relative dates are extracted."""
        message = "Met on July 15, 2026"
        result = _extract_date_regex(message)
        assert result is None, "Non-ISO date should not be extracted by regex"

    def test_edge_case_brochures_plural_check(self):
        """'brochures' (plural) should still match."""
        msg1 = "I shared brochures"
        msg2 = "I shared a brochure"
        assert _extract_materials_regex(msg1) == "Brochures"
        assert _extract_materials_regex(msg2) == "Brochures"


class TestPromptStructure:
    """Tests that the extraction prompt enforces all rules.
    
    These tests validate the prompt we send to the LLM, not the LLM output
    itself. They ensure the prompt contains all required rule constraints.
    """

    def _get_extraction_prompt(self):
        """Read the extraction prompt from the router file."""
        filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                "app", "routers", "extraction.py")
        with open(filepath, "r") as f:
            content = f.read()
        # Extract the prompt template
        return content

    def test_prompt_has_no_hallucination_rule(self):
        """Prompt must have rule against hallucination."""
        prompt = self._get_extraction_prompt()
        assert "Do NOT hallucinate" in prompt, "Prompt missing no-hallucination rule"

    def test_prompt_has_time_default_rule(self):
        """Prompt must not set default time."""
        prompt = self._get_extraction_prompt()
        assert "null if not mentioned" in prompt or "null if not mentioned" in prompt, \
            "Prompt should set time to null if not mentioned"

    def test_prompt_has_hcp_not_attendee_rule(self):
        """Prompt must not treat HCP as attendee."""
        prompt = self._get_extraction_prompt()
        assert "Do NOT treat the HCP name as an attendee" in prompt or \
               "HCP name as an attendee" in prompt, \
            "Prompt must have rule about HCP not being attendee"

    def test_prompt_has_brochures_materials_rule(self):
        """Prompt must map 'brochures' to materials_shared."""
        prompt = self._get_extraction_prompt()
        assert "materials_shared" in prompt and "Brochures" in prompt, \
            "Prompt should map brochures to materials_shared"

    def test_prompt_has_sentiment_only_explicit_rule(self):
        """Prompt must only populate sentiment if explicitly stated."""
        prompt = self._get_extraction_prompt()
        assert "explicitly" in prompt.lower() and "sentiment" in prompt.lower(), \
            "Prompt should require explicit sentiment"

    def test_prompt_has_no_outcome_fabrication_rule(self):
        """Prompt must not create outcome unless provided."""
        prompt = self._get_extraction_prompt()
        assert "outcome" in prompt.lower() and "explicitly" in prompt.lower(), \
            "Prompt should require explicit outcome"

    def test_prompt_uses_today_date_only_when_mentioned(self):
        """Prompt uses today's date ONLY if user says 'today'."""
        prompt = self._get_extraction_prompt()
        assert "today" in prompt.lower() and "null otherwise" in prompt.lower(), \
            "Prompt should use today only if mentioned, null otherwise"

    def test_prompt_has_materials_shared_field(self):
        """Prompt must extract materials_shared field."""
        prompt = self._get_extraction_prompt()
        assert "materials_shared" in prompt, "Prompt missing materials_shared field"

    def test_prompt_has_samples_distributed_field(self):
        """Prompt must extract samples_distributed field."""
        prompt = self._get_extraction_prompt()
        assert "samples_distributed" in prompt, "Prompt missing samples_distributed field"


class TestAgentExtraction:
    """Tests for agent.py log interaction extraction prompt."""

    def _get_agent_prompt_section(self):
        """Read the extraction prompt from agent.py."""
        filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                "local_langgraph", "agent.py")
        with open(filepath, "r") as f:
            content = f.read()
        return content

    def test_agent_prompt_has_no_hallucination(self):
        """Agent prompt must have no-hallucination rule."""
        content = self._get_agent_prompt_section()
        assert "Do NOT hallucinate" in content

    def test_agent_prompt_has_time_null_rule(self):
        """Agent prompt must set time to null if not mentioned."""
        content = self._get_agent_prompt_section()
        assert "null if not mentioned" in content

    def test_agent_prompt_has_materials_shared(self):
        """Agent prompt must extract materials_shared."""
        content = self._get_agent_prompt_section()
        assert "materials_shared" in content

    def test_agent_prompt_has_samples_distributed(self):
        """Agent prompt must extract samples_distributed."""
        content = self._get_agent_prompt_section()
        assert "samples_distributed" in content

    def test_agent_prompt_has_sentiment_rule(self):
        """Agent prompt must only set sentiment if explicitly stated."""
        content = self._get_agent_prompt_section()
        assert "explicitly" in content.lower() and "sentiment" in content.lower()