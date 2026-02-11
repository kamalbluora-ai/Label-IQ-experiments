#!/usr/bin/env python3
"""
Canadian Standards of Identity (CSI) Extraction Orchestrator

This script orchestrates the complete extraction process for Canadian Standards of Identity
common names from all 8 volumes.

Usage:
    python csi_orchestrator.py [options]

Options:
    --volumes 1,3,5          Extract only specific volumes (comma-separated)
    --skip-validation        Skip the final validation step
    --verbose                Enable verbose output
    --help                   Show this help message

The orchestrator processes:
- Volume 1: https://inspection.canada.ca/.../canadian-standards-identity-volume-1
- Volume 2: https://inspection.canada.ca/.../canadian-standards-identity-volume-2
- ...
- Volume 8: https://inspection.canada.ca/.../canadian-standards-identity-volume-8
"""

import sys, config
import argparse
import sqlite3
import requests
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from bs4 import BeautifulSoup
import re


class CSIOrchestrator:
    """Orchestrates the Canadian Standards of Identity extraction process"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.base_url = "https://inspection.canada.ca/en/about-cfia/acts-and-regulations/list-acts-and-regulations/documents-incorporated-reference/canadian-standards-identity-volume-{}"
        self.db_file = Path("ilt_requirements.db")
        self.client = None
        self.setup_openai()
        
        # Volume information
        self.volumes_info = {
            1: {"title": "General Standards", "expected_sections": ["1.1", "1.2", "1.3"]},
            2: {"title": "Dairy Products", "expected_sections": ["2.1", "2.2", "2.3"]},
            3: {"title": "Fats and Oils", "expected_sections": ["3.1", "3.2"]},
            4: {"title": "Fruit and Vegetable Products", "expected_sections": ["4.1", "4.2"]},
            5: {"title": "Sugars and Honey", "expected_sections": ["5.1", "5.2"]},
            6: {"title": "Cereal Products", "expected_sections": ["6.1", "6.2"]},
            7: {"title": "Meat and Poultry Products", "expected_sections": ["7.1", "7.2"]},
            8: {"title": "Fish and Marine Products", "expected_sections": ["8.1", "8.2"]}
        }
        
    def log(self, message, level="INFO"):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def setup_openai(self):
        """Initialize OpenAI client"""
        try:
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.log("OpenAI client initialized successfully")
        except Exception as e:
            self.log(f"Error initializing OpenAI client: {e}", "ERROR")
            raise
    
    def check_database_exists(self):
        """Check if the database exists"""
        if not self.db_file.exists():
            self.log(f"Database {self.db_file} does not exist!", "ERROR")
            self.log("Please run create_ilt_database.py first.", "ERROR")
            return False
        return True
    
    def setup_csiv_table(self):
        """Setup the csiv_cname table"""
        self.log("Setting up csiv_cname table...")
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Drop existing table
            cursor.execute("DROP TABLE IF EXISTS csiv_cname")
            self.log("Dropped existing csiv_cname table (if existed)")
            
            # Create table
            create_table_sql = """
            CREATE TABLE csiv_cname (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                common_name TEXT NOT NULL,
                definition TEXT,
                volume_number INTEGER,
                volume_title TEXT,
                section TEXT,
                tag TEXT,
                source_url TEXT,
                created_date DATETIME NOT NULL
            )
            """
            
            cursor.execute(create_table_sql)
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='csiv_cname'")
            conn.commit()
            conn.close()
            
            self.log("csiv_cname table created successfully")
            return True
            
        except Exception as e:
            self.log(f"Error setting up table: {e}", "ERROR")
            return False
    
    def process_volume(self, volume_number):
        """Process a single CSI volume"""
        vol_info = self.volumes_info.get(volume_number, {"title": "Unknown"})
        vol_url = self.base_url.format(volume_number)
        
        self.log(f"Processing Volume {volume_number}: {vol_info['title']}")
        self.log(f"URL: {vol_url}")
        
        try:
            # Fetch webpage
            self.log(f"Fetching Volume {volume_number} content...")
            response = requests.get(vol_url, timeout=30)
            response.raise_for_status()
            html_content = response.text
            self.log(f"Successfully fetched Volume {volume_number} ({len(html_content)} chars)")
            
            # Extract content
            extracted_data = self.extract_volume_content(html_content, volume_number, vol_url)
            
            if extracted_data:
                self.log(f"Extracted {len(extracted_data)} items from Volume {volume_number}")
                return extracted_data
            else:
                self.log(f"No data extracted from Volume {volume_number}", "WARNING")
                return []
                
        except requests.RequestException as e:
            self.log(f"Error fetching Volume {volume_number}: {e}", "ERROR")
            return []
        except Exception as e:
            self.log(f"Error processing Volume {volume_number}: {e}", "ERROR")
            return []
    
    def extract_volume_content(self, html_content, volume_number, source_url):
        """Extract common names from a volume's HTML content"""
        
        # Clean HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        main_content = soup.find('main') or soup.find('div', class_='container') or soup
        clean_text = main_content.get_text(separator='\n', strip=True)
        
        if self.verbose:
            self.log(f"  Volume {volume_number} content length: {len(clean_text)} characters")
        
        # Chunking strategy
        max_chunk_size = 15000
        overlap_size = 3000
        chunks = []
        
        start = 0
        while start < len(clean_text):
            end = start + max_chunk_size
            
            if end < len(clean_text):
                search_start = max(start + max_chunk_size - overlap_size, start)
                
                # Look for good break points
                break_patterns = [
                    r'\n\d+\.\d+\.\d+',
                    r'\n\d+\.\d+', 
                    r'\n[A-Z][a-z]+ [A-Z]',
                    r'\n\s*\n'
                ]
                
                best_break = end
                for pattern in break_patterns:
                    matches = list(re.finditer(pattern, clean_text[search_start:end + overlap_size]))
                    if matches:
                        last_match = matches[-1]
                        potential_break = search_start + last_match.start()
                        if potential_break > start + max_chunk_size // 2:
                            best_break = potential_break
                            break
                
                end = min(best_break, len(clean_text))
            
            chunk = clean_text[start:end].strip()
            if chunk and len(chunk) > 100:
                chunks.append(chunk)
            
            start = end
            if start >= len(clean_text):
                break
        
        if self.verbose:
            self.log(f"  Split Volume {volume_number} into {len(chunks)} chunks")
        
        # Process chunks with GPT
        all_extracted_data = []
        
        for i, chunk in enumerate(chunks):
            if self.verbose:
                self.log(f"  Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
            
            try:
                chunk_data = self.extract_chunk_with_gpt(chunk, volume_number, source_url)
                all_extracted_data.extend(chunk_data)
                
                if self.verbose and chunk_data:
                    self.log(f"    Extracted {len(chunk_data)} items from chunk {i+1}")
                    
            except Exception as e:
                self.log(f"    Error processing chunk {i+1}: {e}", "WARNING")
                continue
        
        # Remove duplicates
        seen_names = set()
        unique_data = []
        
        for item in all_extracted_data:
            name_lower = item["common_name"].lower()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                unique_data.append(item)
        
        if len(all_extracted_data) > len(unique_data):
            self.log(f"  Removed {len(all_extracted_data) - len(unique_data)} duplicates")
        
        return unique_data
    
    def extract_chunk_with_gpt(self, chunk, volume_number, source_url):
        """Extract data from a text chunk using GPT"""
        
        vol_info = self.volumes_info.get(volume_number, {"title": "Unknown"})
        
        system_prompt = f"""You are an expert parser for Canadian Standards of Identity Volume {volume_number} ({vol_info['title']}).

Extract common names from the text. Focus on food/product names that have identity standards.

For each product name found, extract:
- common_name: the actual product name (no section numbers)
- definition: the standard definition (first sentence is enough) 
- volume_number: {volume_number}
- volume_title: Volume {volume_number} - {vol_info['title']}
- section: the section number (e.g. "1.2")
- tag: the section heading if available

Return ONLY pipe-delimited format:
common_name|definition|volume_number|volume_title|section|tag

Example:
Butter|is the food derived exclusively from milk fat|{volume_number}|Volume {volume_number} - {vol_info['title']}|2.1|2.1 Butter Standards

Only extract actual product names with standards. No headers, no extra text."""

        user_prompt = f"""Extract product common names from this Canadian Standards of Identity Volume {volume_number} text.

{chunk}

Return ONLY pipe-delimited data:
common_name|definition|volume_number|volume_title|section|tag"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=16000
            )

            content = response.choices[0].message.content.strip()
            
            # Parse response
            parsed_data = []
            lines = content.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line or '|' not in line:
                    continue
                
                parts = line.split('|')
                if len(parts) >= 6:
                    parsed_data.append({
                        "common_name": parts[0].strip(),
                        "definition": parts[1].strip(),
                        "volume_number": volume_number,
                        "volume_title": parts[3].strip(),
                        "section": parts[4].strip(),
                        "tag": parts[5].strip(),
                        "source_url": source_url
                    })
            
            return parsed_data
            
        except Exception as e:
            if self.verbose:
                self.log(f"      GPT extraction error: {e}", "WARNING")
            return []
    
    def save_extracted_data(self, all_data):
        """Save extracted data to database"""
        if not all_data:
            self.log("No data to save", "WARNING")
            return 0
        
        self.log(f"Saving {len(all_data)} records to database...")
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            records_inserted = 0
            created_date = datetime.now()
            
            for item in all_data:
                try:
                    cursor.execute("""
                        INSERT INTO csiv_cname (common_name, definition, volume_number, volume_title, section, tag, source_url, created_date) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item.get("common_name", ""),
                        item.get("definition", ""),
                        item.get("volume_number", 0),
                        item.get("volume_title", ""),
                        item.get("section", ""),
                        item.get("tag", ""),
                        item.get("source_url", ""),
                        created_date
                    ))
                    records_inserted += 1
                    
                    if records_inserted % 50 == 0:
                        self.log(f"  Inserted {records_inserted} records...")
                        
                except Exception as e:
                    self.log(f"  Error inserting record: {e}", "WARNING")
                    continue
            
            conn.commit()
            conn.close()
            
            self.log(f"Successfully saved {records_inserted} records")
            return records_inserted
            
        except Exception as e:
            self.log(f"Error saving data: {e}", "ERROR")
            return 0
    
    def validate_extraction(self):
        """Validate the extraction results"""
        self.log("="*60)
        self.log("VALIDATION RESULTS")
        self.log("="*60)
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Total count
            cursor.execute("SELECT COUNT(*) FROM csiv_cname")
            total_records = cursor.fetchone()[0]
            self.log(f"Total records: {total_records}")
            
            # Volume coverage
            cursor.execute("""
                SELECT volume_number, volume_title, COUNT(*) as count 
                FROM csiv_cname 
                GROUP BY volume_number 
                ORDER BY volume_number
            """)
            volume_results = cursor.fetchall()
            
            self.log("Volume coverage:")
            expected_volumes = set(range(1, 9))
            covered_volumes = set()
            
            for vol_num, vol_title, count in volume_results:
                status = "✅" if count > 0 else "❌"
                self.log(f"  {status} Volume {vol_num} ({vol_title}): {count} names")
                if count > 0:
                    covered_volumes.add(vol_num)
            
            missing_volumes = expected_volumes - covered_volumes
            if missing_volumes:
                self.log(f"❌ Missing volumes: {sorted(missing_volumes)}", "WARNING")
            else:
                self.log("✅ All 8 volumes covered successfully!")
            
            # Top sections
            cursor.execute("""
                SELECT section, COUNT(*) as count 
                FROM csiv_cname 
                WHERE section IS NOT NULL AND section != ''
                GROUP BY section 
                ORDER BY count DESC 
                LIMIT 5
            """)
            top_sections = cursor.fetchall()
            
            if top_sections:
                self.log("Top sections:")
                for section, count in top_sections:
                    self.log(f"  {section}: {count} names")
            
            conn.close()
            return len(missing_volumes) == 0
            
        except Exception as e:
            self.log(f"Error in validation: {e}", "ERROR")
            return False
    
    def run_extraction(self, volumes_to_process=None):
        """Run the complete CSI extraction process"""
        self.log("CANADIAN STANDARDS OF IDENTITY EXTRACTION STARTED")
        
        if not self.check_database_exists():
            return False
        
        if not self.setup_csiv_table():
            return False
        
        # Determine volumes to process
        if volumes_to_process is None:
            volumes_to_process = list(range(1, 9))  # All volumes 1-8
        
        self.log(f"Processing volumes: {volumes_to_process}")
        
        # Process each volume
        all_extracted_data = []
        successful_volumes = 0
        
        for volume_num in volumes_to_process:
            if volume_num not in self.volumes_info:
                self.log(f"Invalid volume number: {volume_num}", "WARNING")
                continue
            
            self.log(f"\n{'='*40}")
            self.log(f"PROCESSING VOLUME {volume_num}")
            self.log(f"{'='*40}")
            
            volume_data = self.process_volume(volume_num)
            if volume_data:
                all_extracted_data.extend(volume_data)
                successful_volumes += 1
                self.log(f"✅ Volume {volume_num} completed: {len(volume_data)} items")
            else:
                self.log(f"❌ Volume {volume_num} failed", "WARNING")
        
        # Save all data
        if all_extracted_data:
            records_saved = self.save_extracted_data(all_extracted_data)
            self.log(f"\n✅ Extraction completed: {records_saved} total records from {successful_volumes}/{len(volumes_to_process)} volumes")
            return True
        else:
            self.log("❌ No data extracted from any volume", "ERROR")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Canadian Standards of Identity Extraction Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--volumes', type=str,
                       help='Comma-separated list of volumes to process (e.g., "1,3,5")')
    parser.add_argument('--skip-validation', action='store_true',
                       help='Skip the final validation step')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Parse volumes
    volumes_to_process = None
    if args.volumes:
        try:
            volumes_to_process = [int(x.strip()) for x in args.volumes.split(',')]
            volumes_to_process = [v for v in volumes_to_process if 1 <= v <= 8]
        except ValueError:
            print("Error: Invalid volumes format. Use comma-separated numbers (e.g., '1,3,5')")
            sys.exit(1)
    
    try:
        orchestrator = CSIOrchestrator(verbose=args.verbose)
        
        # Run extraction
        success = orchestrator.run_extraction(volumes_to_process)
        
        # Run validation unless skipped
        if success and not args.skip_validation:
            validation_success = orchestrator.validate_extraction()
            success = success and validation_success
        
        if success:
            orchestrator.log("🎉 CSI EXTRACTION COMPLETED SUCCESSFULLY!", "SUCCESS")
        else:
            orchestrator.log("⚠️ CSI EXTRACTION COMPLETED WITH ISSUES", "WARNING")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Extraction cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"[FATAL] Extraction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()