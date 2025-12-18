"""
In-memory storage with seed data for testing.
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import random
import base64
import tempfile
import os
import sys
from pathlib import Path
from models import Project, ProjectFile, Analysis, User

# Add core module to path for evaluator import
sys.path.insert(0, str(Path(__file__).parent.parent / 'core' / 'evaluator'))
sys.path.insert(0, str(Path(__file__).parent.parent))



class Storage:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.projects: Dict[str, Project] = {}
        self.files: Dict[str, ProjectFile] = {}
        self.analyses: Dict[str, Analysis] = {}
        self._seed_data()

    def _seed_data(self):
        """Seed with sample data for immediate testing."""
        # Create sample projects
        project1 = Project(
            id="proj-1",
            name="Maple Syrup Label Review",
            description="Compliance review for Grade A maple syrup products for Canadian market",
            tags=["maple", "grade-a", "organic"],
            createdAt=(datetime.now() - timedelta(days=5)).isoformat()
        )
        project2 = Project(
            id="proj-2",
            name="Organic Honey Labels",
            description="Review multi-language honey product labels for CFIA compliance",
            tags=["honey", "bilingual", "organic"],
            createdAt=(datetime.now() - timedelta(days=2)).isoformat()
        )
        self.projects[project1.id] = project1
        self.projects[project2.id] = project2

        # Create sample files for project 1
        file1 = ProjectFile(
            id="file-1",
            name="maple_syrup_front.jpg",
            type="image",
            url="https://placehold.co/400x600/2a2a2a/ffffff?text=Maple+Syrup+Front",
            tags=["front"],
            projectId="proj-1"
        )
        file2 = ProjectFile(
            id="file-2",
            name="maple_syrup_back.jpg",
            type="image",
            url="https://placehold.co/400x600/2a2a2a/ffffff?text=Maple+Syrup+Back",
            tags=["back"],
            projectId="proj-1"
        )
        self.files[file1.id] = file1
        self.files[file2.id] = file2

        # Create a completed analysis for project 1
        analysis1 = Analysis(
            id="analysis-1",
            name="Food Labelling Analysis #1",
            status="completed",
            progress=100,
            resultSummary="All labelling requirements met. Minor recommendation: Consider increasing font size for allergen warnings.",
            details={
                "bilingual_compliance": "Pass",
                "net_quantity": "Pass",
                "ingredients_list": "Pass",
                "nutrition_facts": "Pass",
                "allergens": "Minor Issue"
            },
            createdAt=(datetime.now() - timedelta(hours=2)).isoformat(),
            projectId="proj-1"
        )
        self.analyses[analysis1.id] = analysis1

    # User methods
    def get_mock_user(self) -> User:
        return User(
            id="user-1",
            name="Demo User",
            email="demo@bluora.ai",
            avatar="https://api.dicebear.com/7.x/avataaars/svg?seed=demo"
        )

    # Project methods
    def list_projects(self) -> List[Project]:
        return list(self.projects.values())

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.projects.get(project_id)

    def create_project(self, name: str, description: Optional[str], tags: List[str]) -> Project:
        project = Project(name=name, description=description, tags=tags)
        self.projects[project.id] = project
        return project

    def update_project(self, project_id: str, name: Optional[str], description: Optional[str], tags: Optional[List[str]]) -> Optional[Project]:
        project = self.projects.get(project_id)
        if not project:
            return None
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if tags is not None:
            project.tags = tags
        return project

    def delete_project(self, project_id: str) -> bool:
        if project_id in self.projects:
            del self.projects[project_id]
            # Also delete associated files and analyses
            self.files = {k: v for k, v in self.files.items() if v.projectId != project_id}
            self.analyses = {k: v for k, v in self.analyses.items() if v.projectId != project_id}
            return True
        return False

    # File methods
    def list_files(self, project_id: str) -> List[ProjectFile]:
        return [f for f in self.files.values() if f.projectId == project_id]

    def create_file(self, project_id: str, name: str, file_type: str, url: str, tags: List[str]) -> ProjectFile:
        file = ProjectFile(
            name=name,
            type=file_type,
            url=url,
            tags=tags,
            projectId=project_id
        )
        self.files[file.id] = file
        return file

    def delete_file(self, file_id: str) -> bool:
        if file_id in self.files:
            del self.files[file_id]
            return True
        return False

    # Analysis methods
    def list_analyses(self, project_id: str) -> List[Analysis]:
        return [a for a in self.analyses.values() if a.projectId == project_id]

    def create_analysis(self, project_id: str, name: str) -> Analysis:
        analysis = Analysis(
            name=name,
            status="running",
            progress=0,
            projectId=project_id
        )
        self.analyses[analysis.id] = analysis
        return analysis

    async def run_real_analysis(self, analysis_id: str):
        """Run actual AI-powered label analysis using MultiImageLabelEvaluator."""
        print(f"[DEBUG] Starting analysis for ID: {analysis_id}")
        analysis = self.analyses.get(analysis_id)
        if not analysis:
            print(f"[DEBUG] Analysis not found: {analysis_id}")
            return
        
        try:
            # Update progress: starting
            analysis.progress = 10
            analysis.status = "running"
            print(f"[DEBUG] Analysis running for project: {analysis.projectId}")
            
            # Get project files
            project_files = self.list_files(analysis.projectId)
            image_files = [f for f in project_files if f.type == "image"]
            print(f"[DEBUG] Found {len(image_files)} image files")
            
            if not image_files:
                analysis.status = "failed"
                analysis.resultSummary = "No images found in project. Please upload label images first."
                analysis.progress = 100
                return
            
            analysis.progress = 20
            
            # Save images to temp files for evaluator (it needs file paths)
            temp_dir = tempfile.mkdtemp(prefix="labeliq_")
            temp_image_paths = []
            
            for i, pf in enumerate(image_files):
                try:
                    print(f"[DEBUG] Processing image {i}: {pf.name}, URL starts with: {pf.url[:50]}...")
                    # Handle data URLs (base64 encoded images)
                    if pf.url.startswith("data:"):
                        # Extract base64 data
                        header, b64_data = pf.url.split(",", 1)
                        image_data = base64.b64decode(b64_data)
                        
                        # Determine extension from content type
                        ext = ".jpg"
                        if "png" in header:
                            ext = ".png"
                        elif "gif" in header:
                            ext = ".gif"
                        elif "webp" in header:
                            ext = ".webp"
                        
                        temp_path = os.path.join(temp_dir, f"image_{i}{ext}")
                        with open(temp_path, "wb") as f:
                            f.write(image_data)
                        temp_image_paths.append(temp_path)
                        print(f"[DEBUG] Saved data URL image to {temp_path}")
                    else:
                        print(f"[DEBUG] Skipping non-data URL: {pf.url[:50]}...")
                except Exception as e:
                    print(f"Error saving temp image {pf.name}: {e}")
                    continue
            
            if not temp_image_paths:
                analysis.status = "failed"
                analysis.resultSummary = "Could not process uploaded images."
                analysis.progress = 100
                return
            
            analysis.progress = 30
            print(f"[DEBUG] Saved {len(temp_image_paths)} temp images to {temp_dir}")
            
            # Import and run the evaluator
            try:
                print("[DEBUG] Importing MultiImageLabelEvaluator...")
                from multi_image_evaluator import MultiImageLabelEvaluator
                print("[DEBUG] Import successful, creating evaluator...")
                
                analysis.progress = 40
                
                # Run evaluation in a thread to not block async
                import concurrent.futures
                
                def run_evaluation():
                    print("[DEBUG] Creating evaluator instance...")
                    evaluator = MultiImageLabelEvaluator()
                    print("[DEBUG] Starting image processing...")
                    return evaluator.process_product_images(temp_image_paths)
                
                # Run in executor
                print("[DEBUG] Running evaluation in executor...")
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    evaluation_result = await loop.run_in_executor(executor, run_evaluation)
                
                print("[DEBUG] Evaluation completed successfully")
                analysis.progress = 90
                
                # Map evaluator results to frontend format
                rule_evaluations = evaluation_result.get("rule_evaluations", {})
                overall = evaluation_result.get("overall_compliance", {})
                critical_issues = evaluation_result.get("critical_issues", [])
                
                # Build details dict for frontend
                details = {}
                rule_names = {
                    1: "common_name_present",
                    2: "common_name_exempt",
                    3: "common_name_on_pdp",
                    4: "common_name_text_size",
                    5: "small_package_text_size",
                    6: "appropriate_common_name",
                    7: "standards_compliance",
                    8: "regulation_compliance",
                    9: "descriptive_name",
                    10: "true_nature_description",
                    11: "bilingual_common_name"
                }
                
                # Bilingual rules names
                bilingual_rule_names = {
                    1: "bilingual_all_mandatory",
                    2: "bilingual_exemption"
                }
                
                # Net quantity rules names
                net_qty_rule_names = {
                    1: "net_qty_present",
                    2: "net_qty_exempt",
                    3: "net_qty_on_pdp",
                    4: "net_qty_metric",
                    5: "net_qty_retail_bulk",
                    6: "net_qty_manner",
                    7: "net_qty_rounding",
                    8: "net_qty_symbols",
                    9: "net_qty_written_units",
                    10: "net_qty_type_height",
                    11: "net_qty_canadian_units",
                    12: "net_qty_us_units"
                }
                
                # Ingredients/allergen rules names
                ingredients_rule_names = {
                    1: "ingredients_present",
                    2: "ingredients_exempt",
                    3: "ingredients_order",
                    4: "ingredients_common_names",
                    5: "components_declared",
                    6: "sugars_grouped",
                    7: "allergens_declared",
                    8: "contains_statement",
                    9: "cross_contamination",
                    10: "statements_position",
                    11: "phenylalanine",
                    12: "statements_order",
                    13: "bilingual_match",
                    14: "formatting_legibility",
                    15: "location_requirements"
                }
                
                # Nutrition rules names
                nutrition_rule_names = {
                    1: "nft_present",
                    2: "nft_exempt",
                    3: "nft_location",
                    4: "serving_size",
                    5: "core_nutrients",
                    6: "units_dv",
                    7: "dv_statement",
                    8: "format_appropriate",
                    9: "format_version",
                    10: "graphical_colours",
                    11: "graphical_font",
                    12: "fop_present",
                    13: "fop_thresholds",
                    14: "fop_specs",
                    15: "fop_location"
                }
                
                # Date marking rules names
                date_rule_names = {
                    1: "best_before_present",
                    2: "best_before_wording",
                    3: "best_before_format",
                    4: "best_before_location",
                    5: "packaged_on_present",
                    6: "packaged_on_wording",
                    7: "expiration_date",
                    8: "storage_instructions",
                    9: "date_grouped",
                    10: "date_legibility"
                }
                
                for rule_key, evaluation in rule_evaluations.items():
                    # Handle date marking rules (date_rule_1, etc.)
                    if rule_key.startswith("date_rule_"):
                        rule_num = int(rule_key.replace("date_rule_", ""))
                        rule_name = date_rule_names.get(rule_num, rule_key)
                    # Handle nutrition rules (nutrition_rule_1, etc.)
                    elif rule_key.startswith("nutrition_rule_"):
                        rule_num = int(rule_key.replace("nutrition_rule_", ""))
                        rule_name = nutrition_rule_names.get(rule_num, rule_key)
                    # Handle ingredients rules (ingredients_rule_1, etc.)
                    elif rule_key.startswith("ingredients_rule_"):
                        rule_num = int(rule_key.replace("ingredients_rule_", ""))
                        rule_name = ingredients_rule_names.get(rule_num, rule_key)
                    # Handle origin rules (origin_rule_1, etc.)
                    elif rule_key.startswith("origin_rule_"):
                        origin_rule_names = {
                            1: "origin_required", 2: "origin_present", 3: "origin_format",
                            4: "origin_bilingual", 5: "origin_legibility"
                        }
                        rule_num = int(rule_key.replace("origin_rule_", ""))
                        rule_name = origin_rule_names.get(rule_num, rule_key)
                    # Handle net quantity rules (net_qty_rule_1, etc.)
                    elif rule_key.startswith("net_qty_rule_"):
                        rule_num = int(rule_key.replace("net_qty_rule_", ""))
                        rule_name = net_qty_rule_names.get(rule_num, rule_key)
                    # Handle bilingual rules (bilingual_rule_1, bilingual_rule_2)
                    elif rule_key.startswith("bilingual_rule_"):
                        rule_num = int(rule_key.replace("bilingual_rule_", ""))
                        rule_name = bilingual_rule_names.get(rule_num, rule_key)
                    else:
                        # Handle common name rules (rule_1, rule_2, etc.)
                        rule_num = int(rule_key.replace("rule_", ""))
                        rule_name = rule_names.get(rule_num, f"rule_{rule_num}")
                    
                    if evaluation.get("compliant") is True:
                        details[rule_name] = "Pass"
                    elif evaluation.get("compliant") is False:
                        details[rule_name] = "Fail"
                    else:
                        details[rule_name] = "Unknown"
                
                # Build summary
                status = overall.get("status", "Unknown")
                summary_text = overall.get("summary", "Analysis completed.")
                
                if critical_issues:
                    summary_text += f" Critical issues: {'; '.join(critical_issues[:3])}"
                
                analysis.resultSummary = summary_text
                analysis.details = details
                
                # Store full evaluation data for PDF report generation
                analysis.details['_fullEvaluationData'] = {
                    'rule_evaluations': rule_evaluations,
                    'overall_compliance': overall,
                    'critical_issues': critical_issues,
                    'extracted_label_data': evaluation_result.get('extracted_label_data', {})
                }
                
                analysis.status = "completed"
                analysis.progress = 100
                
            except ImportError as e:
                print(f"Evaluator import error: {e}")
                # Fallback to basic analysis if evaluator not available
                analysis.status = "completed"
                analysis.resultSummary = f"Basic analysis completed. Full AI evaluation unavailable: {str(e)}"
                analysis.details = {"status": "Evaluator unavailable"}
                analysis.progress = 100
                
            except Exception as e:
                print(f"Evaluation error: {e}")
                import traceback
                traceback.print_exc()
                analysis.status = "failed"
                analysis.resultSummary = f"Analysis failed: {str(e)}"
                analysis.progress = 100
            
            finally:
                # Cleanup temp files
                for temp_path in temp_image_paths:
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                try:
                    os.rmdir(temp_dir)
                except:
                    pass
                    
        except Exception as e:
            print(f"Analysis error: {e}")
            import traceback
            traceback.print_exc()
            analysis.status = "failed"
            analysis.resultSummary = f"Analysis error: {str(e)}"
            analysis.progress = 100


# Global storage instance
storage = Storage()

