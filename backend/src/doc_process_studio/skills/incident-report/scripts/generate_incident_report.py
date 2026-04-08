#!/usr/bin/env python3
"""
DAS Fault Log Form Generator
Generates Word document matching the exact DAS Fault Log Form template
"""

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from datetime import datetime
import json


def _to_text(value, default='N/A'):
    if value is None:
        return default
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or default
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        parts = [_to_text(item, '').strip() for item in value]
        parts = [part for part in parts if part]
        return '; '.join(parts) if parts else default
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            item_text = _to_text(item, '').strip()
            if not item_text:
                continue
            key_text = str(key).replace('_', ' ').strip()
            if key_text:
                parts.append(f'{key_text}: {item_text}')
            else:
                parts.append(item_text)
        return '；'.join(parts) if parts else default
    return str(value)


def _to_text_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [_to_text(item, '').strip() for item in value if _to_text(item, '').strip()]
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return []
        if '\n' in cleaned:
            return [line.strip('- ').strip() for line in cleaned.splitlines() if line.strip()]
        if ';' in cleaned:
            return [item.strip() for item in cleaned.split(';') if item.strip()]
        return [cleaned]
    return [_to_text(value)]


def _normalize_event_sequence(value):
    if value is None:
        return []
    if not isinstance(value, list):
        return [
            {
                'time': 'N/A',
                'event': _to_text(value),
                'evidence': 'N/A',
            }
        ]

    normalized = []
    for item in value:
        if isinstance(item, dict):
            normalized.append(
                {
                    'time': _to_text(item.get('time', 'N/A')),
                    'event': _to_text(
                        item.get('event', item.get('description', item.get('detail', 'N/A')))
                    ),
                    'evidence': _to_text(
                        item.get('evidence', item.get('source', item.get('proof', 'N/A')))
                    ),
                }
            )
            continue

        normalized.append(
            {
                'time': 'N/A',
                'event': _to_text(item),
                'evidence': 'N/A',
            }
        )
    return normalized


def _normalize_actions(value, action_type):
    if value is None:
        return []
    if not isinstance(value, list):
        return [
            {
                'action': _to_text(value),
                'by': 'N/A' if action_type == 'immediate' else '',
                'owner': 'N/A' if action_type != 'immediate' else '',
                'time': 'N/A' if action_type == 'immediate' else '',
                'due_date': 'N/A' if action_type != 'immediate' else '',
                'status': 'Planned' if action_type != 'immediate' else 'Completed',
            }
        ]

    normalized = []
    for item in value:
        if isinstance(item, dict):
            normalized.append(
                {
                    'action': _to_text(item.get('action', item.get('description', 'N/A'))),
                    'by': _to_text(item.get('by', item.get('taken_by', 'N/A'))),
                    'owner': _to_text(item.get('owner', item.get('by', 'N/A'))),
                    'time': _to_text(item.get('time', item.get('taken_at', 'N/A'))),
                    'due_date': _to_text(item.get('due_date', item.get('time', 'N/A'))),
                    'status': _to_text(item.get('status', 'N/A')),
                }
            )
            continue

        normalized.append(
            {
                'action': _to_text(item),
                'by': 'N/A',
                'owner': 'N/A',
                'time': 'N/A',
                'due_date': 'N/A',
                'status': 'N/A',
            }
        )
    return normalized


def _first_non_empty(*values, default='N/A'):
    for value in values:
        text_value = _to_text(value, '').strip()
        if text_value:
            return text_value
    return default


def _is_placeholder(value):
    normalized = _to_text(value, '').strip().lower()
    return normalized in {'', 'n/a', 'na', 'none', 'null', '-'}


def _split_date_time(date_time_value):
    normalized = _to_text(date_time_value, '').strip()
    if not normalized:
        return 'N/A', 'N/A'

    parts = normalized.split()
    if len(parts) >= 2:
        return parts[0], parts[1]

    if ':' in normalized and '/' not in normalized:
        return 'N/A', normalized

    return normalized, 'N/A'


