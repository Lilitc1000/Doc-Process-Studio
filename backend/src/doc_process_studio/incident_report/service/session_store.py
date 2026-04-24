from ..models.incident_report import (
    IncidentReportSessionSnapshot,
    IncidentReportSessionSummary,
)
from ...core.session_store import RedisSessionStore

_incident_store = RedisSessionStore[
    IncidentReportSessionSummary, IncidentReportSessionSnapshot
](
    namespace="incident-report",
    summary_model=IncidentReportSessionSummary,
    snapshot_model=IncidentReportSessionSnapshot,
)

list_incident_session_ids = _incident_store.list_session_ids
load_incident_session_summary = _incident_store.load_summary
load_incident_session_snapshot = _incident_store.load_snapshot
save_incident_session_summary = _incident_store.save_summary
save_incident_session_snapshot = _incident_store.save_snapshot
touch_incident_session_index = _incident_store.touch_index
delete_incident_session_records = _incident_store.delete_session
