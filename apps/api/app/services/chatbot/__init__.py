"""Local public-knowledge prototype; deliberately not registered with FastAPI."""

from app.services.chatbot.service import ChatbotService

__all__ = ["ChatbotService"]
