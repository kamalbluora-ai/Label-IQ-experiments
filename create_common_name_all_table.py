import sqlite3
import json
import requests
from openai import OpenAI
from datetime import datetime
from pathlib import Path
import time
import hashlib, config

def create_common_name_all_table():
    """Create and populate common_name_all table with processed common name compliance information"""
    
    # OpenAI Client - Replace with your API key
    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        print("Please set your OpenAI API key in the script or environment variable")
        return
    
    db_file = Path("ilt_requirements.db")
    
    # Connect to SQLite database
    if not db_file.exists():
        print(f"Error: Database {db_file} does not exist!")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    print(f"Creating common_name_all table in: {db_file}")
    
    # Drop and create common_name_all table with comprehensive structure
    cursor.execute("DROP TABLE IF EXISTS common_name_all")
    create_table_sql = """
    CREATE TABLE common_name_all (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_table TEXT NOT NULL,
        source_id INTEGER,
        content_type TEXT NOT NULL,  -- 'rule', 'content', 'internal_link', 'external_link'
        rule_number INTEGER,         -- For rules from common_name_rule_methods.py
        rule_id TEXT,               -- SHA1 rule identifier
        title TEXT NOT NULL,        -- Summary title/heading
        original_content TEXT,      -- Full original content/definition
        concise_summary TEXT,       -- GPT-processed concise version
        compliance_keywords TEXT,   -- Key compliance terms extracted
        regulatory_context TEXT,    -- Regulatory context (SFCR, FDR, etc.)
        section_reference TEXT,     -- Section/regulation reference
        related_urls TEXT,          -- Comma-separated URLs
        volume_category TEXT,       -- Volume/category if applicable
        applicability_scope TEXT,  -- When this applies (all foods, specific types, etc.)
        content_hash TEXT UNIQUE,   -- Hash to prevent duplicates
        created_date DATETIME NOT NULL
    )
    """
    
    cursor.execute(create_table_sql)
    print("Table 'common_name_all' created")
    
    # Clear sequence
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='common_name_all'")
    conn.commit()
    print("Sequence reset")
    
    total_records = 0
    created_date = datetime.utcnow()
    
    # Base insert SQL
    insert_sql = """
    INSERT OR IGNORE INTO common_name_all 
    (source_table, source_id, content_type, rule_number, rule_id, title, original_content, 
     concise_summary, compliance_keywords, regulatory_context, section_reference,
     related_urls, volume_category, applicability_scope, content_hash, created_date) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    # 1. Extract rules from common_name_rule_methods.py
    print("\n" + "="*60)
    print("STEP 1: PROCESSING COMMON NAME RULES")
    print("="*60)
    
    rules_data = extract_common_name_rules()
    for rule_data in rules_data:
        print(f"Processing Rule {rule_data['rule_number']}: {rule_data['title']}")
        processed = process_with_gpt(client, rule_data['content'], 'rule', rule_data.get('title', ''))
        if processed:
            content_hash = hashlib.md5(rule_data['content'].encode()).hexdigest()
            
            cursor.execute(insert_sql, (
                'common_name_rule_methods',
                rule_data.get('rule_number'),
                'rule',
                rule_data.get('rule_number'),
                rule_data.get('rule_id'),
                processed['title'],
                rule_data['content'],
                processed['concise_summary'],
                processed['compliance_keywords'],
                processed['regulatory_context'],
                processed['section_reference'],
                ', '.join(rule_data.get('content_links', [])),
                'General',
                processed['applicability_scope'],
                content_hash,
                created_date
            ))
            total_records += 1
    
    print(f"Processed {len(rules_data)} common name rules")
    
    # 2. Extract from core_labelling_requirements_content table
    print("\n" + "="*60)
    print("STEP 2: PROCESSING CORE LABELLING REQUIREMENTS CONTENT")
    print("="*60)
    
    # Check if table exists first
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='core_labelling_requirements_content'")
    if cursor.fetchone():
        cursor.execute("""
        SELECT id, requirement_name, section, content, internal_links, external_links, source_url
        FROM core_labelling_requirements_content 
        WHERE requirement_name LIKE '%common name%' OR requirement_name LIKE '%Common name%'
           OR section LIKE '%common name%' OR content LIKE '%common name%'
        """)
        
        core_records = cursor.fetchall()
        for record in core_records:
            record_id, req_name, section, content, internal_links, external_links, source_url = record
            
            if content and len(content.strip()) > 10:
                print(f"Processing core requirement: {req_name}")
                processed = process_with_gpt(client, content, 'content', f"{req_name} - {section}")
                if processed:
                    content_hash = hashlib.md5(content.encode()).hexdigest()
                    
                    urls = []
                    if source_url: urls.append(source_url)
                    if internal_links: urls.extend(internal_links.split(', '))
                    if external_links: urls.extend(external_links.split(', '))
                    
                    cursor.execute(insert_sql, (
                        'core_labelling_requirements_content',
                        record_id,
                        'content',
                        None,  # rule_number
                        None,  # rule_id
                        processed['title'],
                        content,
                        processed['concise_summary'],
                        processed['compliance_keywords'],
                        processed['regulatory_context'],
                        processed['section_reference'],
                        ', '.join(urls[:5]),  # Limit URLs
                        'Core Requirements',
                        processed['applicability_scope'],
                        content_hash,
                        created_date
                    ))
                    total_records += 1
        
        print(f"Processed {len(core_records)} core labelling content records")
    else:
        print("Table 'core_labelling_requirements_content' not found, skipping")
    
    # 3. Extract from food_specific_labelling_requirements_content table
    print("\n" + "="*60)
    print("STEP 3: PROCESSING FOOD-SPECIFIC CONTENT")
    print("="*60)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='food_specific_labelling_requirements_content'")
    if cursor.fetchone():
        cursor.execute("""
        SELECT id, requirement_name, section, content, internal_links, external_links, source_url
        FROM food_specific_labelling_requirements_content 
        WHERE section LIKE '%common name%' OR content LIKE '%common name%'
           OR requirement_name LIKE '%name%'
        """)
        
        food_specific_records = cursor.fetchall()
        for record in food_specific_records:
            record_id, req_name, section, content, internal_links, external_links, source_url = record
            
            if content and len(content.strip()) > 10:
                print(f"Processing food-specific requirement: {req_name}")
                processed = process_with_gpt(client, content, 'content', f"{req_name} - {section}")
                if processed:
                    content_hash = hashlib.md5(content.encode()).hexdigest()
                    
                    urls = []
                    if source_url: urls.append(source_url)
                    if internal_links: urls.extend(internal_links.split(', '))
                    if external_links: urls.extend(external_links.split(', '))
                    
                    cursor.execute(insert_sql, (
                        'food_specific_labelling_requirements_content',
                        record_id,
                        'content',
                        None, None,
                        processed['title'],
                        content,
                        processed['concise_summary'],
                        processed['compliance_keywords'],
                        processed['regulatory_context'],
                        processed['section_reference'],
                        ', '.join(urls[:5]),
                        'Food-Specific',
                        processed['applicability_scope'],
                        content_hash,
                        created_date
                    ))
                    total_records += 1
        
        print(f"Processed {len(food_specific_records)} food-specific content records")
    else:
        print("Table 'food_specific_labelling_requirements_content' not found, skipping")
    
    # 4. Extract from claims_and_statements_content table
    print("\n" + "="*60)
    print("STEP 4: PROCESSING CLAIMS AND STATEMENTS CONTENT")
    print("="*60)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='claims_and_statements_content'")
    if cursor.fetchone():
        cursor.execute("""
        SELECT id, requirement_name, section, content, internal_links, external_links, source_url
        FROM claims_and_statements_content 
        WHERE section LIKE '%name%' OR content LIKE '%common name%'
           OR content LIKE '%name%' OR requirement_name LIKE '%name%'
        """)
        
        claims_records = cursor.fetchall()
        for record in claims_records:
            record_id, req_name, section, content, internal_links, external_links, source_url = record
            
            if content and len(content.strip()) > 10:
                print(f"Processing claims/statements: {req_name}")
                processed = process_with_gpt(client, content, 'content', f"{req_name} - {section}")
                if processed:
                    content_hash = hashlib.md5(content.encode()).hexdigest()
                    
                    urls = []
                    if source_url: urls.append(source_url)
                    if internal_links: urls.extend(internal_links.split(', '))
                    if external_links: urls.extend(external_links.split(', '))
                    
                    cursor.execute(insert_sql, (
                        'claims_and_statements_content',
                        record_id,
                        'content',
                        None, None,
                        processed['title'],
                        content,
                        processed['concise_summary'],
                        processed['compliance_keywords'],
                        processed['regulatory_context'],
                        processed['section_reference'],
                        ', '.join(urls[:5]),
                        'Claims & Statements',
                        processed['applicability_scope'],
                        content_hash,
                        created_date
                    ))
                    total_records += 1
        
        print(f"Processed {len(claims_records)} claims and statements records")
    else:
        print("Table 'claims_and_statements_content' not found, skipping")
    
    # 5. Extract from internal_links and external_links tables
    print("\n" + "="*60)
    print("STEP 5: PROCESSING RELEVANT LINKS")
    print("="*60)
    
    # Internal links related to common name
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='internal_links'")
    if cursor.fetchone():
        cursor.execute("""
        SELECT id, link, link_text, context_text, section, tag
        FROM internal_links 
        WHERE link_text LIKE '%common name%' OR context_text LIKE '%common name%'
           OR section LIKE '%common name%'
        """)
        
        internal_links_records = cursor.fetchall()
        for record in internal_links_records:
            record_id, link, link_text, context_text, section, tag = record
            
            content_text = f"Link: {link}\nText: {link_text}\nContext: {context_text}\nSection: {section}"
            if content_text and len(content_text.strip()) > 10:
                print(f"Processing internal link: {link_text}")
                processed = process_with_gpt(client, content_text, 'internal_link', link_text or section)
                if processed:
                    content_hash = hashlib.md5(content_text.encode()).hexdigest()
                    
                    cursor.execute(insert_sql, (
                        'internal_links',
                        record_id,
                        'internal_link',
                        None, None,
                        processed['title'],
                        content_text,
                        processed['concise_summary'],
                        processed['compliance_keywords'],
                        processed['regulatory_context'],
                        processed['section_reference'],
                        link,
                        'Internal Links',
                        processed['applicability_scope'],
                        content_hash,
                        created_date
                    ))
                    total_records += 1
        
        print(f"Processed {len(internal_links_records)} internal link records")
    else:
        print("Table 'internal_links' not found, skipping")
    
    # External links related to common name
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='external_links'")
    if cursor.fetchone():
        cursor.execute("""
        SELECT id, link, link_text, context_text, section, tag
        FROM external_links 
        WHERE link_text LIKE '%common name%' OR context_text LIKE '%common name%'
           OR section LIKE '%common name%'
        """)
        
        external_links_records = cursor.fetchall()
        for record in external_links_records:
            record_id, link, link_text, context_text, section, tag = record
            
            content_text = f"Link: {link}\nText: {link_text}\nContext: {context_text}\nSection: {section}"
            if content_text and len(content_text.strip()) > 10:
                print(f"Processing external link: {link_text}")
                processed = process_with_gpt(client, content_text, 'external_link', link_text or section)
                if processed:
                    content_hash = hashlib.md5(content_text.encode()).hexdigest()
                    
                    cursor.execute(insert_sql, (
                        'external_links',
                        record_id,
                        'external_link',
                        None, None,
                        processed['title'],
                        content_text,
                        processed['concise_summary'],
                        processed['compliance_keywords'],
                        processed['regulatory_context'],
                        processed['section_reference'],
                        link,
                        'External Links',
                        processed['applicability_scope'],
                        content_hash,
                        created_date
                    ))
                    total_records += 1
        
        print(f"Processed {len(external_links_records)} external link records")
    else:
        print("Table 'external_links' not found, skipping")
    
    # Commit all changes
    conn.commit()
    
    print(f"\nTotal records inserted: {total_records}")
    
    # Display summary
    print(f"\n{'='*60}")
    print("COMMON NAME ALL TABLE SUMMARY")
    print(f"{'='*60}")
    
    cursor.execute("SELECT COUNT(*) FROM common_name_all")
    total_final = cursor.fetchone()[0]
    print(f"Total records in common_name_all: {total_final}")
    
    # Summary by content type
    cursor.execute("""
    SELECT content_type, COUNT(*) as count
    FROM common_name_all 
    GROUP BY content_type 
    ORDER BY count DESC
    """)
    
    print(f"\nRECORDS BY CONTENT TYPE:")
    for content_type, count in cursor.fetchall():
        print(f"  {content_type}: {count} records")
    
    # Summary by source table
    cursor.execute("""
    SELECT source_table, COUNT(*) as count
    FROM common_name_all 
    GROUP BY source_table 
    ORDER BY count DESC
    """)
    
    print(f"\nRECORDS BY SOURCE TABLE:")
    for source_table, count in cursor.fetchall():
        print(f"  {source_table}: {count} records")
    
    # Summary by volume category
    cursor.execute("""
    SELECT volume_category, COUNT(*) as count
    FROM common_name_all 
    GROUP BY volume_category 
    ORDER BY count DESC
    """)
    
    print(f"\nRECORDS BY CATEGORY:")
    for volume_category, count in cursor.fetchall():
        print(f"  {volume_category}: {count} records")
    
    # Show sample processed records
    print(f"\n{'='*60}")
    print("SAMPLE PROCESSED RECORDS")
    print(f"{'='*60}")
    
    cursor.execute("""
    SELECT content_type, title, 
           SUBSTR(concise_summary, 1, 100) as summary_preview,
           SUBSTR(compliance_keywords, 1, 50) as keywords_preview
    FROM common_name_all 
    ORDER BY id
    LIMIT 10
    """)
    
    sample_records = cursor.fetchall()
    for record in sample_records:
        print(f"Type: {record[0]}")
        print(f"Title: {record[1]}")
        print(f"Summary: {record[2]}...")
        print(f"Keywords: {record[3]}...")
        print("-" * 40)
    
    conn.close()
    print(f"\nCommon name all table created successfully!")

def extract_common_name_rules():
    """Extract rules from common_name_rule_methods.py"""
    rules_data = []
    
    # Define the rules based on your actual rules
    rules = [
        {
            'rule_number': 1,
            'rule_id': 'sha1:4e1b93a10d39',
            'title': 'Common Name Presence Requirement',
            'content': 'is a common name present? A common name must be displayed on food labels as required by SFCR regulations.',
            'content_links': ['https://inspection.canada.ca/en/food-labels/labelling/industry/common-name']
        },
        {
            'rule_number': 2,
            'rule_id': 'sha1:c20cfb1e7fdf', 
            'title': 'Common Name Exemptions',
            'content': 'if not, is the product exempt from common name? Certain products may be exempt from common name requirements under specific conditions.',
            'content_links': ['https://inspection.canada.ca/en/food-labels/labelling/industry/common-name#a1_2']
        },
        {
            'rule_number': 3,
            'rule_id': 'sha1:83c8e4a7093c',
            'title': 'Principal Display Panel Requirement',
            'content': 'is the common name on the principal display panel (PDP)? The common name must be displayed on the principal display panel for visibility.',
            'content_links': ['https://inspection.canada.ca/en/food-labels/labelling/industry/legibility-and-location#s14c3']
        },
        {
            'rule_number': 4,
            'rule_id': 'sha1:858b303922e8',
            'title': 'Minimum Text Size Requirement',
            'content': 'is the common name in letters of 1.6 mm or greater? Common names must meet minimum text size requirements for legibility.',
            'content_links': ['https://inspection.canada.ca/en/food-labels/labelling/industry/legibility-and-location#s15c3']
        },
        {
            'rule_number': 5,
            'rule_id': 'sha1:f00c531f323c',
            'title': 'Small Package Text Size Exception',
            'content': 'or, if the area of the principal display surface (PDS) is 10 cm² (1.55 inches²) or less, is the common name shown in characters with a minimum type height of 0.8 mm (1/32 inch)? Small packages have reduced minimum text size requirements.',
            'content_links': ['https://inspection.canada.ca/en/food-labels/labelling/industry/legibility-and-location#s15c3']
        },
        {
            'rule_number': 6,
            'rule_id': 'sha1:c6287136bf6e',
            'title': 'Appropriate Common Name Requirement',
            'content': 'is it an appropriate common name? The common name must accurately represent the food product and comply with regulatory standards.',
            'content_links': [
                'https://inspection.canada.ca/en/about-cfia/acts-and-regulations/list-acts-and-regulations/documents-incorporated-reference',
                'https://inspection.canada.ca/en/food-labels/labelling/industry/true-nature'
            ]
        },
        {
            'rule_number': 7,
            'rule_id': 'sha1:066ba186767c',
            'title': 'Bold Face Type Requirement',
            'content': 'as printed in bold face type, but not in italics, in the FDR or in the Canadian Standards of Identity documents incorporated by reference (IbR) in the SFCR. Common names must follow specific formatting requirements.',
            'content_links': ['https://inspection.canada.ca/en/about-cfia/acts-and-regulations/list-acts-and-regulations/documents-incorporated-reference']
        },
        {
            'rule_number': 8,
            'rule_id': 'sha1:15e066fd11d3',
            'title': 'Other Regulation Prescription',
            'content': 'as prescribed by any other regulation. Some common names may be specifically prescribed by other applicable regulations.',
            'content_links': []
        },
        {
            'rule_number': 9,
            'rule_id': 'sha1:b7d3432f46d3',
            'title': 'Generally Known Name Alternative',
            'content': 'the name by which the food is generally known or a name that is not generic and that describes the food, if the name is not so printed or prescribed. Alternative naming when standard names are not available.',
            'content_links': []
        },
        {
            'rule_number': 10,
            'rule_id': 'sha1:5a34dc2408ac',
            'title': 'True Nature Description Requirement',
            'content': 'if the food is likely to be mistaken for another food, the common name must include words that describe the food\'s true nature with respect to its condition. Prevent consumer confusion through descriptive naming.',
            'content_links': ['https://inspection.canada.ca/en/food-labels/labelling/industry/true-nature']
        }
    ]
    
    return rules

def process_with_gpt(client, content, content_type, title=""):
    """Process content with GPT to create concise summaries and extract compliance information"""
    
    system_prompt = """You are an expert in Canadian food labelling regulations and CFIA compliance. 

