import asyncio

from doc_process_studio.services.chat import sessions as sessions_module


def test_delete_chat_session_also_cleans_agent_traces(monkeypatch) -> None:
    async def fake_delete_chat_session_records(session_id: str) -> bool:
        assert session_id == "conversation-1"
        return False

    def fake_delete_attachments_for_conversation(conversation_id: str) -> int:
        assert conversation_id == "conversation-1"
        return 0

    async def fake_delete_agent_traces_for_conversation(
        *,
        conversation_id: str,
    ) -> int:
        assert conversation_id == "conversation-1"
        return 2

    monkeypatch.setattr(
        sessions_module,
        "delete_chat_session_records",
        fake_delete_chat_session_records,
    )
    monkeypatch.setattr(
        sessions_module,
        "delete_attachments_for_conversation",
        fake_delete_attachments_for_conversation,
    )
    monkeypatch.setattr(
        sessions_module,
        "delete_agent_traces_for_conversation",
        fake_delete_agent_traces_for_conversation,
    )

    async def _run() -> None:
        deleted = await sessions_module.delete_chat_session("conversation-1")
        assert deleted is True

    asyncio.run(_run())
