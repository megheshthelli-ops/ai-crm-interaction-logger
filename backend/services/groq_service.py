import json
from groq import Groq

from app.settings import settings


class GroqService:
    def __init__(self):
        api_key = settings.groq_api_key.strip()
        self.model = settings.groq_model
        self.disabled = False

        if not settings.groq_configured:
            self.client = None
            self.disabled = True
            print(
                "Warning: GROQ_API_KEY is not configured or is a placeholder. "
                "Using offline fallback responses."
            )
        else:
            self.client = Groq(api_key=api_key)

    def _chat(self, messages: list[dict], system: str | None = None) -> str:
        if system:
            messages = [{"role": "system", "content": system}, *messages]

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return completion.choices[0].message.content or ""

    def summarize_interaction(self, raw_text: str) -> dict:
        """Use LLM to summarize interaction and extract key information."""
        if self.disabled:
            return self._offline_summary(raw_text)

        try:
            response_text = self._chat(
                [
                    {
                        "role": "user",
                        "content": f"""Analyze this HCP interaction and provide:
1. A concise summary (2-3 sentences)
2. Sentiment (Positive/Neutral/Negative)
3. Key topics discussed (list)
4. Recommended follow-up actions (list)

Interaction: {raw_text}

Format your response as JSON with keys: summary, sentiment, topics, follow_up_actions""",
                    }
                ]
            )

            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return self._parse_text_response(response_text)

        except Exception as e:
            print(f"Error in Groq summarization: {e}")
            return self._offline_summary(raw_text)

    def generate_chat_response(self, user_message: str, context: str = "") -> str:
        """Generate response for chat interface."""
        if self.disabled:
            return self._offline_chat_response(user_message)

        try:
            system_prompt = """You are an AI assistant helping healthcare field representatives log interactions with Healthcare Professionals (HCPs).
You help:
1. Extract interaction details (date, attendees, topics, outcomes)
2. Suggest follow-up actions
3. Identify key points and entities
4. Recommend materials to share

Be concise, professional, and focused on sales/relationship management."""

            user_content = f"{context}\n\nUser: {user_message}" if context else user_message
            return self._chat(
                [{"role": "user", "content": user_content}],
                system=system_prompt,
            )

        except Exception as e:
            print(f"Error in Groq chat: {e}")
            return self._offline_chat_response(user_message)

    def extract_entities(self, text: str) -> dict:
        """Extract named entities from interaction text."""
        if self.disabled:
            return self._offline_extract_entities(text)

        try:
            response_text = self._chat(
                [
                    {
                        "role": "user",
                        "content": f"""Extract entities from this text. Return as JSON with categories:
- names (HCP names)
- medications
- diseases
- institutions
- products

Text: {text}

Return only valid JSON.""",
                    }
                ]
            )

            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return {"raw": response_text}

        except Exception as e:
            print(f"Error in entity extraction: {e}")
            return self._offline_extract_entities(text)

    def _offline_summary(self, raw_text: str) -> dict:
        return {
            "summary": raw_text[:150] if raw_text else "No content provided.",
            "sentiment": "Neutral",
            "topics": ["General discussion"],
            "follow_up_actions": ["Follow up with the HCP as needed."],
        }

    def _offline_chat_response(self, user_message: str) -> str:
        return (
            "Groq API is not configured. I received your message and can help "
            f"structure it locally. You said: \"{user_message[:200]}\""
        )

    def _offline_extract_entities(self, text: str) -> dict:
        return {
            "names": [],
            "medications": [],
            "diseases": [],
            "institutions": [],
            "products": [],
        }

    def _parse_text_response(self, text: str) -> dict:
        """Parse non-JSON text response."""
        return {
            "summary": text[:200],
            "sentiment": "Neutral",
            "topics": [],
            "follow_up_actions": [],
        }
