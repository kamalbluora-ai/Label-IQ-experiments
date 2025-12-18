"""
PDF Report Generation Service for Label-IQ
Generates professional CFIA compliance reports with rule evaluations
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime
from typing import Dict, Any, Optional


def generate_compliance_report(
    project_name: str,
    analysis_name: str,
    analysis_date: str,
    overall_compliance: Dict[str, Any],
    rule_evaluations: Dict[str, Any],
    critical_issues: list,
    extracted_label_data: Optional[Dict[str, Any]] = None
) -> BytesIO:
    """
    Generate a PDF compliance report.
    
    Returns a BytesIO buffer containing the PDF.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=20,
        textColor=colors.HexColor('#1a1a2e'),
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#16213e')
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubheading',
        parent=styles['Heading3'],
        fontSize=12,
        spaceBefore=15,
        spaceAfter=8,
        textColor=colors.HexColor('#0f3460')
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        leading=14
    )
    
    small_style = ParagraphStyle(
        'CustomSmall',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.gray,
        alignment=TA_CENTER
    )
    
    # Build document content
    story = []
    
    # Title
    story.append(Paragraph("CFIA Food Labelling Compliance Report", title_style))
    story.append(Spacer(1, 10))
    
    # Header info table
    header_data = [
        ["Project:", project_name, "Analysis:", analysis_name],
        ["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M"), "Analysis Date:", analysis_date[:10] if analysis_date else "N/A"]
    ]
    header_table = Table(header_data, colWidths=[1*inch, 2.5*inch, 1*inch, 2.5*inch])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.gray),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 20))
    
    # Overall Compliance Status
    story.append(Paragraph("Executive Summary", heading_style))
    
    status = overall_compliance.get('status', 'Unknown')
    compliance_rate = overall_compliance.get('compliance_rate', 0)
    compliant_rules = overall_compliance.get('compliant_rules', 0)
    total_rules = overall_compliance.get('total_rules', 11)
    
    # Status color
    if compliance_rate >= 0.9:
        status_color = colors.HexColor('#10b981')  # Green
        status_text = "COMPLIANT"
    elif compliance_rate >= 0.7:
        status_color = colors.HexColor('#f59e0b')  # Amber
        status_text = "MOSTLY COMPLIANT"
    else:
        status_color = colors.HexColor('#ef4444')  # Red
        status_text = "NON-COMPLIANT"
    
    summary_data = [
        ["Overall Status", status_text],
        ["Compliance Rate", f"{compliance_rate*100:.1f}%"],
        ["Rules Passed", f"{compliant_rules} / {total_rules}"]
    ]
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (1, 0), (1, 0), status_color),
        ('TEXTCOLOR', (1, 0), (1, 0), colors.white),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 5))
    
    # Summary text
    summary_text = overall_compliance.get('summary', 'Analysis completed.')
    story.append(Paragraph(summary_text, body_style))
    
    # Critical Issues
    if critical_issues:
        story.append(Spacer(1, 10))
        story.append(Paragraph("⚠️ Critical Issues", subheading_style))
        for issue in critical_issues[:5]:
            # Clean up the issue text
            issue_text = str(issue).replace("CRITICAL: ", "• ")
            story.append(Paragraph(issue_text, body_style))
    
    # Extracted Label Data (if available)
    if extracted_label_data:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Extracted Label Information", heading_style))
        
        label_items = [
            ("Common Name", extracted_label_data.get('common_name', 'N/A')),
            ("Product Type", extracted_label_data.get('product_type', 'N/A')),
            ("Brand", extracted_label_data.get('brand_name', 'N/A')),
            ("Net Quantity", extracted_label_data.get('net_quantity', 'N/A')),
            ("Bilingual", "Yes" if extracted_label_data.get('bilingual_compliance') else "No"),
        ]
        
        for label, value in label_items:
            story.append(Paragraph(f"<b>{label}:</b> {value}", body_style))
    
    # Rule Evaluations
    story.append(Spacer(1, 15))
    story.append(Paragraph("Detailed Rule Evaluations", heading_style))
    
    # Rule names mapping - Common Name Rules
    rule_names = {
        1: "Common Name Present",
        2: "Common Name Exemption",
        3: "Common Name on PDP",
        4: "Common Name Text Size",
        5: "Small Package Text Size",
        6: "Appropriate Common Name",
        7: "Standards Compliance",
        8: "Regulation Compliance",
        9: "Descriptive Name",
        10: "True Nature Description",
        11: "Bilingual (Common Name)"
    }
    
    # Bilingual Rules mapping
    bilingual_rule_names = {
        1: "All Mandatory Info Bilingual",
        2: "Bilingual Exemption Check"
    }
    
    # Net Quantity Rules mapping
    net_qty_rule_names = {
        1: "Net Qty Present",
        2: "Net Qty Exemption",
        3: "Net Qty on PDP",
        4: "Metric Units",
        5: "Retail Bulk Units",
        6: "Measurement Manner",
        7: "Rounding (3 figures)",
        8: "Bilingual Symbols",
        9: "Written Units Bilingual",
        10: "Type Height/Bold",
        11: "Canadian Units",
        12: "US Units"
    }
    
    # Create table header
    table_data = [["Rule", "Status", "Confidence", "Finding"]]
    
    # Sort keys: common name (0), bilingual (1), net qty (2), ingredients (3), nutrition (4), date (5), origin (6), dealer (7), fop (8)
    def sort_key(x):
        if x.startswith('sweet_rule_'):
            return (10, int(x.replace('sweet_rule_', '')))
        elif x.startswith('irrad_rule_'):
            return (9, int(x.replace('irrad_rule_', '')))
        elif x.startswith('fop_rule_'):
            return (8, int(x.replace('fop_rule_', '')))
        elif x.startswith('dealer_rule_'):
            return (7, int(x.replace('dealer_rule_', '')))
        elif x.startswith('origin_rule_'):
            return (6, int(x.replace('origin_rule_', '')))
        elif x.startswith('date_rule_'):
            return (5, int(x.replace('date_rule_', '')))
        elif x.startswith('nutrition_rule_'):
            return (4, int(x.replace('nutrition_rule_', '')))
        elif x.startswith('ingredients_rule_'):
            return (3, int(x.replace('ingredients_rule_', '')))
        elif x.startswith('net_qty_rule_'):
            return (2, int(x.replace('net_qty_rule_', '')))
        elif x.startswith('bilingual_rule_'):
            return (1, int(x.replace('bilingual_rule_', '')))
        else:
            return (0, int(x.replace('rule_', '')))
    
    # Ingredients Rules mapping
    ingredients_rule_names = {
        1: "Ingredients Present",
        2: "Ingredients Exemption",
        3: "Descending Order",
        4: "Common Names Used",
        5: "Components Declared",
        6: "Sugars Grouped",
        7: "Allergens Declared",
        8: "Contains Statement",
        9: "Cross-Contamination",
        10: "Statements Position",
        11: "Phenylalanine (Aspartame)",
        12: "Statements Order",
        13: "Bilingual Match",
        14: "Formatting/Legibility",
        15: "Location Requirements"
    }
    
    # Nutrition Rules mapping
    nutrition_rule_names = {
        1: "NFt Present",
        2: "NFt Exempt/Prohibited",
        3: "NFt Location",
        4: "Serving Size",
        5: "Core Nutrients",
        6: "Units & %DV",
        7: "%DV Statement",
        8: "Format Appropriate",
        9: "Format Version/Size",
        10: "Colours/Contrast",
        11: "Font Requirements",
        12: "FOP Symbol Present",
        13: "FOP Thresholds",
        14: "FOP Specifications",
        15: "FOP Location"
    }
    
    for rule_key in sorted(rule_evaluations.keys(), key=sort_key):
        eval_data = rule_evaluations[rule_key]
        
        # Date marking rules mapping
        date_rule_names = {
            1: "Best Before Present",
            2: "Best Before Wording",
            3: "Date Format",
            4: "Date Location",
            5: "Packaged On Present",
            6: "Packaged On Wording",
            7: "Expiration Date",
            8: "Storage Instructions",
            9: "Date Grouped",
            10: "Date Legibility"
        }
        
        # Determine rule name based on type
        # Origin rules mapping
        origin_rule_names = {
            1: "Origin Required",
            2: "Origin Present",
            3: "Origin Format",
            4: "Origin Bilingual",
            5: "Origin Legibility"
        }
        
        # Dealer rules mapping
        dealer_rule_names = {
            1: "Dealer Present",
            2: "Dealer Address",
            3: "Imported Declaration",
            4: "Type Height",
            5: "Dealer Location",
            6: "Dealer Legibility"
        }
        
        if rule_key.startswith('origin_rule_'):
            rule_num = int(rule_key.replace('origin_rule_', ''))
            rule_name = origin_rule_names.get(rule_num, f"Origin Rule {rule_num}")
            display_num = f"O{rule_num}"
        elif rule_key.startswith('dealer_rule_'):
            rule_num = int(rule_key.replace('dealer_rule_', ''))
            rule_name = dealer_rule_names.get(rule_num, f"Dealer Rule {rule_num}")
            display_num = f"DL{rule_num}"
        elif rule_key.startswith('date_rule_'):
            rule_num = int(rule_key.replace('date_rule_', ''))
            rule_name = date_rule_names.get(rule_num, f"Date Rule {rule_num}")
            display_num = f"D{rule_num}"
        elif rule_key.startswith('nutrition_rule_'):
            rule_num = int(rule_key.replace('nutrition_rule_', ''))
            rule_name = nutrition_rule_names.get(rule_num, f"Nutrition Rule {rule_num}")
            display_num = f"NL{rule_num}"
        elif rule_key.startswith('ingredients_rule_'):
            rule_num = int(rule_key.replace('ingredients_rule_', ''))
            rule_name = ingredients_rule_names.get(rule_num, f"Ingredients Rule {rule_num}")
            display_num = f"I{rule_num}"
        # FOP rules mapping
        elif rule_key.startswith('fop_rule_'):
            fop_rule_names = {
                1: "FOP Present", 2: "FOP Exempt", 3: "FOP Thresholds",
                4: "FOP Legibility", 5: "FOP Specifications", 6: "FOP Proportional",
                7: "FOP Location", 8: "FOP Multi-pack"
            }
            rule_num = int(rule_key.replace('fop_rule_', ''))
            rule_name = fop_rule_names.get(rule_num, f"FOP Rule {rule_num}")
            display_num = f"F{rule_num}"
        # Irradiation rules mapping
        elif rule_key.startswith('irrad_rule_'):
            irrad_rule_names = {
                1: "Irrad Permitted", 2: "Irrad Statement", 3: "Irrad Discernible",
                4: "Irrad Symbol PDP", 5: "Irrad Symbol Size", 6: "Irrad Ingredients"
            }
            rule_num = int(rule_key.replace('irrad_rule_', ''))
            rule_name = irrad_rule_names.get(rule_num, f"Irrad Rule {rule_num}")
            display_num = f"IR{rule_num}"
        # Sweeteners rules mapping
        elif rule_key.startswith('sweet_rule_'):
            sweet_rule_names = {
                1: "Aspartame Present", 2: "Phenylalanine Statement", 3: "Statement Location",
                4: "Statement Bold", 5: "Table-top Sweetener", 6: "Sweetness Equivalence"
            }
            rule_num = int(rule_key.replace('sweet_rule_', ''))
            rule_name = sweet_rule_names.get(rule_num, f"Sweet Rule {rule_num}")
            display_num = f"SW{rule_num}"
        elif rule_key.startswith('net_qty_rule_'):
            rule_num = int(rule_key.replace('net_qty_rule_', ''))
            rule_name = net_qty_rule_names.get(rule_num, f"Net Qty Rule {rule_num}")
            display_num = f"N{rule_num}"
        elif rule_key.startswith('bilingual_rule_'):
            rule_num = int(rule_key.replace('bilingual_rule_', ''))
            rule_name = bilingual_rule_names.get(rule_num, f"Bilingual Rule {rule_num}")
            display_num = f"B{rule_num}"
        else:
            rule_num = int(rule_key.replace('rule_', ''))
            rule_name = rule_names.get(rule_num, f"Rule {rule_num}")
            display_num = str(rule_num)
        
        compliant = eval_data.get('compliant')
        if compliant is True:
            status = "✓ Pass"
        elif compliant is False:
            status = "✗ Fail"
        else:
            status = "? Unknown"
        
        confidence = eval_data.get('confidence', 0)
        confidence_str = f"{confidence*100:.0f}%"
        
        finding = eval_data.get('finding', 'No finding available')
        # Truncate long findings for table
        if len(finding) > 80:
            finding = finding[:77] + "..."
        
        table_data.append([
            f"{display_num}. {rule_name}",
            status,
            confidence_str,
            finding
        ])
    
    # Create table
    rule_table = Table(table_data, colWidths=[1.8*inch, 0.7*inch, 0.8*inch, 3.7*inch])
    
    # Table styling
    table_style = [
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        
        # Body
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (1, 1), (2, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        
        # Borders
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]
    
    # Color code rows based on status
    for i, row in enumerate(table_data[1:], start=1):
        if "✓" in row[1]:
            table_style.append(('BACKGROUND', (1, i), (1, i), colors.HexColor('#d1fae5')))
            table_style.append(('TEXTCOLOR', (1, i), (1, i), colors.HexColor('#065f46')))
        elif "✗" in row[1]:
            table_style.append(('BACKGROUND', (1, i), (1, i), colors.HexColor('#fee2e2')))
            table_style.append(('TEXTCOLOR', (1, i), (1, i), colors.HexColor('#991b1b')))
        # Alternate row colors
        if i % 2 == 0:
            table_style.append(('BACKGROUND', (0, i), (0, i), colors.HexColor('#f9fafb')))
            table_style.append(('BACKGROUND', (2, i), (-1, i), colors.HexColor('#f9fafb')))
    
    rule_table.setStyle(TableStyle(table_style))
    story.append(rule_table)
    
    # Detailed findings for failed rules
    failed_rules = [(k, v) for k, v in rule_evaluations.items() if v.get('compliant') is False]
    if failed_rules:
        story.append(Spacer(1, 20))
        story.append(Paragraph("Recommendations for Non-Compliant Rules", heading_style))
        
        for rule_key, eval_data in failed_rules:
            # Determine rule name based on type
            if rule_key.startswith('date_rule_'):
                rule_num = int(rule_key.replace('date_rule_', ''))
                rule_name = date_rule_names.get(rule_num, f"Date Rule {rule_num}")
                display = f"Date Rule {rule_num}: {rule_name}"
            elif rule_key.startswith('nutrition_rule_'):
                rule_num = int(rule_key.replace('nutrition_rule_', ''))
                rule_name = nutrition_rule_names.get(rule_num, f"Nutrition Rule {rule_num}")
                display = f"Nutrition Rule {rule_num}: {rule_name}"
            elif rule_key.startswith('ingredients_rule_'):
                rule_num = int(rule_key.replace('ingredients_rule_', ''))
                rule_name = ingredients_rule_names.get(rule_num, f"Ingredients Rule {rule_num}")
                display = f"Ingredients Rule {rule_num}: {rule_name}"
            elif rule_key.startswith('net_qty_rule_'):
                rule_num = int(rule_key.replace('net_qty_rule_', ''))
                rule_name = net_qty_rule_names.get(rule_num, f"Net Qty Rule {rule_num}")
                display = f"Net Qty Rule {rule_num}: {rule_name}"
            elif rule_key.startswith('origin_rule_'):
                rule_num = int(rule_key.replace('origin_rule_', ''))
                rule_name = origin_rule_names.get(rule_num, f"Origin Rule {rule_num}")
                display = f"Origin Rule {rule_num}: {rule_name}"
            elif rule_key.startswith('dealer_rule_'):
                rule_num = int(rule_key.replace('dealer_rule_', ''))
                rule_name = dealer_rule_names.get(rule_num, f"Dealer Rule {rule_num}")
                display = f"Dealer Rule {rule_num}: {rule_name}"
            elif rule_key.startswith('fop_rule_'):
                rule_num = int(rule_key.replace('fop_rule_', ''))
                rule_name = fop_rule_names.get(rule_num, f"FOP Rule {rule_num}")
                display = f"FOP Rule {rule_num}: {rule_name}"
            elif rule_key.startswith('irrad_rule_'):
                rule_num = int(rule_key.replace('irrad_rule_', ''))
                rule_name = irrad_rule_names.get(rule_num, f"Irrad Rule {rule_num}")
                display = f"Irrad Rule {rule_num}: {rule_name}"
            elif rule_key.startswith('sweet_rule_'):
                rule_num = int(rule_key.replace('sweet_rule_', ''))
                rule_name = sweet_rule_names.get(rule_num, f"Sweet Rule {rule_num}")
                display = f"Sweet Rule {rule_num}: {rule_name}"
            elif rule_key.startswith('bilingual_rule_'):
                rule_num = int(rule_key.replace('bilingual_rule_', ''))
                rule_name = bilingual_rule_names.get(rule_num, f"Bilingual Rule {rule_num}")
                display = f"Bilingual Rule {rule_num}: {rule_name}"
            else:
                rule_num = int(rule_key.replace('rule_', ''))
                rule_name = rule_names.get(rule_num, f"Rule {rule_num}")
                display = f"Rule {rule_num}: {rule_name}"
            
            story.append(Paragraph(f"<b>{display}</b>", subheading_style))
            
            # Full finding
            finding = eval_data.get('finding', 'No finding available')
            story.append(Paragraph(f"<b>Finding:</b> {finding}", body_style))
            
            # Reasoning
            reasoning = eval_data.get('reasoning', '')
            if reasoning:
                story.append(Paragraph(f"<b>Reasoning:</b> {reasoning}", body_style))
            
            # Recommendations
            recommendations = eval_data.get('recommendations', [])
            if recommendations:
                story.append(Paragraph("<b>Recommendations:</b>", body_style))
                for rec in recommendations:
                    story.append(Paragraph(f"  • {rec}", body_style))
            
            story.append(Spacer(1, 10))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("─" * 80, small_style))
    story.append(Paragraph(
        f"Generated by Bluora CFIA.AI Platform • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • Confidential",
        small_style
    ))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
