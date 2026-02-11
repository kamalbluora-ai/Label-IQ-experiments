import subprocess
import sys

def run_script(script_name):
    try:
        print(f"Running {script_name}...")
        result = subprocess.run([sys.executable, script_name], check=True, capture_output=True, text=True)
        print(f"{script_name} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}")
        print(f"Error: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False

def main():
    print("Starting CFIA Rules Processing Pipeline")
    print("=" * 40)
    
    scripts = [
        "requirements_checklist_parser.py",
        "split_rules_by_sections.py",
        "industry_labelling_tool_parser.py",
        "parse_industry_labelling_tool_json.py"
    ]
    
    for script in scripts:
        success = run_script(script)
        if not success:
            print(f"Pipeline failed at {script}")
            sys.exit(1)
    
    print("=" * 40)
    print("Pipeline completed successfully!")

if __name__ == "__main__":
    main()