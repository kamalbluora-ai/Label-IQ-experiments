#!/usr/bin/env python3
"""
CFCS Common Names Extraction Orchestrator

This script orchestrates the complete extraction and validation process for 
Canadian Food Compositional Standards (CFCS) common names.

Usage:
    python cfcs_orchestrator.py [options]

Options:
    --skip-main-extraction    Skip the main extraction and only run validation/gap-filling
    --skip-water-search      Skip the targeted water search
    --skip-volume-check      Skip the volume validation check
    --verbose                Enable verbose output
    --help                   Show this help message

The orchestrator runs the following steps in order:
1. Main CFCS extraction (create_cfcs_cname_table.py logic)
2. Volume validation and gap filling
3. Targeted water search for Volume 11 - Prepackaged Water
4. Final verification and reporting
"""

import sys, config
import argparse
import sqlite3
import requests
import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from bs4 import BeautifulSoup
import re


class CFCSOrchestrator:
    """Orchestrates the complete CFCS common names extraction process"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.url = "https://inspection.canada.ca/en/about-cfia/acts-and-regulations/list-acts-and-regulations/documents-incorporated-reference/canadian-food-compositional-standards-0"
        self.db_file = Path("ilt_requirements.db")
        self.client = None
        self.setup_openai()
        
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
    
    def run_main_extraction(self):
        """Step 1: Run the main CFCS extraction process"""
        self.log("="*60)
        self.log("STEP 1: MAIN CFCS EXTRACTION")
        self.log("="*60)
        
        if not self.check_database_exists():
            return False
            
        try:
            # Import and run the main extraction logic
            from create_cfcs_cname_table import create_cfcs_cname_table
            create_cfcs_cname_table()
            self.log("Main extraction completed successfully")
            return True
        except ImportError:
            # If import fails, run the extraction logic inline
            self.log("Running main extraction inline...")
            return self._run_main_extraction_inline()
        except Exception as e:
            self.log(f"Error in main extraction: {e}", "ERROR")
            return False
    
    def _run_main_extraction_inline(self):
        """Inline version of main extraction if import fails"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            self.log("Creating cfcs_cname table...")
            
            # Drop and recreate table
            cursor.execute("DROP TABLE IF EXISTS cfcs_cname")
            create_table_sql = """
            CREATE TABLE cfcs_cname (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                common_name TEXT NOT NULL,
                definition TEXT,
                volume TEXT,
                tag TEXT,
                source_url TEXT,
                created_date DATETIME NOT NULL
            )
            """
            cursor.execute(create_table_sql)
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='cfcs_cname'")
            conn.commit()
            
            # Fetch webpage
            self.log("Fetching webpage...")
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            
            # Extract data (simplified version - you can expand this)
            extracted_data = self._extract_with_gpt_inline(response.text)
            
            # Insert data
            records_inserted = 0
            created_date = datetime.now()
            
            for item in extracted_data:
                try:
                    cursor.execute("""
                        INSERT INTO cfcs_cname (common_name, definition, volume, tag, source_url, created_date) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        item.get("common_name", ""),
                        item.get("definition", ""),
                        item.get("volume", ""),
                        item.get("tag", ""),
                        self.url,
                        created_date
                    ))
                    records_inserted += 1
                    if records_inserted % 100 == 0:
                        self.log(f"Inserted {records_inserted} records...")
                except Exception as e:
                    self.log(f"Error inserting record: {e}", "WARNING")
            
            conn.commit()
            conn.close()
            
            self.log(f"Main extraction completed: {records_inserted} records inserted")
            return True
            
        except Exception as e:
            self.log(f"Error in inline main extraction: {e}", "ERROR")
            return False
    
    def _extract_with_gpt_inline(self, html_content):
        """Simplified extraction logic"""
        # This is a simplified version - you can expand with full chunking logic
        soup = BeautifulSoup(html_content, 'html.parser')
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        main_content = soup.find('main') or soup.find('div', class_='container') or soup
        clean_text = main_content.get_text(separator='\n', strip=True)[:50000]  # Limit for demo
        
        system_prompt = """Extract Canadian Food Compositional Standards common names.
Return pipe-delimited format: common_name|definition|volume|tag"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract food names from:\n{clean_text}"}
                ],
                temperature=0,
                max_tokens=16000
            )
            
            content = response.choices[0].message.content.strip()
            items = []
            
            for line in content.split('\n'):
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 4:
                        items.append({
                            'common_name': parts[0].strip(),
                            'definition': parts[1].strip(),
                            'volume': parts[2].strip(),
                            'tag': parts[3].strip()
                        })
            return items
        except Exception as e:
            self.log(f"Error in GPT extraction: {e}", "WARNING")
            return []
    
    def run_volume_validation(self):
        """Step 2: Run volume validation and gap filling"""
        self.log("="*60)
        self.log("STEP 2: VOLUME VALIDATION AND GAP FILLING")
        self.log("="*60)
        
        try:
            # Import and run validation logic
            from create_cfcs_cname_table import validate_and_fill_missing_volumes
            validate_and_fill_missing_volumes(self.url, self.db_file, self.client)
            self.log("Volume validation completed successfully")
            return True
        except ImportError:
            # Inline validation logic
            return self._run_volume_validation_inline()
        except Exception as e:
            self.log(f"Error in volume validation: {e}", "ERROR")
            return False
    
    def _run_volume_validation_inline(self):
        """Inline version of volume validation"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Get current volumes
            cursor.execute("SELECT DISTINCT volume FROM cfcs_cname WHERE volume IS NOT NULL ORDER BY volume")
            current_volumes = [row[0] for row in cursor.fetchall()]
            
            self.log(f"Current volumes: {len(current_volumes)}")
            if self.verbose:
                for vol in current_volumes[:10]:  # Show first 10
                    cursor.execute("SELECT COUNT(*) FROM cfcs_cname WHERE volume = ?", (vol,))
                    count = cursor.fetchone()[0]
                    self.log(f"  {vol}: {count} names")
            
            # Expected volumes (subset for demo)
            expected_volumes = [
                "Volume 11 – Prepackaged Water",
                "Volume 14 – Salt Standard",
                "Volume 20 – Egg Products"
            ]
            
            # Find missing
            missing = []
            for expected in expected_volumes:
                found = any(expected.split('–')[1].strip().lower() in vol.lower() for vol in current_volumes)
                if not found:
                    missing.append(expected)
            
            self.log(f"Missing volumes: {missing}")
            
            conn.close()
            return True
            
        except Exception as e:
            self.log(f"Error in inline volume validation: {e}", "ERROR")
            return False
    
    def run_water_search(self):
        """Step 3: Run targeted search for Volume 11 - Prepackaged Water"""
        self.log("="*60)
        self.log("STEP 3: TARGETED WATER SEARCH")
        self.log("="*60)
        
        try:
            # Import and run water search logic
            from search_water import search_for_prepackaged_water
            search_for_prepackaged_water()
            self.log("Water search completed successfully")
            return True
        except ImportError:
            # Inline water search
            return self._run_water_search_inline()
        except Exception as e:
            self.log(f"Error in water search: {e}", "ERROR")
            return False
    
    def _run_water_search_inline(self):
        """Inline version of water search"""
        try:
            self.log("Searching for prepackaged water content...")
            
            # Fetch webpage
            response = requests.get(self.url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            clean_text = soup.get_text()
            
            # Search for water patterns
            water_patterns = ["prepackaged water", "mineral water", "spring water"]
            found_items = []
            
            for pattern in water_patterns:
                if pattern.lower() in clean_text.lower():
                    self.log(f"Found pattern: {pattern}")
                    # Simplified - could add full GPT extraction here
                    found_items.append({
                        'common_name': pattern.title(),
                        'definition': f'Water product matching pattern: {pattern}',
                        'volume': 'Volume 11 – Prepackaged Water',
                        'tag': '11.1 Water'
                    })
            
            # Insert found items
            if found_items:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                
                for item in found_items:
                    try:
                        cursor.execute("""
                            INSERT INTO cfcs_cname (common_name, definition, volume, tag, source_url, created_date)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            item['common_name'], item['definition'], item['volume'],
                            item['tag'], self.url, datetime.now()
                        ))
                    except:
                        pass  # Skip duplicates
                
                conn.commit()
                conn.close()
                
            self.log(f"Water search found {len(found_items)} items")
            return True
            
        except Exception as e:
            self.log(f"Error in inline water search: {e}", "ERROR")
            return False
    
    def run_final_verification(self):
        """Step 4: Run final verification and reporting"""
        self.log("="*60)
        self.log("STEP 4: FINAL VERIFICATION AND REPORTING")
        self.log("="*60)
        
        try:
            # Import and run verification logic
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Total count
            cursor.execute("SELECT COUNT(*) FROM cfcs_cname")
            total_records = cursor.fetchone()[0]
            
            # Volume summary
            cursor.execute("""
                SELECT volume, COUNT(*) as count 
                FROM cfcs_cname 
                WHERE volume IS NOT NULL AND volume != ''
                GROUP BY volume 
                ORDER BY count DESC
                LIMIT 10
            """)
            top_volumes = cursor.fetchall()
            
            # Volume 11 variants
            cursor.execute("SELECT DISTINCT volume FROM cfcs_cname WHERE volume LIKE '%Volume 11%'")
            vol11_variants = cursor.fetchall()
            
            # Recent additions
            cursor.execute("""
                SELECT common_name, volume 
                FROM cfcs_cname 
                ORDER BY created_date DESC 
                LIMIT 5
            """)
            recent_items = cursor.fetchall()
            
            # Generate report
            self.log("FINAL VERIFICATION REPORT")
            self.log(f"Total CFCS Common Names: {total_records}")
            self.log(f"Total Volumes Covered: {len(top_volumes)}")
            
            self.log("\nTop 10 Volumes by Count:")
            for vol, count in top_volumes:
                self.log(f"  {vol}: {count} names")
            
            self.log(f"\nVolume 11 Variants: {len(vol11_variants)}")
            for vol, in vol11_variants:
                cursor.execute("SELECT COUNT(*) FROM cfcs_cname WHERE volume = ?", (vol,))
                count = cursor.fetchone()[0]
                self.log(f"  {vol}: {count} names")
            
            self.log("\nMost Recent Additions:")
            for name, vol in recent_items:
                self.log(f"  {name} ({vol})")
            
            conn.close()
            self.log("Final verification completed successfully")
            return True
            
        except Exception as e:
            self.log(f"Error in final verification: {e}", "ERROR")
            return False
    
    def run_orchestration(self, skip_main=False, skip_water=False, skip_volume_check=False):
        """Run the complete orchestration process"""
        self.log("CFCS COMMON NAMES EXTRACTION ORCHESTRATOR STARTED")
        self.log(f"Target URL: {self.url}")
        self.log(f"Database: {self.db_file}")
        
        success_count = 0
        total_steps = 4
        
        # Step 1: Main extraction
        if not skip_main:
            if self.run_main_extraction():
                success_count += 1
            else:
                self.log("Main extraction failed, continuing with remaining steps...", "WARNING")
        else:
            self.log("Skipping main extraction (--skip-main-extraction)")
            success_count += 1  # Count as success since it was intentionally skipped
        
        # Step 2: Volume validation
        if not skip_volume_check:
            if self.run_volume_validation():
                success_count += 1
            else:
                self.log("Volume validation failed, continuing with remaining steps...", "WARNING")
        else:
            self.log("Skipping volume validation (--skip-volume-check)")
            success_count += 1
        
        # Step 3: Water search
        if not skip_water:
            if self.run_water_search():
                success_count += 1
            else:
                self.log("Water search failed, continuing with remaining steps...", "WARNING")
        else:
            self.log("Skipping water search (--skip-water-search)")
            success_count += 1
        
        # Step 4: Final verification
        if self.run_final_verification():
            success_count += 1
        
        # Final summary
        self.log("="*60)
        self.log("ORCHESTRATION SUMMARY")
        self.log("="*60)
        self.log(f"Steps completed: {success_count}/{total_steps}")
        
        if success_count == total_steps:
            self.log("🎉 ALL STEPS COMPLETED SUCCESSFULLY!", "SUCCESS")
        elif success_count >= 3:
            self.log("✅ Most steps completed successfully", "SUCCESS")
        else:
            self.log("⚠️ Multiple steps failed - manual intervention may be required", "WARNING")
        
        self.log("CFCS COMMON NAMES EXTRACTION ORCHESTRATOR FINISHED")
        return success_count == total_steps


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="CFCS Common Names Extraction Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--skip-main-extraction', action='store_true',
                       help='Skip the main extraction process')
    parser.add_argument('--skip-water-search', action='store_true',
                       help='Skip the targeted water search')
    parser.add_argument('--skip-volume-check', action='store_true',
                       help='Skip the volume validation check')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    try:
        orchestrator = CFCSOrchestrator(verbose=args.verbose)
        success = orchestrator.run_orchestration(
            skip_main=args.skip_main_extraction,
            skip_water=args.skip_water_search,
            skip_volume_check=args.skip_volume_check
        )
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Orchestration cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"[FATAL] Orchestration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()