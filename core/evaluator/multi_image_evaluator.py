"""
Multi-Image Label Evaluator - Process multiple product images and evaluate against common name rules
"""

import sqlite3, config
import pickle
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Google Vision API
from google.cloud import vision

# OpenAI for embeddings and evaluation
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity

# Import rule methods
import sys
sys.path.append(str(Path(__file__).parent.parent / 'rules'))

class MultiImageLabelEvaluator:
    """Comprehensive system for OCR multiple product images and evaluating common name rules"""
    
    def __init__(self, db_path=str(Path(__file__).parent.parent.parent / 'data' / 'ilt_requirements.db'), api_key=config.OPENAI_API_KEY, 
                 google_credentials_path=None):
        self.db_path = Path(db_path)
        self.client = OpenAI(api_key=api_key)
        
        # Initialize Google Vision - use config, then fallback to default path
        if google_credentials_path is None:
            google_credentials_path = config.GOOGLE_CREDENTIALS or str(Path(__file__).parent.parent.parent / 'google-credentials.json')
        if google_credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_credentials_path
        self.vision_client = vision.ImageAnnotatorClient()
        
        # Load knowledge base
        self.knowledge_base = []
        self.load_knowledge_base()
    
    def load_knowledge_base(self):
        """Load embeddings knowledge base for rule evaluation"""
        
        if not self.db_path.exists():
            print(f"Warning: Database {self.db_path} not found. Rule evaluation will use basic logic.")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if embeddings table exists
        cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='common_name_embeddings'
        """)
        
        if not cursor.fetchone():
            print("Warning: Embeddings table not found. Run create_embeddings_system.py first.")
            conn.close()
            return
        
        cursor.execute("""
        SELECT e.source_id, e.rule_number, e.content_type, e.title, 
               e.content_text, e.embedding,
               c.concise_summary, c.compliance_keywords, c.regulatory_context
        FROM common_name_embeddings e
        JOIN common_name_all c ON e.source_id = c.id
        ORDER BY e.rule_number, e.id
        """)
        
        for record in cursor.fetchall():
            (source_id, rule_number, content_type, title, content_text, 
             embedding_blob, concise_summary, compliance_keywords, regulatory_context) = record
            
            self.knowledge_base.append({
                'source_id': source_id,
                'rule_number': rule_number,
                'content_type': content_type,
                'title': title,
                'content_text': content_text,
                'embedding': pickle.loads(embedding_blob),
                'concise_summary': concise_summary,
                'compliance_keywords': compliance_keywords,
                'regulatory_context': regulatory_context
            })
        
        conn.close()
        print(f"✓ Loaded {len(self.knowledge_base)} embeddings for rule evaluation")
    
    def process_product_images(self, image_paths: List[str], 
                              product_info: Dict = None) -> Dict[str, Any]:
        """Process multiple product images and evaluate common name and bilingual compliance"""
        
        print(f"Processing {len(image_paths)} product images...")
        
        # Step 1: OCR all images
        ocr_results = self.ocr_multiple_images(image_paths)
        
        # Step 2: Extract label data from OCR results
        label_data = self.extract_label_data(ocr_results, product_info)
        
        # Step 3: Evaluate against common name rules (1-11)
        rule_evaluations = self.evaluate_common_name_rules(label_data)
        
        # Step 4: Evaluate bilingual requirements
        bilingual_evaluations = self.evaluate_bilingual_requirements(label_data)
        rule_evaluations.update(bilingual_evaluations)
        
        # Step 5: Create comprehensive report
        evaluation_report = {
            'product_info': product_info or {},
            'images_processed': len(image_paths),
            'ocr_results': ocr_results,
            'extracted_label_data': label_data,
            'rule_evaluations': rule_evaluations,
            'overall_compliance': self.calculate_overall_compliance(rule_evaluations),
            'processing_timestamp': datetime.utcnow().isoformat(),
            'critical_issues': self.identify_critical_issues(rule_evaluations)
        }
        
        return evaluation_report
    
    def ocr_multiple_images(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """Perform OCR on multiple product images"""
        
        ocr_results = []
        
        for i, image_path in enumerate(image_paths, 1):
            print(f"  OCR processing image {i}/{len(image_paths)}: {Path(image_path).name}")
            
            try:
                # Determine image type based on filename or user input
                image_type = self.determine_image_type(image_path)
                
                # Perform OCR
                ocr_result = self.ocr_single_image(image_path)
                
                if ocr_result:
                    ocr_result['image_type'] = image_type
                    ocr_result['image_path'] = image_path
                    ocr_result['image_name'] = Path(image_path).name
                    ocr_results.append(ocr_result)
                    print(f"    ✓ OCR completed ({len(ocr_result.get('text', ''))} chars extracted)")
                else:
                    print(f"    ✗ OCR failed for {image_path}")
                
            except Exception as e:
                print(f"    ✗ Error processing {image_path}: {str(e)}")
                continue
        
        return ocr_results
    
    def ocr_single_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Perform OCR on a single image using Google Vision API"""
        
        try:
            # Read image
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            # Create Vision API image object
            image = vision.Image(content=content)
            
            # Configure for multiple languages
            image_context = vision.ImageContext(
                language_hints=['en', 'fr', 'ko', 'zh-CN', 'pl']
            )
            
            # Perform OCR with bounding boxes
            response = self.vision_client.text_detection(
                image=image, 
                image_context=image_context
            )
            
            if response.error.message:
                print(f"    Vision API error: {response.error.message}")
                return None
            
            # Extract text and bounding boxes
            texts = response.text_annotations
            if not texts:
                return {'text': '', 'blocks': []}
            
            # First annotation is the full text
            full_text = texts[0].description
            
            # Remaining annotations are individual text blocks
            blocks = []
            for text in texts[1:]:  # Skip first (full text)
                vertices = [(vertex.x, vertex.y) for vertex in text.bounding_poly.vertices]
                
                # Calculate bounding box
                x_coords = [v[0] for v in vertices]
                y_coords = [v[1] for v in vertices]
                
                blocks.append({
                    'text': text.description,
                    'bounding_box': {
                        'x1': min(x_coords), 'y1': min(y_coords),
                        'x2': max(x_coords), 'y2': max(y_coords),
                        'vertices': vertices
                    }
                })
            
            return {
                'text': full_text,
                'blocks': blocks,
                'total_blocks': len(blocks)
            }
            
        except Exception as e:
            print(f"    OCR error: {str(e)}")
            return None
    
    def determine_image_type(self, image_path: str) -> str:
        """Determine image type (front, back, top, etc.) from filename"""
        
        filename = Path(image_path).name.lower()
        
        # Auto-detect from filename
        if 'front' in filename or 'pdp' in filename:
            return 'front'
        elif 'back' in filename:
            return 'back'
        elif 'top' in filename:
            return 'top'
        elif 'bottom' in filename:
            return 'bottom'
        elif 'side' in filename:
            return 'side'
        elif 'ingredient' in filename:
            return 'ingredients'
        elif 'nutrition' in filename:
            return 'nutrition'
        else:
            return 'other'
    
    def extract_label_data(self, ocr_results: List[Dict], 
                          product_info: Dict = None) -> Dict[str, Any]:
        """Extract structured label data from OCR results using AI"""
        
        # Combine all OCR text by image type
        combined_text = {}
        all_text = ""
        
        for ocr in ocr_results:
            image_type = ocr.get('image_type', 'unknown')
            text = ocr.get('text', '')
            
            combined_text[image_type] = text
            all_text += f"\n{image_type.upper()}:\n{text}\n"
        
        # Use GPT to extract structured label data
        extracted_data = self.ai_extract_label_data(all_text, combined_text, product_info)
        
        # Add OCR metadata
        extracted_data['ocr_metadata'] = {
            'images_processed': len(ocr_results),
            'image_types': [ocr.get('image_type') for ocr in ocr_results],
            'total_text_chars': len(all_text),
            'text_by_image_type': {k: len(v) for k, v in combined_text.items()}
        }
        
        return extracted_data
    
    def ai_extract_label_data(self, all_text: str, text_by_type: Dict, 
                             product_info: Dict = None) -> Dict[str, Any]:
        """Use AI to extract structured label data from OCR text"""
        
        system_prompt = """You are an expert food label analysis system. Extract structured label data from OCR text.

You MUST respond with ONLY a valid JSON object. No additional text, explanations, or markdown formatting.

Extract and return exactly this JSON structure:
{
    "common_name": "Primary common name found on label",
    "common_name_location": "front/back/top/etc - where common name was found",
    "common_name_text_size_estimate": "estimated text size in mm or unknown",
    "product_type": "category like dairy, meat, beverages, etc",
    "package_size_cm2": "estimated principal display panel area in cm² or unknown",
    "brand_name": "brand name if visible",
    "net_quantity": "net weight/volume statement",
    "ingredients_list": "ingredients if visible",
    "nutrition_facts": "nutrition information if visible",
    "other_claims": ["list of claims found like organic, natural, etc"],
    "bilingual_compliance": "whether French text is present - true/false/unknown",
    "regulatory_statements": ["required statements found"],
    "text_analysis": {
        "largest_text": "largest text found",
        "smallest_text": "smallest readable text",
        "pdp_identified": true
    }
}

Focus on information relevant to CFIA common name compliance evaluation. Use "unknown" for fields that cannot be determined from the OCR text."""
        
        context = ""
        if product_info:
            context = f"Additional product context: {json.dumps(product_info)}\n\n"
        
        user_prompt = f"""{context}Extract structured label data from this OCR text. Respond with ONLY valid JSON:

OCR TEXT FROM ALL IMAGES:
{all_text[:8000]}

Return only the JSON object with no additional text."""
        
        try:
            print("    Extracting label data with AI...")
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use mini for better reliability
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=2000
            )
            
            response_content = response.choices[0].message.content.strip()
            print(f"    GPT response length: {len(response_content)} chars")
            print(f"    GPT response preview: {response_content[:200]}...")
            
            # Clean response - remove any markdown formatting
            if response_content.startswith('```json'):
                response_content = response_content.replace('```json', '').replace('```', '').strip()
            elif response_content.startswith('```'):
                response_content = response_content.replace('```', '').strip()
            
            # Try to parse JSON
            extracted_data = json.loads(response_content)
            print("    ✓ Successfully extracted label data")
            return extracted_data
            
        except json.JSONDecodeError as e:
            print(f"    ✗ JSON parsing error: {str(e)}")
            print(f"    Response content: {response_content[:500]}...")
            
            # Try to fix common JSON issues
            try:
                # Remove any text before first {
                start_idx = response_content.find('{')
                end_idx = response_content.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    cleaned_content = response_content[start_idx:end_idx]
                    extracted_data = json.loads(cleaned_content)
                    print("    ✓ Successfully parsed cleaned JSON")
                    return extracted_data
                else:
                    raise ValueError("No valid JSON structure found")
                    
            except Exception as e2:
                print(f"    ✗ JSON cleanup failed: {str(e2)}")
                return self.create_fallback_extraction(text_by_type, str(e))
            
        except Exception as e:
            print(f"    ✗ AI extraction error: {str(e)}")
            return self.create_fallback_extraction(text_by_type, str(e))
    
    def create_fallback_extraction(self, text_by_type: Dict, error_msg: str) -> Dict[str, Any]:
        """Create fallback extraction when AI fails"""
        
        print("    Using fallback extraction method...")
        
        # Basic text analysis
        common_name = self.basic_extract_common_name(text_by_type)
        
        # Determine location
        location = "unknown"
        for img_type in ['front', 'pdp', 'top']:
            if img_type in text_by_type and text_by_type[img_type]:
                if common_name.lower() in text_by_type[img_type].lower():
                    location = img_type
                    break
        
        # Look for French text
        all_text = " ".join(text_by_type.values()).lower()
        has_french = any(word in all_text for word in ['ingrédients', 'nutrition', 'ml', 'grammes', 'sans'])
        
        # Basic product type detection
        product_type = "unknown"
        if any(word in all_text for word in ['milk', 'lait']):
            product_type = "dairy"
        elif any(word in all_text for word in ['juice', 'jus']):
            product_type = "beverage"
        elif any(word in all_text for word in ['bread', 'pain']):
            product_type = "bakery"
        
        return {
            "common_name": common_name,
            "common_name_location": location,
            "common_name_text_size_estimate": "unknown",
            "product_type": product_type,
            "package_size_cm2": "unknown",
            "brand_name": "unknown",
            "net_quantity": "unknown",
            "ingredients_list": "unknown",
            "nutrition_facts": "unknown",
            "other_claims": [],
            "bilingual_compliance": "true" if has_french else "false",
            "regulatory_statements": [],
            "text_analysis": {
                "largest_text": common_name,
                "smallest_text": "unknown",
                "pdp_identified": location in ['front', 'pdp']
            },
            "extraction_method": "fallback",
            "extraction_error": error_msg,
            "ocr_text_sample": list(text_by_type.values())[0][:200] if text_by_type else "No text found"
        }
    
    def basic_extract_common_name(self, text_by_type: Dict) -> str:
        """Basic fallback method to extract common name"""
        
        # Look for common name on front/PDP first
        priority_types = ['front', 'pdp', 'top', 'other']
        
        for img_type in priority_types:
            text = text_by_type.get(img_type, '')
            if text:
                lines = text.split('\n')
                # Return first substantial line as potential common name
                for line in lines:
                    line = line.strip()
                    if len(line) > 2 and not line.isdigit():
                        return line
        
        # Fallback to any text found
        for text in text_by_type.values():
            if text.strip():
                return text.split('\n')[0].strip()
        
        return "No common name detected"
    
    def evaluate_common_name_rules(self, label_data: Dict) -> Dict[str, Any]:
        """Evaluate label data against all common name rules"""
        
        print(f"\nEvaluating common name compliance...")
        
        rule_results = {}
        
        # Evaluate rules 1-11
        for rule_num in range(1, 12):
            print(f"  Evaluating Rule {rule_num}...")
            
            try:
                # Get rule evaluation using embeddings and AI
                evaluation = self.evaluate_single_rule(rule_num, label_data)
                rule_results[f"rule_{rule_num}"] = evaluation
                
                status = "✓" if evaluation.get('compliant') else "✗"
                confidence = evaluation.get('confidence', 0.0)
                print(f"    {status} Rule {rule_num}: {evaluation.get('finding', 'No finding')} (confidence: {confidence:.2f})")
                
            except Exception as e:
                print(f"    ✗ Error evaluating Rule {rule_num}: {str(e)}")
                rule_results[f"rule_{rule_num}"] = {
                    "compliant": None,
                    "confidence": 0.0,
                    "finding": f"Evaluation error: {str(e)}",
                    "error": str(e)
                }
        
        return rule_results
    
    def evaluate_single_rule(self, rule_number: int, label_data: Dict) -> Dict[str, Any]:
        """Evaluate a single rule using AI with semantic context"""
        
        # Get rule-specific context from knowledge base
        rule_context = [item for item in self.knowledge_base if item['rule_number'] == rule_number]
        
        # Create evaluation query for semantic search
        query = self.create_evaluation_query(rule_number, label_data)
        
        # Get semantically relevant context
        relevant_context = self.search_relevant_context(query, rule_number, top_k=3)
        
        # Use AI to evaluate
        evaluation = self.ai_evaluate_rule(rule_number, label_data, rule_context, relevant_context)
        
        return evaluation
    
    def create_evaluation_query(self, rule_number: int, label_data: Dict) -> str:
        """Create query for semantic search"""
        
        query_parts = [f"Rule {rule_number} evaluation"]
        
        if label_data.get('common_name'):
            query_parts.append(f"common name: {label_data['common_name']}")
        
        if label_data.get('product_type'):
            query_parts.append(f"product type: {label_data['product_type']}")
        
        if label_data.get('package_size_cm2'):
            query_parts.append(f"package size: {label_data['package_size_cm2']}")
        
        return " ".join(query_parts)
    
    def search_relevant_context(self, query: str, rule_number: int = None, top_k: int = 3) -> List[Dict]:
        """Search for semantically relevant context"""
        
        if not self.knowledge_base:
            return []
        
        try:
            # Get query embedding
            response = self.client.embeddings.create(input=query, model="text-embedding-3-small")
            query_embedding = response.data[0].embedding
        except:
            return []
        
        # Calculate similarities
        similarities = []
        for item in self.knowledge_base:
            if rule_number and item['rule_number'] != rule_number:
                continue
            
            similarity = cosine_similarity([query_embedding], [item['embedding']])[0][0]
            similarities.append((similarity, item))
        
        # Return top similar items
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in similarities[:top_k]]
    
    def ai_evaluate_rule(self, rule_number: int, label_data: Dict, 
                        rule_context: List, relevant_context: List) -> Dict[str, Any]:
        """Use AI to evaluate rule with context"""
        
        # Special handling for Rule 7 - database search
        if rule_number == 7:
            return self.evaluate_rule_7_database_search(label_data)
        
        # Special handling for Rule 11 - bilingual requirements
        if rule_number == 11:
            return self.evaluate_rule_11_bilingual_requirements(label_data, rule_context, relevant_context)
        
        # Build context for AI
        context_text = "COMPLIANCE CONTEXT:\n\n"
        
        # Add rule-specific context
        if rule_context:
            context_text += f"RULE {rule_number} CONTEXT:\n"
            for ctx in rule_context:
                context_text += f"- {ctx['title']}: {ctx['concise_summary']}\n"
        
        # Add semantically relevant context
        if relevant_context:
            context_text += "\nRELATED GUIDANCE:\n"
            for ctx in relevant_context:
                context_text += f"- {ctx['title']}: {ctx['concise_summary']}\n"
        
        system_prompt = """You are an expert CFIA food labelling compliance auditor.

You MUST respond with ONLY a valid JSON object. No additional text, explanations, or markdown formatting.

Return exactly this JSON structure:
{
    "compliant": true,
    "confidence": 0.95,
    "finding": "Detailed compliance finding",
    "reasoning": "Step-by-step evaluation reasoning",
    "recommendations": ["Specific recommendations if non-compliant"],
    "regulatory_references": ["SFCR/FDR sections mentioned"],
    "missing_information": ["Any required info not found in label data"]
}"""
        
        user_prompt = f"""Evaluate Rule {rule_number} compliance. Respond with ONLY valid JSON:

RULE {rule_number} DESCRIPTION:
{self.get_rule_description(rule_number)}

LABEL DATA:
{json.dumps(label_data, indent=2)}

{context_text}

Return only the JSON evaluation object with no additional text."""
        
        try:
            print(f"      Evaluating rule {rule_number}...")
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use mini for better reliability
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=1500
            )
            
            response_content = response.choices[0].message.content.strip()
            print(f"      Response length: {len(response_content)} chars")
            
            # Clean response - remove any markdown formatting
            if response_content.startswith('```json'):
                response_content = response_content.replace('```json', '').replace('```', '').strip()
            elif response_content.startswith('```'):
                response_content = response_content.replace('```', '').strip()
            
            # Try to parse JSON
            result = json.loads(response_content)
            result['rule_number'] = rule_number
            result['context_used'] = len(rule_context) + len(relevant_context)
            
            print(f"      ✓ Rule {rule_number}: {result.get('compliant', 'unknown')}")
            return result
            
        except json.JSONDecodeError as e:
            print(f"      ✗ JSON parsing error for rule {rule_number}: {str(e)}")
            print(f"      Response preview: {response_content[:200]}...")
            
            # Try to fix common JSON issues
            try:
                # Remove any text before first {
                start_idx = response_content.find('{')
                end_idx = response_content.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    cleaned_content = response_content[start_idx:end_idx]
                    result = json.loads(cleaned_content)
                    result['rule_number'] = rule_number
                    result['context_used'] = len(rule_context) + len(relevant_context)
                    print(f"      ✓ Rule {rule_number}: parsed after cleanup")
                    return result
                else:
                    raise ValueError("No valid JSON structure found")
                    
            except Exception as e2:
                print(f"      ✗ JSON cleanup failed for rule {rule_number}: {str(e2)}")
                return self.create_fallback_rule_evaluation(rule_number, str(e))
            
        except Exception as e:
            print(f"      ✗ AI evaluation error for rule {rule_number}: {str(e)}")
            return self.create_fallback_rule_evaluation(rule_number, str(e))
    
    def evaluate_rule_7_database_search(self, label_data: Dict) -> Dict[str, Any]:
        """Special evaluation for Rule 7 - search Canadian Food Compositional Standards and Canadian Standards Identity Volume databases"""
        
        print(f"      Evaluating rule 7 with database search...")
        
        common_name = label_data.get('common_name', '')
        
        # Perform database search
        search_results = self.search_common_name_in_standards(common_name)
        
        if not search_results['search_performed']:
            return {
                "compliant": None,
                "confidence": 0.0,
                "finding": f"Database search failed: {search_results.get('error', 'Unknown error')}",
                "reasoning": "Unable to search Canadian Food Compositional Standards and Canadian Standards Identity Volume databases",
                "recommendations": ["Verify database connectivity", "Perform manual standards check"],
                "regulatory_references": ["Canadian Food Compositional Standards", "Canadian Standards Identity Volume"],
                "missing_information": ["Database search results"],
                "rule_number": 7,
                "database_search_results": search_results
            }
        
        # Determine compliance based on search results
        found_any = search_results['found_in_cfcs'] or search_results['found_in_csiv']
        total_matches = search_results['total_matches']
        
        if found_any:
            # Found in standards - compliant
            sources = []
            if search_results['found_in_cfcs']:
                sources.append(f"Canadian Food Compositional Standards ({len(search_results['cfcs_matches'])} matches)")
            if search_results['found_in_csiv']:
                sources.append(f"Canadian Standards Identity Volume ({len(search_results['csiv_matches'])} matches)")
            
            confidence = min(0.95, 0.7 + (total_matches * 0.05))  # Higher confidence with more matches
            
            finding = f"Common name '{common_name}' found in Canadian standards: {', '.join(sources)}"
            reasoning = f"Database search found {total_matches} matching entries in official standards databases"
            
            result = {
                "compliant": True,
                "confidence": confidence,
                "finding": finding,
                "reasoning": reasoning,
                "recommendations": [],
                "regulatory_references": sources,
                "missing_information": []
            }
        else:
            # Not found in standards
            confidence = 0.8  # High confidence that it's not in standards
            
            finding = f"Common name '{common_name}' not found in Canadian Food Compositional Standards or Canadian Standards Identity Documents"
            reasoning = "Database search completed but no matching entries found in official Canadian food standards"
            
            result = {
                "compliant": False,
                "confidence": confidence,
                "finding": finding,
                "reasoning": reasoning,
                "recommendations": [
                    "Verify if this is a generic descriptive name",
                    "Check if product falls under a different standardized category",
                    "Consider using a standardized common name if available"
                ],
                "regulatory_references": ["Canadian Food Compositional Standards", "Canadian Standards Identity Documents"],
                "missing_information": []
            }
        
        # Add database search details
        result.update({
            "rule_number": 7,
            "database_search_results": search_results,
            "search_term": common_name
        })
        
        print(f"      ✓ Rule 7: {result['compliant']} (found {total_matches} matches)")
        return result
    
    def evaluate_rule_11_bilingual_requirements(self, label_data: Dict, rule_context: List, relevant_context: List) -> Dict[str, Any]:
        """Special evaluation for Rule 11 - bilingual labelling requirements using embeddings"""
        
        print(f"      Evaluating rule 11 with bilingual requirements analysis...")
        
        common_name = label_data.get('common_name', '')
        bilingual_compliance = label_data.get('bilingual_compliance', 'unknown')
        
        # Search for bilingual-specific context using embeddings
        bilingual_query = f"bilingual labelling requirements common name {common_name} French English"
        bilingual_context = self.search_relevant_context(bilingual_query, rule_number=None, top_k=5)
        
        # Combine all context
        all_context = rule_context + relevant_context + bilingual_context
        
        # Build detailed context text
        context_text = "BILINGUAL LABELLING COMPLIANCE CONTEXT:\n\n"
        
        if all_context:
            context_text += "RELEVANT BILINGUAL REQUIREMENTS:\n"
            for ctx in all_context:
                if any(keyword in ctx.get('compliance_keywords', '').lower() for keyword in ['bilingual', 'french', 'english', 'langue']):
                    context_text += f"- {ctx['title']}: {ctx['concise_summary']}\n"
        
        # Extract French/English indicators from label data
        french_indicators = self.detect_french_text(label_data)
        english_indicators = self.detect_english_text(label_data)
        
        context_text += f"\nDETECTED LANGUAGE ELEMENTS:\n"
        context_text += f"- French indicators: {french_indicators}\n"
        context_text += f"- English indicators: {english_indicators}\n"
        context_text += f"- Bilingual compliance reported: {bilingual_compliance}\n"
        
        system_prompt = """You are an expert CFIA bilingual labelling compliance auditor.

You MUST respond with ONLY a valid JSON object. No additional text, explanations, or markdown formatting.

Evaluate bilingual labelling compliance for common names based on Canadian food labelling regulations.

Return exactly this JSON structure:
{
    "compliant": true,
    "confidence": 0.95,
    "finding": "Detailed bilingual compliance finding",
    "reasoning": "Step-by-step bilingual evaluation reasoning",
    "recommendations": ["Specific recommendations if non-compliant"],
    "regulatory_references": ["Specific bilingual regulation sections"],
    "missing_information": ["Any required bilingual info not found"],
    "bilingual_analysis": {
        "french_present": true,
        "english_present": true,
        "equal_prominence": true,
        "exemption_applicable": false
    }
}"""
        
        user_prompt = f"""Evaluate Rule 11 - Bilingual labelling compliance for common name. Respond with ONLY valid JSON:

COMMON NAME: {common_name}
PRODUCT TYPE: {label_data.get('product_type', 'unknown')}

{context_text}

BILINGUAL REQUIREMENT EVALUATION:
- Does the common name appear in both official languages (English and French)?
- Are both language versions given equal prominence?
- Are there any exemptions that apply to this product type?
- Does the labelling meet CFIA bilingual requirements?

Return only the JSON evaluation object with no additional text."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=1800
            )
            
            response_content = response.choices[0].message.content.strip()
            
            # Clean response - remove any markdown formatting
            if response_content.startswith('```json'):
                response_content = response_content.replace('```json', '').replace('```', '').strip()
            elif response_content.startswith('```'):
                response_content = response_content.replace('```', '').strip()
            
            # Try to parse JSON
            result = json.loads(response_content)
            result['rule_number'] = 11
            result['context_used'] = len(all_context)
            result['evaluation_method'] = 'embeddings_enhanced_bilingual'
            
            print(f"      ✓ Rule 11: {result.get('compliant', 'unknown')} (bilingual compliance)")
            return result
            
        except json.JSONDecodeError as e:
            print(f"      ✗ JSON parsing error for rule 11: {str(e)}")
            return self.create_fallback_bilingual_evaluation(label_data, str(e))
            
        except Exception as e:
            print(f"      ✗ AI evaluation error for rule 11: {str(e)}")
            return self.create_fallback_bilingual_evaluation(label_data, str(e))
    
    def detect_french_text(self, label_data: Dict) -> List[str]:
        """Detect French text indicators in label data"""
        
        french_indicators = []
        
        # Common French words/phrases in food labelling
        french_keywords = [
            'ingrédients', 'nutrition', 'valeur nutritive', 'calories', 'glucides',
            'protéines', 'lipides', 'sodium', 'sucres', 'fibres', 'gras',
            'saturés', 'trans', 'cholestérol', 'vitamine', 'calcium',
            'fer', 'ml', 'grammes', 'sans', 'avec', 'naturel', 'biologique'
        ]
        
        # Check all text fields for French indicators
        all_text = ""
        for key, value in label_data.items():
            if isinstance(value, str):
                all_text += f" {value.lower()}"
        
        for keyword in french_keywords:
            if keyword in all_text:
                french_indicators.append(keyword)
        
        return french_indicators
    
    def detect_english_text(self, label_data: Dict) -> List[str]:
        """Detect English text indicators in label data"""
        
        english_indicators = []
        
        # Common English words in food labelling
        english_keywords = [
            'ingredients', 'nutrition', 'facts', 'calories', 'carbohydrate',
            'protein', 'fat', 'sodium', 'sugars', 'fiber', 'saturated',
            'trans', 'cholesterol', 'vitamin', 'calcium', 'iron',
            'natural', 'organic', 'contains', 'may contain'
        ]
        
        # Check all text fields for English indicators
        all_text = ""
        for key, value in label_data.items():
            if isinstance(value, str):
                all_text += f" {value.lower()}"
        
        for keyword in english_keywords:
            if keyword in all_text:
                english_indicators.append(keyword)
        
        return english_indicators
    
    def create_fallback_bilingual_evaluation(self, label_data: Dict, error_msg: str) -> Dict[str, Any]:
        """Create fallback evaluation for bilingual requirements when AI fails"""
        
        # Basic bilingual compliance check
        bilingual_compliance = label_data.get('bilingual_compliance', 'unknown')
        
        if bilingual_compliance == 'true' or bilingual_compliance is True:
            compliant = True
            confidence = 0.7
            finding = "Basic bilingual compliance detected in label data"
        elif bilingual_compliance == 'false' or bilingual_compliance is False:
            compliant = False
            confidence = 0.7
            finding = "No bilingual compliance detected in label data"
        else:
            compliant = None
            confidence = 0.0
            finding = "Unable to determine bilingual compliance"
        
        return {
            "compliant": compliant,
            "confidence": confidence,
            "finding": finding,
            "reasoning": f"Fallback evaluation due to AI error: {error_msg}",
            "recommendations": ["Manual bilingual compliance review required"],
            "regulatory_references": ["SFCR Bilingual Labelling Requirements"],
            "missing_information": ["Detailed bilingual analysis due to technical error"],
            "rule_number": 11,
            "error": error_msg,
            "evaluation_method": "fallback_bilingual",
            "bilingual_analysis": {
                "french_present": bilingual_compliance in ['true', True],
                "english_present": True,  # Assume English is present
                "equal_prominence": "unknown",
                "exemption_applicable": "unknown"
            }
        }
    
    def evaluate_bilingual_requirements(self, label_data: Dict) -> Dict[str, Any]:
        """Evaluate bilingual requirements using dedicated bilingual rules module"""
        
        print(f"\nEvaluating bilingual requirements...")
        
        try:
            # Import bilingual rules module
            from bilingual_rules import evaluate_all_bilingual_rules
            
            # Run bilingual evaluation
            bilingual_results = evaluate_all_bilingual_rules(label_data, self.client)
            
            # Convert to standard rule format
            rule_evaluations = {}
            
            for key, result in bilingual_results.items():
                if key == 'bilingual_overall':
                    continue  # Skip summary
                
                rule_num = result.get('rule_number', 0)
                status = "✓" if result.get('compliant') else "✗"
                confidence = result.get('confidence', 0.0)
                print(f"  {status} Bilingual Rule {rule_num}: {result.get('finding', 'No finding')[:60]}... (confidence: {confidence:.2f})")
                
                rule_evaluations[f"bilingual_rule_{rule_num}"] = result
            
            return rule_evaluations
            
        except ImportError as e:
            print(f"  ✗ Bilingual rules module not available: {e}")
            return {}
            
        except Exception as e:
            print(f"  ✗ Bilingual evaluation error: {e}")
            return {
                "bilingual_rule_1": {
                    "compliant": None,
                    "confidence": 0.0,
                    "finding": f"Bilingual evaluation failed: {str(e)}",
                    "error": str(e)
                }
            }
    
    def create_fallback_rule_evaluation(self, rule_number: int, error_msg: str) -> Dict[str, Any]:
        """Create fallback evaluation when AI fails"""
        
        return {
            "compliant": None,
            "confidence": 0.0,
            "finding": f"Evaluation failed due to technical error: {error_msg}",
            "reasoning": "AI evaluation failed due to JSON parsing issues",
            "recommendations": ["Manual review required", "Re-run evaluation after fixing technical issues"],
            "regulatory_references": [],
            "missing_information": ["Complete evaluation due to technical error"],
            "rule_number": rule_number,
            "error": error_msg,
            "evaluation_method": "fallback"
        }
    
    def create_fallback_rule_evaluation(self, rule_number: int, error_msg: str) -> Dict[str, Any]:
        """Create fallback evaluation when AI fails"""
        
        return {
            "compliant": None,
            "confidence": 0.0,
            "finding": f"Evaluation failed due to technical error: {error_msg}",
            "reasoning": "AI evaluation failed due to JSON parsing issues",
            "recommendations": ["Manual review required", "Re-run evaluation after fixing technical issues"],
            "regulatory_references": [],
            "missing_information": ["Complete evaluation due to technical error"],
            "rule_number": rule_number,
            "error": error_msg,
            "evaluation_method": "fallback"
        }
    
    def get_rule_description(self, rule_number: int) -> str:
        """Get rule description from rule methods"""
        
        rule_descriptions = {
            1: "Is a common name present?",
            2: "If not, is the product exempt from common name?",
            3: "Is the common name on the principal display panel (PDP)?",
            4: "Is the common name in letters of 1.6 mm or greater?",
            5: "If PDS <= 10 cm2, is common name shown in characters >= 0.8 mm?",
            6: "Is it an appropriate common name?",
            7: "Is the common name found in Canadian Food Compositional Standards or Canadian Standards Identity Volume databases?",
            8: "Is it prescribed by any other regulation?",
            9: "Is it the name by which food is generally known or descriptive name?",
            10: "If food could be mistaken, does common name describe true nature?",
            11: "Does the common name meet bilingual labelling requirements?"
        }
        
        return rule_descriptions.get(rule_number, f"Rule {rule_number} description not available")
    
    def search_common_name_in_standards(self, common_name: str) -> Dict[str, Any]:
        """Search for common name in Canadian Food Compositional Standards and Canadian Standards Identity Volume databases"""
        
        if not common_name:
            return {
                "found_in_cfcs": False,
                "found_in_csiv": False,
                "cfcs_matches": [],
                "csiv_matches": [],
                "search_performed": False,
                "error": "No common name provided"
            }
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Search in Canadian Food Compositional Standards table
            cfcs_matches = []
            cursor.execute("""
                SELECT common_name, definition, volume, tag 
                FROM cfcs_cname 
                WHERE LOWER(common_name) LIKE LOWER(?) 
                OR LOWER(?) LIKE LOWER(common_name)
            """, (f"%{common_name}%", f"%{common_name}%"))
            
            cfcs_results = cursor.fetchall()
            for result in cfcs_results:
                cfcs_matches.append({
                    "common_name": result[0],
                    "definition": result[1],
                    "volume": result[2],
                    "tag": result[3]
                })
            
            # Search in Canadian Standards Identity Volume table
            csiv_matches = []
            cursor.execute("""
                SELECT common_name, definition, volume_number, volume_title, section
                FROM csiv_cname 
                WHERE LOWER(common_name) LIKE LOWER(?) 
                OR LOWER(?) LIKE LOWER(common_name)
            """, (f"%{common_name}%", f"%{common_name}%"))
            
            csiv_results = cursor.fetchall()
            for result in csiv_results:
                csiv_matches.append({
                    "common_name": result[0],
                    "definition": result[1],
                    "volume_number": result[2],
                    "volume_title": result[3],
                    "section": result[4]
                })
            
            conn.close()
            
            return {
                "found_in_cfcs": len(cfcs_matches) > 0,
                "found_in_csiv": len(csiv_matches) > 0,
                "cfcs_matches": cfcs_matches,
                "csiv_matches": csiv_matches,
                "search_performed": True,
                "total_matches": len(cfcs_matches) + len(csiv_matches)
            }
            
        except Exception as e:
            print(f"      Database search error: {str(e)}")
            return {
                "found_in_cfcs": False,
                "found_in_csiv": False,
                "cfcs_matches": [],
                "csiv_matches": [],
                "search_performed": False,
                "error": str(e)
            }
    
    def calculate_overall_compliance(self, rule_evaluations: Dict) -> Dict[str, Any]:
        """Calculate overall compliance summary"""
        
        total_rules = len(rule_evaluations)
        compliant_rules = sum(1 for eval_result in rule_evaluations.values() 
                            if eval_result.get('compliant') is True)
        non_compliant_rules = sum(1 for eval_result in rule_evaluations.values() 
                                if eval_result.get('compliant') is False)
        error_rules = sum(1 for eval_result in rule_evaluations.values() 
                        if eval_result.get('compliant') is None)
        
        compliance_rate = compliant_rules / total_rules if total_rules > 0 else 0.0
        
        # Determine overall status
        if compliance_rate >= 0.9:
            status = "COMPLIANT"
        elif compliance_rate >= 0.7:
            status = "MOSTLY_COMPLIANT"
        elif compliance_rate >= 0.5:
            status = "PARTIALLY_COMPLIANT"
        else:
            status = "NON_COMPLIANT"
        
        return {
            "status": status,
            "compliance_rate": compliance_rate,
            "total_rules": total_rules,
            "compliant_rules": compliant_rules,
            "non_compliant_rules": non_compliant_rules,
            "error_rules": error_rules,
            "summary": f"{compliant_rules}/{total_rules} rules compliant ({compliance_rate:.1%})"
        }
    
    def identify_critical_issues(self, rule_evaluations: Dict) -> List[str]:
        """Identify critical compliance issues"""
        
        critical_issues = []
        
        # Critical rules that must be compliant
        critical_rule_numbers = [1, 3, 4, 6, 11]  # Common name presence, PDP location, size, appropriateness, bilingual
        
        for rule_num in critical_rule_numbers:
            rule_key = f"rule_{rule_num}"
            if rule_key in rule_evaluations:
                evaluation = rule_evaluations[rule_key]
                if evaluation.get('compliant') is False:
                    issue = f"CRITICAL: Rule {rule_num} - {evaluation.get('finding', 'Non-compliant')}"
                    critical_issues.append(issue)
        
        return critical_issues


def evaluate_product_images(image_paths: List[str], product_info: Dict = None,
                          api_key: str = config.OPENAI_API_KEY, 
                          google_credentials: str = None) -> Dict[str, Any]:
    """Main function to evaluate product images against common name rules"""
    
    print(f"Multi-Image Label Evaluator")
    print("=" * 50)
    
    # Initialize evaluator
    evaluator = MultiImageLabelEvaluator(
        api_key=api_key,
        google_credentials_path='google-credentials.json'
    )
    
    # Process images and evaluate
    results = evaluator.process_product_images(image_paths, product_info)
    
    return results


def save_evaluation_report(results: Dict, output_file: str = None):
    """Save evaluation report to JSON file"""
    
    if output_file is None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_file = f"label_evaluation_report_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Evaluation report saved: {output_file}")
    return output_file


if __name__ == "__main__":
    print("\nMulti-Image Label Evaluator")
    print("=" * 50)
    print("System ready! Use evaluate_product_images() to process your product images.")
    print("\nExample usage:")
    print("""
    results = evaluate_product_images([
        "product_front.jpg",
        "product_back.jpg", 
        "product_top.jpg"
    ], {
        "product_name": "Test Product",
        "category": "dairy"
    })
    
    save_evaluation_report(results)
    """)