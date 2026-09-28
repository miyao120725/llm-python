import uuid
from datetime import datetime
from pathlib import Path

import aiosqlite

from app.core.exceptions import ConversationNotFoundError
from app.domain.models import Conversation, ConversationMessage, ConversationSummary, utc_now
from app.ports.conversations import ConversationStore

_CREATE_CONVERSATIONS = """
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
)
"""

_CREATE_MESSAGES = """
CREATE TABLE IF NOT EXISTS conversation_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
)
"""


class SqliteConversationStore(ConversationStore):
    backend = "sqlite"

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ready = False

    async def init(self) -> None:
        if self._ready:
            return
        async with aiosqlite.connect(self.path) as db:
            await db.execute(_CREATE_CONVERSATIONS)
            await db.execute(_CREATE_MESSAGES)
            await db.commit()
        self._ready = True

    async def create(self) -> Conversation:
        await self.init()
        record = Conversation(conversation_id=uuid.uuid4().hex)
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO conversations (conversation_id, created_at) VALUES (?, ?)",
                (record.conversation_id, record.created_at.isoformat()),
            )
            await db.commit()
        return record

    async def get(self, conversation_id: str) -> Conversation:
        await self.init()
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT conversation_id, created_at FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                raise ConversationNotFoundError(conversation_id)
            msg_cursor = await db.execute(
                """
                SELECT role, content, created_at
                FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation_id,),
            )
            messages = [
                ConversationMessage(
                    role=item["role"],
                    content=item["content"],
                    created_at=datetime.fromisoformat(item["created_at"]),
                )
                for item in await msg_cursor.fetchall()
            ]
        return Conversation(
            conversation_id=row["conversation_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            messages=messages,
        )

    async def add_message(self, conversation_id: str, role: str, content: str) -> None:
        await self.get(conversation_id)
        now = utc_now().isoformat()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO conversation_messages (conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, role, content, now),
            )
            await db.commit()

    async def list_recent(self, limit: int) -> list[ConversationSummary]:
        await self.init()
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT
                    c.conversation_id,
                    c.created_at,
                    (
                        SELECT m.created_at
                        FROM conversation_messages m
                        WHERE m.conversation_id = c.conversation_id
                        ORDER BY m.id DESC
                        LIMIT 1
                    ) AS updated_at,
                    (
                        SELECT m.content
                        FROM conversation_messages m
                        WHERE m.conversation_id = c.conversation_id AND m.role = 'user'
                        ORDER BY m.id ASC
                        LIMIT 1
                    ) AS title,
                    (
                        SELECT m.role
                        FROM conversation_messages m
                        WHERE m.conversation_id = c.conversation_id
                        ORDER BY m.id DESC
                        LIMIT 1
                    ) AS last_role,
                    (
                        SELECT m.content
                        FROM conversation_messages m
                        WHERE m.conversation_id = c.conversation_id
                        ORDER BY m.id DESC
                        LIMIT 1
                    ) AS last_content,
                    (
                        SELECT COUNT(*)
                        FROM conversation_messages m
                        WHERE m.conversation_id = c.conversation_id
                    ) AS message_count
                FROM conversations c
                WHERE EXISTS (
                    SELECT 1
                    FROM conversation_messages m
                    WHERE m.conversation_id = c.conversation_id
                )
                ORDER BY updated_at DESC, c.created_at DESC
                LIMIT ?
                """,
                (max(1, limit),),
            )
            rows = await cursor.fetchall()
        return [
            ConversationSummary(
                conversation_id=row["conversation_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                title=row["title"] or "",
                last_role=row["last_role"] or "",
                last_content=row["last_content"] or "",
                message_count=int(row["message_count"]),
            )
            for row in rows
        ]
