"""
Report API Router - Generate PDF compliance reports
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage import storage
from pdf_service import generate_compliance_report

router = APIRouter(tags=["reports"])


@router.get("/api/analyses/{analysis_id}/report")
async def download_report(analysis_id: str):
    """Generate and download a PDF compliance report for an analysis."""
    
    # Find the analysis
    analysis = storage.analyses.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis.status != "completed":
        raise HTTPException(status_code=400, detail="Analysis is not completed yet")
    
    # Get project info
    project = storage.projects.get(analysis.projectId)
    project_name = project.name if project else "Unknown Project"
    
    # Get full evaluation data from details
    details = analysis.details or {}
    full_data = details.get('_fullEvaluationData', {})
    
    rule_evaluations = full_data.get('rule_evaluations', {})
    overall_compliance = full_data.get('overall_compliance', {
        'status': 'Unknown',
        'compliance_rate': 0,
        'compliant_rules': 0,
        'total_rules': 11,
        'summary': analysis.resultSummary or 'Analysis completed.'
    })
    critical_issues = full_data.get('critical_issues', [])
    extracted_label_data = full_data.get('extracted_label_data', None)
    
    # If no full data, create basic rule evaluations from simplified details
    if not rule_evaluations:
        rule_names = {
            'common_name_present': 1,
            'common_name_exempt': 2,
            'common_name_on_pdp': 3,
            'common_name_text_size': 4,
            'small_package_text_size': 5,
            'appropriate_common_name': 6,
            'standards_compliance': 7,
            'regulation_compliance': 8,
            'descriptive_name': 9,
            'true_nature_description': 10,
            'bilingual_requirements': 11
        }
        
        for key, value in details.items():
            if key.startswith('_'):
                continue
            rule_num = rule_names.get(key)
            if rule_num:
                rule_evaluations[f'rule_{rule_num}'] = {
                    'compliant': value == 'Pass',
                    'confidence': 0.8 if value != 'Unknown' else 0.0,
                    'finding': f"Rule evaluation: {value}"
                }
    
    # Generate PDF
    pdf_buffer = generate_compliance_report(
        project_name=project_name,
        analysis_name=analysis.name,
        analysis_date=analysis.createdAt,
        overall_compliance=overall_compliance,
        rule_evaluations=rule_evaluations,
        critical_issues=critical_issues,
        extracted_label_data=extracted_label_data
    )
    
    # Return as downloadable file
    filename = f"CFIA_Report_{project_name.replace(' ', '_')}_{analysis.name.replace(' ', '_')}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
