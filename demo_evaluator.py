"""
Example usage and test script for the Multi-Image Label Evaluator
"""

import os, config
from pathlib import Path
from multi_image_evaluator import evaluate_product_images, save_evaluation_report

def demo_multi_image_evaluation():
    """Demo function showing how to use the multi-image evaluator"""
    
    print("Multi-Image Label Evaluator Demo")
    print("=" * 50)
    
    # Example 1: Evaluate multiple product images
    print("\n1. EXAMPLE: Multiple Product Images")
    print("-" * 30)
    
    # Sample image paths (you would replace these with actual image files)
    # sample_images = [
    #     "examples/milk_front.jpg",       # Principal display panel
    #     "examples/milk_back.jpg",        # Ingredients and nutrition
    #     "examples/milk_side.jpg",        # Side panel info
    #     "examples/milk_top.jpg"          # Top view
    # ]
    
    sample_images = [
        "sample_images/example1/Stanley_Hum_coconut_front.png",       # Principal display panel
        "sample_images/example1/Stanley_Hum_BACK.png",        # Ingredients and nutrition      
    ]

    # Product information (optional context)
    product_info = {
        "product_name": "Granola Bar"
    }
    #     "brand": "Example Dairy",
    #     "category": "dairy",
    #     "expected_volume": "1L",
    #     "package_type": "carton"
    # }
    
    print(f"Processing {len(sample_images)} images...")
    print("Images to process:")
    for i, img in enumerate(sample_images, 1):
        print(f"  {i}. {Path(img).name}")
    
    # Check if any images exist (for demo)
    existing_images = [img for img in sample_images if Path(img).exists()]
    
    if existing_images:
        print(f"\nFound {len(existing_images)} existing images, processing...")
        
        try:
            # Evaluate the product images
            results = evaluate_product_images(
                image_paths=existing_images,
                product_info=product_info,
                api_key=config.OPENAI_API_KEY,  # Replace with your key
                google_credentials="google-credentials.json"  # Replace with your credentials
            )
            
            # Save the evaluation report
            report_file = save_evaluation_report(results, "demo_evaluation_report.json")
            
            # Display summary
            print_evaluation_summary(results)
            
        except Exception as e:
            print(f"Error during evaluation: {str(e)}")
            print("Make sure you have:")
            print("1. Valid OpenAI API key")
            print("2. Google Cloud Vision API credentials")
            print("3. Required Python packages installed")
    
    else:
        print("\nNo sample images found. Here's what the system would do:")
        print("\n📸 IMAGE PROCESSING:")
        print("  ✓ OCR each image using Google Vision API")
        print("  ✓ Extract text with bounding boxes")
        print("  ✓ Identify image types (front, back, side, etc.)")
        print("  ✓ Support multiple languages (EN, FR, KO, ZH, PL)")
        
        print("\n🤖 AI ANALYSIS:")
        print("  ✓ Extract structured label data using GPT-4")
        print("  ✓ Identify common name, location, text size")
        print("  ✓ Find product type, claims, bilingual compliance")
        print("  ✓ Combine information from all image views")
        
        print("\n📋 RULE EVALUATION:")
        print("  ✓ Evaluate against all 10 common name rules")
        print("  ✓ Use semantic search for relevant compliance context")
        print("  ✓ Provide detailed findings with confidence scores")
        print("  ✓ Generate compliance recommendations")
        
        print("\n📊 REPORTING:")
        print("  ✓ Overall compliance status and percentage")
        print("  ✓ Critical issues identification")
        print("  ✓ Rule-by-rule detailed evaluation")
        print("  ✓ JSON report with all findings")

def print_evaluation_summary(results):
    """Print a summary of evaluation results"""
    
    print(f"\n{'='*60}")
    print("EVALUATION RESULTS SUMMARY")
    print(f"{'='*60}")
    
    # Overall compliance
    overall = results.get('overall_compliance', {})
    print(f"\n📊 OVERALL COMPLIANCE:")
    print(f"  Status: {overall.get('status', 'UNKNOWN')}")
    print(f"  Summary: {overall.get('summary', 'No summary available')}")
    
    # OCR summary
    label_data = results.get('extracted_label_data', {})
    ocr_meta = label_data.get('ocr_metadata', {})
    
    print(f"\n📸 OCR PROCESSING:")
    print(f"  Images processed: {results.get('images_processed', 0)}")
    print(f"  Image types: {', '.join(ocr_meta.get('image_types', []))}")
    print(f"  Total text extracted: {ocr_meta.get('total_text_chars', 0)} characters")
    
    # Label data extracted
    print(f"\n🏷️ EXTRACTED LABEL DATA:")
    print(f"  Common name: {label_data.get('common_name', 'Not found')}")
    print(f"  Common name location: {label_data.get('common_name_location', 'Unknown')}")
    print(f"  Product type: {label_data.get('product_type', 'Unknown')}")
    print(f"  Package size: {label_data.get('package_size_cm2', 'Unknown')} cm²")
    print(f"  Bilingual compliance: {label_data.get('bilingual_compliance', 'Unknown')}")
    
    # Critical issues
    critical_issues = results.get('critical_issues', [])
    if critical_issues:
        print(f"\n⚠️ CRITICAL ISSUES:")
        for issue in critical_issues:
            print(f"  - {issue}")
    else:
        print(f"\n✅ No critical issues found")
    
    # Rule breakdown
    rule_evaluations = results.get('rule_evaluations', {})
    print(f"\n📋 RULE EVALUATION BREAKDOWN:")
    
    for rule_key, evaluation in rule_evaluations.items():
        rule_num = rule_key.replace('rule_', '')
        compliant = evaluation.get('compliant')
        confidence = evaluation.get('confidence', 0.0)
        finding = evaluation.get('finding', 'No finding')
        
        if compliant is True:
            status = "✅ COMPLIANT"
        elif compliant is False:
            status = "❌ NON-COMPLIANT"
        else:
            status = "⚠️ ERROR"
        
        print(f"  Rule {rule_num}: {status} (confidence: {confidence:.2f})")
        print(f"           {finding}")

def setup_demo_environment():
    """Set up demo environment with sample images directory"""
    
    examples_dir = Path("C:\\Users\\kamal\\workspace\\projects\\experiment1\\sample_images\\example1")
    examples_dir.mkdir(exist_ok=True)
    
    print(f"Demo environment setup:")
    print(f"✓ Created examples directory: {examples_dir}")
    print(f"\nTo run the demo:")
    print(f"1. Add sample product images to {examples_dir}/")
    print(f"2. Name them: Stanley_Hum_coconut_front.png, Stanley_Hum_BACK.png, etc.")
    print(f"3. Set your API keys in the demo function")
    print(f"4. Run: python demo_evaluator.py")

if __name__ == "__main__":
    # Setup demo environment
    setup_demo_environment()
    
    # Run demo
    demo_multi_image_evaluation()
    
    print(f"\n{'='*60}")
    print("SYSTEM COMPONENTS READY!")
    # print(f"{'='*60}")
    # print("To use the system:")
    # print("1. First run: python create_embeddings_system.py")
    # print("2. Then use: python multi_image_evaluator.py")
    # print("3. Or run this demo with your images")
    # print("\nRequired packages:")
    # print("- google-cloud-vision")
    # print("- openai")
    # print("- scikit-learn")
    # print("- Install: pip install google-cloud-vision openai scikit-learn")