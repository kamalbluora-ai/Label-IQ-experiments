import sqlite3, config
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# OpenAI Client - Replace with your API key
client = OpenAI(api_key=config.OPENAI_API_KEY)

def process_related_urls():
    """Process related URLs from common_name_all table and create concise summaries"""
    
    db_file = Path("ilt_requirements.db")
    
    # Connect to SQLite database
    if not db_file.exists():
        print(f"Error: Database {db_file} does not exist!")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    print(f"Processing related URLs from common_name_all table")
    
    # Add the new column if it doesn't exist
    cursor.execute("PRAGMA table_info(common_name_all)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'related_urls_concise_summary' not in columns:
        print("Adding related_urls_concise_summary column...")
        cursor.execute("ALTER TABLE common_name_all ADD COLUMN related_urls_concise_summary TEXT")
        conn.commit()
        print("✓ Column added successfully")
    else:
        print("✓ Column already exists")
    
    # Get records with URLs that need processing (including truncated ones)
    cursor.execute("""
    SELECT id, related_urls, title, rule_number
    FROM common_name_all 
    WHERE related_urls IS NOT NULL 
    AND related_urls != ''
    AND (related_urls_concise_summary IS NULL 
         OR related_urls_concise_summary = ''
         OR related_urls_concise_summary LIKE '%...')
    ORDER BY id
    """)
    
    records = cursor.fetchall()
    print(f"Found {len(records)} records with URLs to process")
    
    if not records:
        print("No records to process")
        conn.close()
        return
    
    processed_count = 0
    error_count = 0
    
    for record_id, related_urls, title, rule_number in records:
        print(f"\nProcessing record {record_id}: {title} (Rule {rule_number})")
        
        # Split URLs by comma and clean them
        urls = [url.strip() for url in related_urls.split(',') if url.strip()]
        print(f"  Found {len(urls)} URLs to process")
        
        # Get summary for each URL
        url_summaries = []
        
        for i, url in enumerate(urls, 1):
            print(f"    Processing URL {i}/{len(urls)}: {url}")
            
            try:
                # Get webpage content first
                content = fetch_webpage_content(url)
                
                if content:
                    # Send content to GPT for summarization
                    summary = summarize_content_with_gpt(url, content, title, rule_number)
                    
                    if summary:
                        url_summaries.append({
                            'url': url,
                            'summary': summary
                        })
                        print(f"      ✓ Summary created ({len(summary)} chars)")
                    else:
                        print(f"      ✗ Failed to create summary")
                        error_count += 1
                else:
                    print(f"      ✗ Failed to fetch content")
                    error_count += 1
                
                # Rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"      ✗ Error: {str(e)}")
                error_count += 1
                continue
        
        # Concatenate summaries for multiple URLs
        if url_summaries:
            concatenated_summary = create_concatenated_summary(url_summaries)
            
            # Update database
            cursor.execute("""
            UPDATE common_name_all 
            SET related_urls_concise_summary = ?
            WHERE id = ?
            """, (concatenated_summary, record_id))
            
            processed_count += 1
            print(f"  ✓ Updated record {record_id} with {len(url_summaries)} URL summaries")
            print(f"      Final summary length: {len(concatenated_summary)} chars")
            
            # Commit after each update
            conn.commit()
        else:
            print(f"  ✗ No summaries created for record {record_id}")
    
    print(f"\n{'='*60}")
    print("PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"Successfully processed: {processed_count}")
    print(f"Errors encountered: {error_count}")
    
    # Show sample results
    cursor.execute("""
    SELECT id, title, rule_number,
           SUBSTR(related_urls_concise_summary, 1, 300) as preview,
           LENGTH(related_urls_concise_summary) as full_length
    FROM common_name_all 
    WHERE related_urls_concise_summary IS NOT NULL 
    AND related_urls_concise_summary != ''
    ORDER BY rule_number, id
    LIMIT 5
    """)
    
    samples = cursor.fetchall()
    if samples:
        print(f"\nSAMPLE RESULTS:")
        for record_id, title, rule_num, preview, full_length in samples:
            print(f"Rule {rule_num} - ID {record_id}: {title}")
            print(f"  Full length: {full_length} chars")
            print(f"  Preview: {preview}...")
            print("-" * 50)
    
    conn.close()
    print("Processing completed!")

def fetch_webpage_content(url):
    """Fetch and clean webpage content"""
    
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return None
        
        # Set headers to mimic browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        print(f"        Fetching: {url}")
        
        # Fetch webpage with timeout and error handling
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"        Status: {response.status_code}")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
        
        # Find main content
        main_content = (
            soup.find('main') or 
            soup.find('article') or 
            soup.find('div', class_='wb-cont') or  # Canada.ca specific
            soup.find('div', class_='content') or
            soup.find('body')
        )
        
        if not main_content:
            main_content = soup
        
        # Extract clean text
        text = main_content.get_text(separator='\n', strip=True)
        
        # Clean up text
        import re
        text = re.sub(r'\n\s*\n', '\n', text)  # Remove extra newlines
        text = re.sub(r'[ \t]+', ' ', text)     # Normalize spaces
        
        # Increased limit size for GPT to get more comprehensive content
        max_length = 50000  # Increased from 12000 to capture full webpage content
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        print(f"        Content length: {len(text)} chars")
        return text
        
    except requests.exceptions.Timeout:
        print(f"        Timeout error for {url}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"        Connection error for {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"        Request error: {str(e)}")
        return None
    except Exception as e:
        print(f"        Fetch error: {str(e)}")
        return None

def summarize_content_with_gpt(url, content, context_title="", rule_number=None):
    """Send content to GPT for concise summarization"""
    
    system_prompt = """You are an expert in Canadian food labelling regulations and CFIA compliance.

Create a comprehensive yet concise summary of the provided webpage content that focuses on food labelling compliance requirements.

The summary should:
- Be 3-6 sentences (comprehensive but concise)
- Focus on specific compliance requirements
- Include regulatory references (SFCR sections, FDR sections, etc.)
- Mention specific measurements, exemptions, or conditions
- Include key definitions or terminology
- Be actionable for food manufacturers
- Cover all important compliance points mentioned

Respond with only the summary text, no additional formatting."""

    context_info = []
    if rule_number:
        context_info.append(f"This is for Common Name Rule #{rule_number}")
    if context_title:
        context_info.append(f"Context: {context_title}")
    
    context_string = " | ".join(context_info) if context_info else ""

    user_prompt = f"""Summarize this CFIA webpage content for food labelling compliance:

{context_string}
URL: {url}

Content:
{content}

Provide a comprehensive summary covering all important compliance requirements and actionable guidance. Include specific measurements, section references, and key definitions."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
            max_tokens=16384  # Maximum supported by gpt-4o-mini
        )
        
        summary = response.choices[0].message.content.strip()
        
        # Clean up formatting
        import re
        summary = re.sub(r'\n+', ' ', summary)
        summary = re.sub(r'\s+', ' ', summary)
        
        return summary
        
    except Exception as e:
        print(f"        GPT error: {str(e)}")
        return None

def create_concatenated_summary(url_summaries):
    """Concatenate summaries from multiple URLs"""
    
    if not url_summaries:
        return ""
    
    if len(url_summaries) == 1:
        return url_summaries[0]['summary']
    
    # Create concatenated summary for multiple URLs
    parts = []
    
    for i, url_data in enumerate(url_summaries, 1):
        url = url_data['url']
        summary = url_data['summary']
        
        # Extract domain for readability
        try:
            domain = urlparse(url).netloc.replace('www.', '')
            if 'inspection.canada.ca' in domain:
                domain = 'CFIA'
            elif 'canada.ca' in domain:
                domain = 'Gov.CA'
        except:
            domain = 'Unknown'
        
        # Format: [1] CFIA: summary text
        part = f"[{i}] {domain}: {summary}"
        parts.append(part)
    
    concatenated = " | ".join(parts)
    
    # Dynamic length limit based on number of URLs (16k chars per URL)
    max_length = 16000 * len(url_summaries)
    if len(concatenated) > max_length:
        # Instead of truncating arbitrarily, try to truncate at sentence boundaries
        truncated = concatenated[:max_length]
        last_period = truncated.rfind('.')
        if last_period > max_length - 1000:  # If there's a period near the end
            concatenated = truncated[:last_period + 1] + "..."
        else:
            concatenated = truncated + "..."
    
    return concatenated

def view_processing_results():
    """View detailed processing results"""
    
    db_file = Path("ilt_requirements.db")
    
    if not db_file.exists():
        print("Database not found.")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(common_name_all)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'related_urls_concise_summary' not in columns:
        print("Column 'related_urls_concise_summary' does not exist yet.")
        conn.close()
        return
    
    print(f"\n{'='*60}")
    print("URL PROCESSING RESULTS")
    print(f"{'='*60}")
    
    # Overall statistics
    cursor.execute("""
    SELECT 
        COUNT(*) as total_records,
        COUNT(CASE WHEN related_urls IS NOT NULL AND related_urls != '' THEN 1 END) as with_urls,
        COUNT(CASE WHEN related_urls_concise_summary IS NOT NULL AND related_urls_concise_summary != '' THEN 1 END) as processed
    FROM common_name_all
    """)
    
    total, with_urls, processed = cursor.fetchone()
    
    print(f"Total records: {total}")
    print(f"Records with URLs: {with_urls}")
    print(f"Records processed: {processed}")
    if with_urls > 0:
        print(f"Completion rate: {processed/with_urls*100:.1f}%")
    
    # Check summary lengths
    cursor.execute("""
    SELECT 
        AVG(LENGTH(related_urls_concise_summary)) as avg_length,
        MAX(LENGTH(related_urls_concise_summary)) as max_length,
        MIN(LENGTH(related_urls_concise_summary)) as min_length
    FROM common_name_all 
    WHERE related_urls_concise_summary IS NOT NULL 
    AND related_urls_concise_summary != ''
    """)
    
    avg_len, max_len, min_len = cursor.fetchone()
    if avg_len:
        print(f"\nSUMMARY LENGTHS:")
        print(f"  Average: {avg_len:.0f} chars")
        print(f"  Maximum: {max_len} chars")
        print(f"  Minimum: {min_len} chars")
    
    # Rules with multiple URLs
    cursor.execute("""
    SELECT rule_number, title, related_urls,
           CASE WHEN related_urls LIKE '%,%' THEN 'Multiple URLs' ELSE 'Single URL' END as url_count,
           LENGTH(related_urls_concise_summary) as summary_length
    FROM common_name_all 
    WHERE related_urls IS NOT NULL AND related_urls != ''
    AND rule_number IS NOT NULL
    ORDER BY rule_number
    """)
    
    rules_data = cursor.fetchall()
    if rules_data:
        print(f"\nRULES WITH URLS:")
        for rule_num, title, urls, url_count, summary_len in rules_data:
            url_list = [url.strip() for url in urls.split(',')]
            print(f"  Rule {rule_num}: {len(url_list)} URLs ({url_count}) - Summary: {summary_len or 0} chars")
    
    # Sample processed results with full summaries
    cursor.execute("""
    SELECT rule_number, title, related_urls_concise_summary
    FROM common_name_all 
    WHERE related_urls_concise_summary IS NOT NULL 
    AND related_urls_concise_summary != ''
    AND rule_number IS NOT NULL
    ORDER BY rule_number
    LIMIT 3
    """)
    
    samples = cursor.fetchall()
    if samples:
        print(f"\nSAMPLE PROCESSED RESULTS (FULL SUMMARIES):")
        for rule_num, title, summary in samples:
            print(f"\nRule {rule_num}: {title}")
            print(f"Summary ({len(summary)} chars): {summary}")
            print("-" * 80)
    
    conn.close()

if __name__ == "__main__":
    print("Related URLs Summary Processor")
    print("=" * 60)
    
    # Process all related URLs
    process_related_urls()
    
    # Show detailed results
    view_processing_results()
