import json
import os

def sanitize_folder_name(name):
    return name.replace(' ', '_').replace('/', '_').replace('\\', '_')

def create_section_files(json_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    output_dir = "food_labelling_requirements_checklist"
    os.makedirs(output_dir, exist_ok=True)
    
    sections = data.get('sections', [])
    
    for section in sections:
        section_title = section.get('title', 'untitled')
        folder_name = sanitize_folder_name(section_title)
        
        section_folder = os.path.join(output_dir, folder_name)
        os.makedirs(section_folder, exist_ok=True)
        
        output_file = os.path.join(section_folder, f"{folder_name}.json")
        
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(section, file, indent=2, ensure_ascii=False)
        
        print(f"Created: {output_file}")

if __name__ == "__main__":
    create_section_files(os.path.join("food_labelling_requirements_checklist", "cfia_rules.json"))