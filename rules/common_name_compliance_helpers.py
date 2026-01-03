import sqlite3
import json
from pathlib import Path

def get_common_name_compliance_context(label_data=None, food_type=None, package_size=None):
    """
    Get relevant common name compliance information for a specific label/food type
    
    Args:
        label_data: Dictionary containing label information
        food_type: Type of food (e.g., 'dairy', 'meat', 'beverage') 
        package_size: Package size in cm² for text size requirements
    
    Returns:
        Dictionary with relevant compliance information
    """
    db_file = Path(__file__).parent.parent.parent / "data" / "ilt_requirements.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Base query to get all common name related info
    base_query = """
    SELECT title, concise_summary, compliance_keywords, regulatory_context, 
           section_reference, applicability_scope, related_urls, content_type,
           rule_number, original_content
    FROM common_name_all 
    WHERE 1=1
    """
    
    conditions = []
    params = []
    
    # Filter by food type if provided
    if food_type:
        conditions.append("(applicability_scope LIKE ? OR compliance_keywords LIKE ?)")
        params.extend([f"%{food_type}%", f"%{food_type}%"])
    
    # Include package size specific rules if provided
    if package_size:
        if package_size <= 10:  # Small package rules
            conditions.append("(compliance_keywords LIKE ? OR title LIKE ?)")
            params.extend(["%small%", "%small package%"])
    
    # Add conditions to query
    if conditions:
        base_query += " AND (" + " OR ".join(conditions) + ")"
    
    base_query += " ORDER BY rule_number, content_type"
    
    cursor.execute(base_query, params)
    results = cursor.fetchall()
    
    compliance_info = {
        'rules': [],
        'content_guidance': [],
        'regulatory_links': [],
        'keywords': set()
    }
    
    for result in results:
        title, summary, keywords, reg_context, section_ref, scope, urls, content_type, rule_num, original = result
        
        info = {
            'title': title,
            'summary': summary,
            'regulatory_context': reg_context,
            'section_reference': section_ref,
            'applicability_scope': scope,
            'urls': urls.split(', ') if urls else [],
            'rule_number': rule_num,
            'original_content': original
        }
        
        if content_type == 'rule':
            compliance_info['rules'].append(info)
        else:
            compliance_info['content_guidance'].append(info)
        
        if urls:
            compliance_info['regulatory_links'].extend(urls.split(', '))
        
        if keywords:
            compliance_info['keywords'].update(keywords.split(', '))
    
    compliance_info['keywords'] = list(compliance_info['keywords'])
    compliance_info['regulatory_links'] = list(set(compliance_info['regulatory_links']))
    
    conn.close()
    return compliance_info

def evaluate_label_common_name_compliance(label_data, gpt_client):
    """
    Evaluate a food label for common name compliance using the processed knowledge base
    
    Args:
        label_data: Dictionary containing label information including common_name, package_info, etc.
        gpt_client: OpenAI client instance
    
    Returns:
        Dictionary with compliance evaluation results
    """
    
    # Get relevant compliance context
    food_type = label_data.get('food_type')
    package_size = label_data.get('package_size_cm2')
    
    compliance_context = get_common_name_compliance_context(label_data, food_type, package_size)
    
    # Create evaluation prompt with context
    system_prompt = """You are an expert CFIA food labelling compliance auditor.
    
Use the provided compliance knowledge base to evaluate the food label for common name compliance.
Check each relevant rule and provide specific compliance findings.

Respond with a JSON object:
{
  "overall_compliance": "COMPLIANT" | "NON_COMPLIANT" | "NEEDS_REVIEW",
  "rule_evaluations": [
    {
      "rule_number": 1,
      "rule_title": "...",
      "status": "PASS" | "FAIL" | "N/A",
      "finding": "specific finding text",
      "recommendation": "action needed if any"
    }
  ],
  "critical_issues": ["list of critical compliance issues"],
  "recommendations": ["list of recommendations for improvement"],
  "confidence_score": 0.95
}
"""

    # Build context for GPT
    context_text = "COMPLIANCE KNOWLEDGE BASE:\n\n"
    
    context_text += "RULES:\n"
    for i, rule in enumerate(compliance_context['rules'], 1):
        context_text += f"{i}. {rule['title']}: {rule['summary']}\n"
        if rule['section_reference']:
            context_text += f"   Reference: {rule['section_reference']}\n"
    
    context_text += "\nCONTENT GUIDANCE:\n"
    for guidance in compliance_context['content_guidance']:
        context_text += f"- {guidance['title']}: {guidance['summary']}\n"
    
    context_text += f"\nKEY COMPLIANCE KEYWORDS: {', '.join(compliance_context['keywords'])}\n"
    
    user_prompt = f"""Evaluate this food label for common name compliance:

LABEL DATA:
{json.dumps(label_data, indent=2)}

{context_text}

Provide detailed compliance evaluation."""

    try:
        response = gpt_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
            max_tokens=2000
        )
        
        result_content = response.choices[0].message.content.strip()
        
        # Clean and parse JSON response
        if result_content.startswith("```json"):
            result_content = result_content.replace("```json", "").replace("```", "").strip()
        
        evaluation_result = json.loads(result_content)
        return evaluation_result
        
    except Exception as e:
        return {
            "overall_compliance": "ERROR",
            "error": str(e),
            "rule_evaluations": [],
            "critical_issues": [f"Evaluation failed: {str(e)}"],
            "recommendations": ["Manual review required due to system error"],
            "confidence_score": 0.0
        }