def _build_reference_no():
    return f"DAS-{datetime.now().strftime('%Y%m%d')}-001"


def _has_valid_event_sequence(events):
    if not isinstance(events, list) or not events:
        return False
    for event in events:
        if not isinstance(event, dict):
            continue
        if not _is_placeholder(event.get('event')):
            return True
    return False


def _has_valid_actions(actions):
    if not isinstance(actions, list) or not actions:
        return False
    for action in actions:
        if not isinstance(action, dict):
            continue
        if not _is_placeholder(action.get('action')):
            return True
    return False


def validate_required_sections(data):
    missing_sections = []

    if _is_placeholder(data.get('detailed_description')):
        missing_sections.append('1. Description of the Incident')

    if any(
        _is_placeholder(data.get(field_name))
        for field_name in ('start_time', 'detection_time', 'resolution_time')
    ):
        missing_sections.append('2. Affected Date')

    if not _has_valid_event_sequence(data.get('event_sequence', [])):
        missing_sections.append('3. Event Sequence')

    impact = data.get('impact', {})
    if not isinstance(impact, dict) or _is_placeholder(impact.get('systems')) or _is_placeholder(
        impact.get('severity')
    ):
        missing_sections.append('4. Impact')

    if _is_placeholder(data.get('trigger')) or _is_placeholder(data.get('root_cause')):
        missing_sections.append('5. Root Cause')

    immediate_actions = data.get('immediate_actions', [])
    preventive_actions = data.get('preventive_actions', [])
    if not _has_valid_actions(immediate_actions) and not _has_valid_actions(preventive_actions):
        missing_sections.append('6. Follow-Up Actions')

    return missing_sections


