from abc import ABC, abstractmethod

from app.domain.models import Conversation, ConversationSummary


class ConversationStore(ABC):
    backend: str = "conversations"

    @abstractmethod
    async def create(self) -> Conversation:
        raise NotImplementedError

    @abstractmethod
    async def get(self, conversation_id: str) -> Conversation:
        raise NotImplementedError

    @abstractmethod
    async def add_message(self, conversation_id: str, role: str, content: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_recent(self, limit: int) -> list[ConversationSummary]:
        raise NotImplementedError

    async def aclose(self) -> None:
        return None
