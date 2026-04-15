from ...models.conversation.sessions import ChatSessionSnapshot, ChatSessionSummary
from ..infra.session_store import RedisSessionStore

_chat_store = RedisSessionStore[ChatSessionSummary, ChatSessionSnapshot](
    namespace="chat",
    summary_model=ChatSessionSummary,
    snapshot_model=ChatSessionSnapshot,
)

list_chat_session_ids = _chat_store.list_session_ids
load_chat_session_summary = _chat_store.load_summary
load_chat_session_snapshot = _chat_store.load_snapshot
save_chat_session_summary = _chat_store.save_summary
save_chat_session_snapshot = _chat_store.save_snapshot
touch_chat_session_index = _chat_store.touch_index
delete_chat_session_records = _chat_store.delete_session