def normalize_incident_data(raw_data):
    source = dict(raw_data) if isinstance(raw_data, dict) else {'detailed_description': _to_text(raw_data)}

    key_facts_raw = source.get('key_facts', {})
    key_facts_map = key_facts_raw if isinstance(key_facts_raw, dict) else {}
    key_facts_text = '' if isinstance(key_facts_raw, dict) else _to_text(key_facts_raw, '')

    impact_raw = source.get('impact', {})
    impact_map = impact_raw if isinstance(impact_raw, dict) else {}
    impact_text = '' if isinstance(impact_raw, dict) else _to_text(impact_raw, '')

    start_time = _first_non_empty(
        source.get('start_time'),
        source.get('incident_start_time'),
        default='N/A',
    )
    detection_time = _first_non_empty(
        source.get('detection_time'),
        source.get('detected_at'),
        default='N/A',
    )
    resolution_time = _first_non_empty(
        source.get('resolution_time'),
        source.get('resolved_at'),
        default='N/A',
    )
    derived_fault_date, derived_fault_time = _split_date_time(start_time)

    system_value = _first_non_empty(
        key_facts_map.get('system'),
        source.get('system'),
        default='N/A',
    )
    detection_method_value = _first_non_empty(
        key_facts_map.get('detection_method'),
        source.get('detection_method'),
        default='N/A',
    )
    symptoms_value = _first_non_empty(
        key_facts_map.get('symptoms'),
        key_facts_text,
        source.get('fault_details'),
        source.get('detailed_description'),
        default='N/A',
    )

    impact_systems = _first_non_empty(
        impact_map.get('systems'),
        impact_text,
        system_value,
        default='N/A',
    )
    impact_users = _first_non_empty(
        impact_map.get('users'),
        source.get('affected_users'),
        default='N/A',
    )
    impact_region = _first_non_empty(
        impact_map.get('region'),
        source.get('site_id'),
        source.get('location'),
        default='N/A',
    )
    impact_severity = _first_non_empty(
        impact_map.get('severity'),
        source.get('severity'),
        default='N/A',
    )
    business_impact = _to_text_list(
        impact_map.get('business_impact', source.get('business_impact', impact_text))
    )
    if not business_impact:
        business_impact = ['Service disruption reported']

    event_sequence = _normalize_event_sequence(source.get('event_sequence'))
    five_whys = _to_text_list(source.get('five_whys'))
    immediate_actions = _normalize_actions(source.get('immediate_actions'), 'immediate')
    preventive_actions = _normalize_actions(source.get('preventive_actions'), 'preventive')

    detailed_description = _first_non_empty(
        source.get('detailed_description'),
        source.get('description'),
        source.get('fault_details'),
        default='N/A',
    )
    root_cause_raw = source.get('root_cause')
    root_cause_map = root_cause_raw if isinstance(root_cause_raw, dict) else {}
    root_cause = _first_non_empty(
        root_cause_map.get('technical'),
        root_cause_map.get('root_cause'),
        root_cause_map.get('proximate_cause'),
        root_cause_raw,
        source.get('fault_cause'),
        default='N/A',
    )
    trigger_value = _first_non_empty(
        source.get('trigger'),
        root_cause_map.get('proximate_cause'),
        root_cause_map.get('trigger'),
        source.get('fault_cause'),
        default='N/A',
    )
    root_cause_evidence = _first_non_empty(
        source.get('root_cause_evidence'),
        root_cause_map.get('evidence'),
        root_cause_map.get('process_gap'),
        source.get('evidence'),
        default='See Fault Log Form Section B',
    )

    repair_details_default = (
        immediate_actions[0].get('action', 'N/A') if immediate_actions else detailed_description
    )

    normalized_data = {
        'reference_no': _first_non_empty(
            source.get('reference_no'),
            source.get('reference'),
            default=_build_reference_no(),
        ),
        'detailed_description': detailed_description,
        'key_facts': {
            'system': system_value,
            'detection_method': detection_method_value,
            'symptoms': symptoms_value,
        },
        'start_time': start_time,
        'detection_time': detection_time,
        'resolution_time': resolution_time,
        'total_duration': _first_non_empty(source.get('total_duration'), source.get('duration')),
        'fault_date': _first_non_empty(source.get('fault_date'), default=derived_fault_date),
        'fault_time': _first_non_empty(source.get('fault_time'), default=derived_fault_time),
        'event_sequence': event_sequence,
        'impact': {
            'systems': impact_systems,
            'users': impact_users,
            'region': impact_region,
            'severity': impact_severity,
            'business_impact': business_impact,
        },
        'trigger': trigger_value,
        'root_cause': root_cause,
        'root_cause_evidence': root_cause_evidence,
        'five_whys': five_whys,
        'immediate_actions': immediate_actions,
        'preventive_actions': preventive_actions,
        'allow_incomplete': bool(source.get('allow_incomplete', False)),
        'reporting_person': _first_non_empty(
            source.get('reporting_person'),
            detection_method_value,
        ),
        'verified_by': _first_non_empty(source.get('verified_by')),
        'site_id': _first_non_empty(source.get('site_id'), impact_region),
        'system': system_value,
        'location': _first_non_empty(source.get('location'), impact_region),
        'fault_details': _first_non_empty(source.get('fault_details'), detailed_description),
        'arrival_datetime': _first_non_empty(source.get('arrival_datetime'), start_time),
        'clearance_datetime': _first_non_empty(source.get('clearance_datetime'), resolution_time),
        'service_person': _first_non_empty(source.get('service_person')),
        'fault_cause': _first_non_empty(source.get('fault_cause'), root_cause),
        'materials_used': _first_non_empty(source.get('materials_used'), default='Nil'),
        'repair_details': _first_non_empty(source.get('repair_details'), repair_details_default),
        'contractor_staff': _first_non_empty(source.get('contractor_staff')),
        'contractor_date': _first_non_empty(
            source.get('contractor_date'),
            source.get('fault_date'),
            default=derived_fault_date,
        ),
        'status': _first_non_empty(source.get('status'), default='Fault has been Cleared'),
        'severity': impact_severity,
        'comments': _first_non_empty(source.get('comments')),
        'employer_rep': _first_non_empty(source.get('employer_rep')),
        'closeout_date': _first_non_empty(
            source.get('closeout_date'),
            source.get('fault_date'),
            default=derived_fault_date,
        ),
    }

    return normalized_data


