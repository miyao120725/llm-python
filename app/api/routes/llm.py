from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.deps import get_container
from app.container import AppContainer
from app.schemas.llm import (
    ChatRequest,
    ConversationCreateResponse,
    ConversationHistoryResponse,
    ConversationListItem,
    ConversationListResponse,
    EnhancePromptRequest,
    EnhancePromptResponse,
    HistoryMessage,
)

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/conversations", response_model=ConversationCreateResponse)
async def create_conversation(
    container: AppContainer = Depends(get_container),
) -> ConversationCreateResponse:
    conversation = await container.conversations.create()
    return ConversationCreateResponse(
        conversation_id=conversation.conversation_id,
        created_at=conversation.created_at,
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=50),
    container: AppContainer = Depends(get_container),
) -> ConversationListResponse:
    items = await container.conversations.list_recent(limit)
    return ConversationListResponse(
        items=[
            ConversationListItem(
                conversation_id=item.conversation_id,
                title=item.title,
                created_at=item.created_at,
                updated_at=item.updated_at,
                last_role=item.last_role,
                last_content=item.last_content,
                message_count=item.message_count,
            )
            for item in items
        ]
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
) -> ConversationHistoryResponse:
    conversation = await container.conversations.get(conversation_id)
    return ConversationHistoryResponse(
        conversation_id=conversation.conversation_id,
        messages=[
            HistoryMessage(role=item.role, content=item.content, created_at=item.created_at)
            for item in conversation.messages
        ],
    )


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    container: AppContainer = Depends(get_container),
):
    service = container.conversations
    if payload.stream:
        return StreamingResponse(
            service.stream(
                messages=payload.messages,
                conversation_id=payload.conversation_id,
                temperature=payload.temperature,
                model=payload.model,
                thinking=payload.thinking,
                search=payload.search,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    return await service.complete(
        messages=payload.messages,
        conversation_id=payload.conversation_id,
        temperature=payload.temperature,
        model=payload.model,
        thinking=payload.thinking,
        search=payload.search,
    )


@router.post("/enhance-prompt", response_model=EnhancePromptResponse)
async def enhance_prompt(
    payload: EnhancePromptRequest,
    container: AppContainer = Depends(get_container),
) -> EnhancePromptResponse:
    provider = container.providers.llm
    enhanced = await provider.enhance_prompt(payload.prompt, payload.mode)
    return EnhancePromptResponse(
        original=payload.prompt,
        enhanced=enhanced,
        mocked=provider.mocked,
    )