Analyze the provided content and create a structured response with the following information:
1. A clear, concise summary (2-3 sentences maximum)
2. Key compliance keywords and terms
3. Regulatory context (which regulations apply - SFCR, FDR, etc.)
4. Section/regulation references if mentioned
5. Applicability scope (when this rule/guidance applies)

Focus on practical compliance guidance that food manufacturers need to know.

Respond ONLY with a JSON object in this format:
{
  "title": "Clear descriptive title",
  "concise_summary": "2-3 sentence summary of key compliance requirements",
  "compliance_keywords": "comma-separated key terms like: common name, PDP, SFCR, minimum size, bold text, etc.",
  "regulatory_context": "applicable regulations like SFCR, FDR, etc.",
  "section_reference": "specific section references if mentioned",
  "applicability_scope": "when this applies - all foods, specific food types, package sizes, etc."
}
"""

    user_prompt = f"""Analyze this {content_type} content for Canadian food labelling compliance:

Title: {title}
Content: {content}

Extract the key compliance information and create a concise summary."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
            max_tokens=1000
        )
        
        # Parse the JSON response
        content_text = response.choices[0].message.content.strip()
        
        # Clean up markdown formatting if present
        if content_text.startswith("```json"):
            content_text = content_text.replace("```json", "").replace("```", "").strip()
        elif content_text.startswith("```"):
            content_text = content_text.replace("```", "").strip()
        
        try:
            result = json.loads(content_text)
            
            # Validate required fields
            required_fields = ['title', 'concise_summary', 'compliance_keywords', 'regulatory_context', 'section_reference', 'applicability_scope']
            for field in required_fields:
                if field not in result:
                    result[field] = ""
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"  JSON parsing error: {e}")
            print(f"  Raw response: {content_text[:200]}...")
            return None
            
    except Exception as e:
        print(f"  Error processing with GPT: {e}")
        return None
    
    # Small delay to respect API rate limits
    time.sleep(0.1)

