"""
Simple OCR using Google Vision API
Supports: English, French, Korean, Simplified Chinese, Polish
"""

import os
from google.cloud import vision
from pathlib import Path


class OCRProcessor:
    """Simple OCR processor using Google Vision API"""
    
    def __init__(self, credentials_path=None):
        """Initialize OCR processor with optional credentials path"""
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(credentials_path)
        
        self.client = vision.ImageAnnotatorClient()
    
    def extract_text(self, image_path, languages=None, include_boxes=False):
        """
        Extract text from image using OCR
        
        Args:
            image_path: Path to image file
            languages: List of language codes (optional)
                      ['en', 'fr', 'ko', 'zh-CN', 'pl']
            include_boxes: Return bounding box coordinates
        
        Returns:
            str or dict: Extracted text or structured data with boxes
        """
        try:
            # Read image file
            image_path = Path(image_path)
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            # Create image object
            image = vision.Image(content=content)
            
            # Set language hints if provided
            image_context = None
            if languages:
                image_context = vision.ImageContext(language_hints=languages)
            
            # Perform OCR
            response = self.client.text_detection(
                image=image,
                image_context=image_context
            )
            
            # Check for errors
            if response.error.message:
                raise Exception(f"OCR API error: {response.error.message}")
            
            # Extract text and boxes
            texts = response.text_annotations
            if not texts:
                return "" if not include_boxes else {"text": "", "blocks": []}
            
            if not include_boxes:
                return texts[0].description.strip()
            
            # Return structured data with bounding boxes
            result = {
                "text": texts[0].description.strip(),
                "blocks": []
            }
            
            # Process each text block (skip first one - it's the full text)
            for text_block in texts[1:]:
                vertices = text_block.bounding_poly.vertices
                bbox = {
                    "text": text_block.description,
                    "confidence": getattr(text_block, 'confidence', 0),
                    "bounding_box": {
                        "x1": vertices[0].x,
                        "y1": vertices[0].y,
                        "x2": vertices[2].x,
                        "y2": vertices[2].y,
                        "vertices": [(v.x, v.y) for v in vertices]
                    }
                }
                result["blocks"].append(bbox)
            
            return result
                
        except Exception as e:
            print(f"OCR error: {e}")
            return "" if not include_boxes else {"text": "", "blocks": []}


def ocr_image(image_path, output_file=None, languages=None, include_boxes=False):
    """
    Simple function to OCR an image
    
    Args:
        image_path: Path to image file
        output_file: Optional path to save extracted text
        languages: List of language codes ['en', 'fr', 'ko', 'zh-CN', 'pl']
        include_boxes: Return bounding box coordinates
    
    Returns:
        str or dict: Extracted text or structured data with boxes
    """
    # Default supported languages
    if languages is None:
        languages = ['en', 'fr', 'ko', 'zh-CN', 'pl']
    
    # Initialize OCR processor
    ocr = OCRProcessor()
    
    # Extract text
    print(f"Processing: {image_path}")
    result = ocr.extract_text(image_path, languages, include_boxes)
    
    if include_boxes:
        text = result.get("text", "")
        blocks = result.get("blocks", [])
        print(f"Extracted {len(text)} characters in {len(blocks)} text blocks")
    else:
        text = result
        print(f"Extracted {len(text)} characters")
    
    if text:
        # Save to file if specified
        if output_file:
            output_path = Path(output_file)
            if include_boxes:
                import json
                output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
            else:
                output_path.write_text(text, encoding='utf-8')
            print(f"Saved to: {output_file}")
        
        return result if include_boxes else text
    else:
        print("No text found in image")
        return {"text": "", "blocks": []} if include_boxes else ""


if __name__ == "__main__":
    # Example usage
    image_file = input("Enter image path: ").strip()
    include_boxes = input("Include bounding boxes? (y/n): ").strip().lower() == 'y'
    
    if image_file:
        # Extract text with multilingual support
        result = ocr_image(
            image_path=image_file,
            output_file="extracted_text.json" if include_boxes else "extracted_text.txt",
            languages=['en', 'fr', 'ko', 'zh-CN', 'pl'],
            include_boxes=include_boxes
        )
        
        # Display results
        if include_boxes and result.get("blocks"):
            print("\nExtracted Text with Bounding Boxes:")
            print("-" * 50)
            text = result["text"]
            print(f"Full Text: {text[:200]}..." if len(text) > 200 else text)
            print(f"\nFound {len(result['blocks'])} text blocks:")
            for i, block in enumerate(result["blocks"][:5]):  # Show first 5 blocks
                bbox = block["bounding_box"]
                print(f"  Block {i+1}: '{block['text']}' at ({bbox['x1']},{bbox['y1']})-({bbox['x2']},{bbox['y2']})")
        elif not include_boxes and result:
            print("\nExtracted Text Preview:")
            print("-" * 50)
            print(result[:200] + "..." if len(result) > 200 else result)
    else:
        print("No image path provided")