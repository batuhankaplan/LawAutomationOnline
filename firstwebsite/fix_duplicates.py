#!/usr/bin/env python3
"""
Safely remove duplicate code blocks from app.py
"""

def fix_app_duplicates():
    with open('firstwebsite/app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Original file: {len(lines)} lines")
    
    # Find all Flask app definitions
    app_defs = []
    perm_defs = []
    admin_defs = []
    
    for i, line in enumerate(lines):
        if line.strip() == 'app = Flask(__name__, static_url_path=\'/static\')':
            app_defs.append(i)
        elif line.strip() == 'def permission_required(permission):':
            perm_defs.append(i)
        elif line.strip() == '# --- Flask-Admin Setup ---':
            admin_defs.append(i)
    
    print(f"Found {len(app_defs)} Flask app definitions at lines: {app_defs}")
    print(f"Found {len(perm_defs)} permission_required definitions at lines: {perm_defs}")
    print(f"Found {len(admin_defs)} Flask-Admin setup comments at lines: {admin_defs}")
    
    if len(app_defs) != 4:
        print(f"ERROR: Expected 4 app definitions, found {len(app_defs)}")
        return False
    
    # Keep only:
    # 1. Lines 0 to first permission_required (imports and helpers)
    # 2. First permission_required definition (lines 131-200)
    # 3. Last Flask app definition onwards (from line 3875)
    
    cleaned_lines = []
    
    # Part 1: Keep imports and helper functions (lines 0-130)
    cleaned_lines.extend(lines[0:131])
    
    # Part 2: Keep first permission_required function (lines 131-200)
    cleaned_lines.extend(lines[131:200])
    
    # Part 3: Keep from last Flask app definition (line 3875) to end
    cleaned_lines.extend(lines[3875:])
    
    # Write cleaned file
    output_file = 'firstwebsite/app_fixed.py'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)
    
    print(f"\nCleaned file written to: {output_file}")
    print(f"New file: {len(cleaned_lines)} lines")
    print(f"Removed: {len(lines) - len(cleaned_lines)} duplicate lines")
    
    return True

if __name__ == '__main__':
    success = fix_app_duplicates()
    if success:
        print("\n✓ Duplicate removal completed successfully!")
        print("Next steps:")
        print("1. Review app_fixed.py")
        print("2. Test the application")
        print("3. If everything works, replace app.py with app_fixed.py")
    else:
        print("\n✗ Duplicate removal failed!")