class FaultLogFormGenerator:
    """Generates DAS Fault Log Form as Word document"""
    
    def __init__(self):
        self.doc = Document()
        self.setup_page()
        
    def setup_page(self):
        """Setup page margins"""
        sections = self.doc.sections
        for section in sections:
            section.top_margin = Cm(1.5)
            section.bottom_margin = Cm(1.5)
            section.left_margin = Cm(1.5)
            section.right_margin = Cm(1.5)
    
    def set_cell_shading(self, cell, color):
        """Set cell background color"""
        shading_elm = OxmlElement('w:shd')
        shading_elm.set(qn('w:fill'), color)
        cell._tc.get_or_add_tcPr().append(shading_elm)
    
    def set_cell_border(self, cell):
        """Set cell borders"""
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        tcBorders = OxmlElement('w:tcBorders')
        for border_name in ['top', 'left', 'bottom', 'right']:
            border = OxmlElement(f'w:{border_name}')
            border.set(qn('w:val'), 'single')
            border.set(qn('w:sz'), '4')
            border.set(qn('w:color'), '000000')
            tcBorders.append(border)
        tcPr.append(tcBorders)
    
    def format_cell_text(self, cell, text, bold=False, font_size=10):
        """Format cell text"""
        cell.text = text
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in paragraph.runs:
                run.font.name = 'Arial'
                run.font.size = Pt(font_size)
                run.bold = bold
    
    def generate_form(self, data, output_path=None):
        """Generate Fault Log Form"""
        
        # Title
        title = self.doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title.add_run('Fault Log Form')
        run.font.name = 'Arial'
        run.font.size = Pt(16)
        run.font.bold = True
        
        # Reference No. row
        ref_table = self.doc.add_table(rows=1, cols=4)
        ref_table.style = 'Table Grid'
        ref_cells = ref_table.rows[0].cells
        
        self.format_cell_text(ref_cells[0], 'Reference No.', bold=True, font_size=10)
        self.set_cell_shading(ref_cells[0], 'D9D9D9')
        self.set_cell_border(ref_cells[0])
        
        ref_cells[1].merge(ref_cells[3])
        self.format_cell_text(ref_cells[1], data.get('reference_no', ''), font_size=10)
        self.set_cell_border(ref_cells[1])
        
        self.doc.add_paragraph()  # Spacing
        
        # Section A: Fault Reporting
        section_a_table = self.doc.add_table(rows=1, cols=4)
        section_a_table.style = 'Table Grid'
        
        # Section A Header
        row = section_a_table.rows[0]
        row_cells = row.cells
        row_cells[0].merge(row_cells[3])
        self.format_cell_text(row_cells[0], 'Section A: Fault Reporting (Filled by Operator)', bold=True, font_size=11)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        # Row 1: Date and Time of Fault Reporting
        row = section_a_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], 'Date of Fault\nReporting\n(DD/MM/YYYY):', bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        self.format_cell_text(row_cells[1], data.get('fault_date', ''), font_size=10)
        self.set_cell_border(row_cells[1])
        
        self.format_cell_text(row_cells[2], 'Time of Fault\nReporting (HH:MM):', bold=True, font_size=9)
        self.set_cell_shading(row_cells[2], 'D9D9D9')
        self.set_cell_border(row_cells[2])
        
        self.format_cell_text(row_cells[3], data.get('fault_time', ''), font_size=10)
        self.set_cell_border(row_cells[3])
        
        # Row 2: Name and Verified By
        row = section_a_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], 'Name and Title of\nReporting Person:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        self.format_cell_text(row_cells[1], data.get('reporting_person', ''), font_size=10)
        self.set_cell_border(row_cells[1])
        
        self.format_cell_text(row_cells[2], 'Verified By:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[2], 'D9D9D9')
        self.set_cell_border(row_cells[2])
        
        self.format_cell_text(row_cells[3], data.get('verified_by', ''), font_size=10)
        self.set_cell_border(row_cells[3])
        
        # Row 3: Site ID and System
        row = section_a_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], 'Site ID:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        self.format_cell_text(row_cells[1], data.get('site_id', ''), font_size=10)
        self.set_cell_border(row_cells[1])
        
        self.format_cell_text(row_cells[2], 'System/ Subsystems:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[2], 'D9D9D9')
        self.set_cell_border(row_cells[2])
        
        self.format_cell_text(row_cells[3], data.get('system', ''), font_size=10)
        self.set_cell_border(row_cells[3])
        
        # Row 4: Location of Fault
        row = section_a_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], 'Location of Fault:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        row_cells[1].merge(row_cells[3])
        self.format_cell_text(row_cells[1], data.get('location', ''), font_size=10)
        self.set_cell_border(row_cells[1])
        
        # Row 5: Details of Fault Symptom
        row = section_a_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], 'Details of Fault\nSymptom:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        row_cells[1].merge(row_cells[3])
        details = data.get('fault_details', '')
        self.format_cell_text(row_cells[1], details, font_size=10)
        self.set_cell_border(row_cells[1])
        # Set row height for details
        row.height = Pt(60)
        
        self.doc.add_paragraph()  # Spacing
        
        # Section B: Fault Clearance
        section_b_table = self.doc.add_table(rows=1, cols=4)
        section_b_table.style = 'Table Grid'
        
        # Section B Header
        row = section_b_table.rows[0]
        row_cells = row.cells
        row_cells[0].merge(row_cells[3])
        self.format_cell_text(row_cells[0], 'Section B: Fault Clearance (Filled by Contractor)', bold=True, font_size=11)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        # Row 1: Date and Time
        row = section_b_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], 'Date and Time of\narrival:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        self.format_cell_text(row_cells[1], data.get('arrival_datetime', ''), font_size=10)
        self.set_cell_border(row_cells[1])
        
        self.format_cell_text(row_cells[2], 'Date & Time of fault\nclearance:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[2], 'D9D9D9')
        self.set_cell_border(row_cells[2])
        
        self.format_cell_text(row_cells[3], data.get('clearance_datetime', ''), font_size=10)
        self.set_cell_border(row_cells[3])
        
        # Row 2: Service Person and Attribution
        row = section_b_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], 'Name of Service\nPerson:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        self.format_cell_text(row_cells[1], data.get('service_person', ''), font_size=10)
        self.set_cell_border(row_cells[1])
        
        self.format_cell_text(row_cells[2], 'Attribution/ Cause of\nFault:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[2], 'D9D9D9')
        self.set_cell_border(row_cells[2])
        
        self.format_cell_text(row_cells[3], data.get('fault_cause', ''), font_size=10)
        self.set_cell_border(row_cells[3])
        
        # Row 3: Materials used
        row = section_b_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], 'Details of materials\nused and replaced and\nitems fitted (if any):', bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        row_cells[1].merge(row_cells[3])
        self.format_cell_text(row_cells[1], data.get('materials_used', 'Nil'), font_size=10)
        self.set_cell_border(row_cells[1])
        
        # Row 4: Repair details header
        row = section_b_table.add_row()
        row_cells = row.cells
        row_cells[0].merge(row_cells[3])
        self.format_cell_text(row_cells[0], 'Details of repair works, and verification carried out: (Please use separate sheet if not sufficient space)', 
                             bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        # Row 5: Repair details content
        row = section_b_table.add_row()
        row_cells = row.cells
        row_cells[0].merge(row_cells[3])
        repair_details = data.get('repair_details', '')
        self.format_cell_text(row_cells[0], repair_details, font_size=10)
        self.set_cell_border(row_cells[0])
        row.height = Pt(80)
        
        # Row 6: Contractor Staff
        row = section_b_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], "Name & Title of\nContractor's Staff:", bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        row_cells[1].merge(row_cells[3])
        self.format_cell_text(row_cells[1], data.get('contractor_staff', ''), font_size=10)
        self.set_cell_border(row_cells[1])
        
        # Row 7: Signature
        row = section_b_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], 'Signature:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        row_cells[1].merge(row_cells[3])
        self.format_cell_text(row_cells[1], '', font_size=10)
        self.set_cell_border(row_cells[1])
        
        # Row 8: Date
        row = section_b_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], 'Date:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        row_cells[1].merge(row_cells[3])
        self.format_cell_text(row_cells[1], data.get('contractor_date', ''), font_size=10)
        self.set_cell_border(row_cells[1])
        
        self.doc.add_paragraph()  # Spacing
        
        # Section C: Close out
        section_c_table = self.doc.add_table(rows=1, cols=4)
        section_c_table.style = 'Table Grid'
        
        # Section C Header
        row = section_c_table.rows[0]
        row_cells = row.cells
        row_cells[0].merge(row_cells[3])
        self.format_cell_text(row_cells[0], 'Section C: Close out of Fault Report (Filled by Representative of the Employer)', 
                             bold=True, font_size=11)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        # Row 1: Status
        row = section_c_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], 'Status:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        row_cells[1].merge(row_cells[3])
        status_text = data.get('status', 'Fault has been Cleared/ Temporarily fixed / Follow up action required (Ref No.')
        self.format_cell_text(row_cells[1], status_text, font_size=10)
        self.set_cell_border(row_cells[1])
        
        # Row 2: Severity Level
        row = section_c_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], 'Severity Level:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        severity = data.get('severity', 'Not Applicable')
        severity_text = f"[ ] Not Applicable    [ ] Minor    [X] {severity}" if severity not in ['Not Applicable', 'Minor', 'Major'] else f"[ ] Not Applicable    [ ] Minor    [ ] Major"
        self.format_cell_text(row_cells[1], severity_text, font_size=10)
        self.set_cell_border(row_cells[1])
        row_cells[2].merge(row_cells[3])
        self.set_cell_border(row_cells[2])
        
        # Row 3: Comments
        row = section_c_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], 'Comments:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        row_cells[1].merge(row_cells[3])
        self.format_cell_text(row_cells[1], data.get('comments', ''), font_size=10)
        self.set_cell_border(row_cells[1])
        row.height = Pt(40)
        
        # Row 4: Name & Title
        row = section_c_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], 'Name & Title:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        row_cells[1].merge(row_cells[3])
        self.format_cell_text(row_cells[1], data.get('employer_rep', ''), font_size=10)
        self.set_cell_border(row_cells[1])
        
        # Row 5: Signature
        row = section_c_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], 'Signature:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        row_cells[1].merge(row_cells[3])
        self.format_cell_text(row_cells[1], '', font_size=10)
        self.set_cell_border(row_cells[1])
        
        # Row 6: Date
        row = section_c_table.add_row()
        row_cells = row.cells
        
        self.format_cell_text(row_cells[0], 'Date:', bold=True, font_size=9)
        self.set_cell_shading(row_cells[0], 'D9D9D9')
        self.set_cell_border(row_cells[0])
        
        row_cells[1].merge(row_cells[3])
        self.format_cell_text(row_cells[1], data.get('closeout_date', ''), font_size=10)
        self.set_cell_border(row_cells[1])
        
        # Page 2: Detailed Incident Report (6 Required Sections)
        self.doc.add_page_break()
        self.add_detailed_report(data)
        
        # Save document
        if output_path:
            self.doc.save(output_path)
            print(f"[OK] Fault Log Form saved to: {output_path}")
        
        return self.doc
    
    def add_detailed_report(self, data):
        """Add detailed incident report with 6 required sections"""
        
        # Title
        title = self.doc.add_heading('INCIDENT REPORT', level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in title.runs:
            run.font.name = 'Arial'
            run.font.size = Pt(18)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0, 51, 102)
        
        # Reference link
        ref_para = self.doc.add_paragraph()
        ref_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = ref_para.add_run(f"Reference: {data.get('reference_no', 'N/A')}")
        run.font.name = 'Arial'
        run.font.size = Pt(11)
        run.italic = True
        
        self.doc.add_paragraph()  # Spacing
        
        # 1. Description of the Incident
        self.doc.add_heading('1. Description of the Incident', level=2)
        desc = data.get('detailed_description', data.get('fault_details', 'N/A'))
        self.add_content_paragraph(desc)
        
        # Key Facts
        self.add_sub_heading('Key Facts:')
        facts = data.get('key_facts', {})
        self.add_bullet(f"System/Service: {facts.get('system', data.get('system', 'N/A'))}")
        self.add_bullet(f"Detection Method: {facts.get('detection_method', 'Fault reported by operator')}")
        self.add_bullet(f"Symptoms: {facts.get('symptoms', data.get('fault_details', 'N/A'))}")
        
        self.doc.add_paragraph()  # Spacing
        
        # 2. Affected Date
        self.doc.add_heading('2. Affected Date', level=2)
        self.add_date_table(data)
        
        self.doc.add_paragraph()  # Spacing
        
        # 3. Event Sequence
        self.doc.add_heading('3. Event Sequence', level=2)
        self.add_event_sequence_table(data)
        
        self.doc.add_paragraph()  # Spacing
        
        # 4. Impact
        self.doc.add_heading('4. Impact', level=2)
        self.add_sub_heading('Scope:')
        impact = data.get('impact', {})
        self.add_bullet(f"Affected Systems: {impact.get('systems', data.get('system', 'N/A'))}")
        self.add_bullet(f"Affected Users: {impact.get('users', 'N/A')}")
        self.add_bullet(f"Geographic Region: {impact.get('region', data.get('site_id', 'N/A'))}")
        
        self.add_sub_heading(f"Severity: {impact.get('severity', data.get('severity', 'N/A'))}")
        
        self.add_sub_heading('Business Impact:')
        business_impact = impact.get('business_impact', [])
        if business_impact:
            for item in business_impact:
                self.add_bullet(item)
        else:
            self.add_bullet('Service disruption reported')
        
        self.doc.add_paragraph()  # Spacing
        
        # 5. Root Cause
        self.doc.add_heading('5. Root Cause', level=2)
        
        self.add_sub_heading('Trigger:')
        self.add_content_paragraph(data.get('trigger', data.get('fault_cause', 'N/A')))
        
        self.add_sub_heading('Root Cause:')
        root_cause = data.get('root_cause', data.get('fault_cause', 'N/A'))
        self.add_content_paragraph(root_cause)
        
        self.add_sub_heading('Evidence:')
        evidence = data.get('root_cause_evidence', 'See Fault Log Form Section B')
        self.add_content_paragraph(evidence)
        
        # 5 Whys
        if data.get('five_whys'):
            self.add_sub_heading('5-Whys Analysis:')
            for i, why in enumerate(data['five_whys'], 1):
                self.add_bullet(f"{i}. Why? → {why}")
        
        self.doc.add_paragraph()  # Spacing
        
        # 6. Follow-Up Actions
        self.doc.add_heading('6. Follow-Up Actions', level=2)
        
        # Immediate Actions
        self.add_sub_heading('Immediate Actions (Completed):')
        self.add_actions_table(data.get('immediate_actions', []), 'immediate')
        
        self.doc.add_paragraph()  # Spacing
        
        # Preventive Actions
        self.add_sub_heading('Preventive Actions (Planned):')
        self.add_actions_table(data.get('preventive_actions', []), 'preventive')
    
    def add_content_paragraph(self, text):
        """Add a content paragraph"""
        para = self.doc.add_paragraph()
        run = para.add_run(_to_text(text))
        run.font.name = 'Arial'
        run.font.size = Pt(11)
    
    def add_sub_heading(self, text):
        """Add a sub-heading"""
        para = self.doc.add_paragraph()
        run = para.add_run(text)
        run.font.name = 'Arial'
        run.font.size = Pt(11)
        run.bold = True
    
    def add_bullet(self, text):
        """Add a bullet point"""
        para = self.doc.add_paragraph(style='List Bullet')
        run = para.add_run(_to_text(text))
        run.font.name = 'Arial'
        run.font.size = Pt(11)
    
    def add_date_table(self, data):
        """Add date table"""
        table = self.doc.add_table(rows=4, cols=2)
        table.style = 'Table Grid'
        
        dates = [
            ('Incident Start Time', data.get('start_time', 'N/A')),
            ('Detection Time', data.get('detection_time', 'N/A')),
            ('Resolution Time', data.get('resolution_time', 'N/A')),
            ('Total Duration', data.get('total_duration', 'N/A'))
        ]
        
        for i, (label, value) in enumerate(dates):
            row = table.rows[i]
            row.cells[0].text = label
            row.cells[1].text = _to_text(value)
            
            # Format cells
            for paragraph in row.cells[0].paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True
                    run.font.name = 'Arial'
                    run.font.size = Pt(10)
            
            for paragraph in row.cells[1].paragraphs:
                for run in paragraph.runs:
                    run.font.name = 'Arial'
                    run.font.size = Pt(10)
    
    def add_event_sequence_table(self, data):
        """Add event sequence table"""
        events = data.get('event_sequence', [])
        
        if not events:
            self.add_content_paragraph('No events recorded.')
            return
        
        table = self.doc.add_table(rows=len(events) + 1, cols=3)
        table.style = 'Table Grid'
        
        # Header row
        header = table.rows[0]
        headers = ['Time', 'Event', 'Evidence']
        for i, h in enumerate(headers):
            header.cells[i].text = h
            for paragraph in header.cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True
                    run.font.name = 'Arial'
                    run.font.size = Pt(10)
        
        # Data rows
        for i, event in enumerate(events):
            row = table.rows[i + 1]
            row.cells[0].text = _to_text(event.get('time', 'N/A'))
            row.cells[1].text = _to_text(event.get('event', 'N/A'))
            row.cells[2].text = _to_text(event.get('evidence', 'N/A'))
            
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = 'Arial'
                        run.font.size = Pt(10)
    
    def add_actions_table(self, actions, action_type):
        """Add actions table"""
        if not actions:
            self.add_content_paragraph('No actions recorded.')
            return
        
        if action_type == 'immediate':
            headers = ['Action', 'Taken By', 'Time', 'Status']
        else:
            headers = ['Action', 'Owner', 'Due Date', 'Status']
        
        table = self.doc.add_table(rows=len(actions) + 1, cols=4)
        table.style = 'Table Grid'
        
        # Header row
        header = table.rows[0]
        for i, h in enumerate(headers):
            header.cells[i].text = h
            for paragraph in header.cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True
                    run.font.name = 'Arial'
                    run.font.size = Pt(10)
        
        # Data rows
        for i, action in enumerate(actions):
            row = table.rows[i + 1]
            row.cells[0].text = _to_text(action.get('action', 'N/A'))
            row.cells[1].text = _to_text(action.get('by', action.get('owner', 'N/A')))
            row.cells[2].text = _to_text(action.get('time', action.get('due_date', 'N/A')))
            row.cells[3].text = _to_text(action.get('status', 'N/A'))
            
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = 'Arial'
                        run.font.size = Pt(10)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate DAS Fault Log Form')
    parser.add_argument('--json', required=True, type=str, help='Load data from JSON file')
    parser.add_argument('--output', '-o', type=str, default='Fault_Log_Form.docx', help='Output file path')
    
    args = parser.parse_args()
    
    # 仅保留工具调用所需的生产链路：从 JSON 文件读取数据。
    print(f"Loading data from {args.json}...")
    with open(args.json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    data = normalize_incident_data(data)

    if not data.get('allow_incomplete'):
        missing_sections = validate_required_sections(data)
        if missing_sections:
            missing_text = '; '.join(missing_sections)
            raise SystemExit(
                f"报告信息不完整，缺少以下章节：{missing_text}。"
                "请先按 6 步补齐信息后再生成；如用户明确接受缺省项，可在 report_data 中设置 allow_incomplete=true。"
            )
    
    # Generate form
    generator = FaultLogFormGenerator()
    generator.generate_form(data, args.output)
    
    print(f"\n[OK] Fault Log Form generated: {args.output}")


if __name__ == '__main__':
    main()