def create_common_name_query_helper():
    """Create helper functions to query the common_name_all table for compliance checking"""
    
    helper_code = '''import sqlite3
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
    db_file = Path("ilt_requirements.db")
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
    context_text = "COMPLIANCE KNOWLEDGE BASE:\\n\\n"
    
    context_text += "RULES:\\n"
    for i, rule in enumerate(compliance_context['rules'], 1):
        context_text += f"{i}. {rule['title']}: {rule['summary']}\\n"
        if rule['section_reference']:
            context_text += f"   Reference: {rule['section_reference']}\\n"
    
    context_text += "\\nCONTENT GUIDANCE:\\n"
    for guidance in compliance_context['content_guidance']:
        context_text += f"- {guidance['title']}: {guidance['summary']}\\n"
    
    context_text += f"\\nKEY COMPLIANCE KEYWORDS: {', '.join(compliance_context['keywords'])}\\n"
    
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
'''
    
    # Write helper functions to a separate file
    helper_file = Path("common_name_compliance_helpers.py")
    with open(helper_file, 'w') as f:
        f.write(helper_code)
    
    print(f"Created helper functions in: {helper_file}")

if __name__ == "__main__":
    print("CFIA Common Name Compliance Knowledge Base Generator")
    print("="*60)
    
    # Create the comprehensive common name table
    create_common_name_all_table()
    
    # Create helper functions for querying and compliance checking
    create_common_name_query_helper()
    
    print("\n" + "="*60)
    print("KNOWLEDGE BASE CREATION COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Use common_name_all table for compliance queries")
    print("2. Import common_name_compliance_helpers.py for evaluation functions")
    print("3. Call evaluate_label_common_name_compliance(label_data, gpt_client) to check labels")
    print("\nExample usage:")
    print("""
from common_name_compliance_helpers import evaluate_label_common_name_compliance
from openai import OpenAI

client = OpenAI(api_key="your-key")
label_data = {
    'common_name': 'Skim Milk',
    'food_type': 'dairy',
    'package_size_cm2': 150,
    'text_size_mm': 2.0,
    'on_pdp': True
}

result = evaluate_label_common_name_compliance(label_data, client)
print(result['overall_compliance'])
""")