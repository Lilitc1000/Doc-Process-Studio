import importlib.util
from pathlib import Path


def _load_incident_report_module():
    script_path = Path(
        '/workspace/backend/src/doc_process_studio/skills/incident-report/scripts/generate_incident_report.py'
    )
    spec = importlib.util.spec_from_file_location('incident_report_script', script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalize_incident_data_handles_string_structures():
    module = _load_incident_report_module()
    payload = {
        'reference_no': 'TEST-INCIDENT-001',
        'detailed_description': 'Payment service outage',
        'impact': 'Users cannot complete payment transactions',
        'event_sequence': ['14:32 monitor alert triggered'],
        'immediate_actions': ['restarted payment worker'],
        'preventive_actions': ['add worker health-check alert'],
        'root_cause': {
            'technical': 'Missing DB index caused full table scan',
            'proximate_cause': 'SQL query deployed without performance check',
            'process_gap': 'Release checklist missing DBA review',
        },
        'severity': 'P2',
        'start_time': '08/04/2026 09:10',
        'detection_time': '08/04/2026 09:12',
        'resolution_time': '08/04/2026 09:40',
    }

    normalized = module.normalize_incident_data(payload)

    assert isinstance(normalized['impact'], dict)
    assert isinstance(normalized['impact']['business_impact'], list)
    assert isinstance(normalized['event_sequence'], list)
    assert isinstance(normalized['immediate_actions'], list)
    assert isinstance(normalized['preventive_actions'], list)
    assert normalized['event_sequence'][0]['event'] == '14:32 monitor alert triggered'
    assert isinstance(normalized['key_facts'], dict)
    assert isinstance(normalized['impact'], dict)
    assert normalized['reporting_person'] != ''
    assert normalized['site_id'] != ''
    assert normalized['fault_details'] != ''
    assert normalized['status'] != ''
    assert normalized['fault_date'] != ''
    assert normalized['fault_time'] != ''
    assert normalized['root_cause'] == 'Missing DB index caused full table scan'
    assert normalized['trigger'] == 'SQL query deployed without performance check'
    assert normalized['root_cause_evidence'] == 'Release checklist missing DBA review'


def test_generate_form_accepts_mixed_payload_without_crash():
    module = _load_incident_report_module()
    payload = {
        'reference_no': 'TEST-INCIDENT-002',
        'impact': 'Regional service disruption',
        'event_sequence': ['Detected by monitoring'],
        'immediate_actions': ['restart service'],
    }
    normalized = module.normalize_incident_data(payload)
    generator = module.FaultLogFormGenerator()

    document = generator.generate_form(normalized, output_path=None)
    assert document is not None
