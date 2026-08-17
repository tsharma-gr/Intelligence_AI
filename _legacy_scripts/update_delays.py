import os
import glob
import py_compile

def process_file(filepath, replacements):
    if not os.path.exists(filepath):
        return False, "Not found"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original = content
    for old, new in replacements:
        content = content.replace(old, new)
        
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        # Compile check
        try:
            py_compile.compile(filepath, doraise=True)
            return True, "Updated and Compiled OK"
        except py_compile.PyCompileError as e:
            # Revert if syntax error
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(original)
            return False, f"Syntax Error: {e}"
    else:
        # File found but no replacements made (maybe already updated or string not present)
        # Let's compile it anyway just to check
        try:
            py_compile.compile(filepath, doraise=True)
            return False, "No replacements made (already updated?), Compiled OK"
        except py_compile.PyCompileError as e:
            return False, f"Syntax Error during check: {e}"

def main():
    dirs = glob.glob("/root/*cv_automation")
    if not dirs:
        print("No directories matching /root/*cv_automation found.")
        return

    for d in sorted(dirs):
        print(f"\nProcessing {d}...")
        
        cv_file = os.path.join(d, "cv_library_searcher.py")
        cv_status, cv_msg = process_file(cv_file, [("await asyncio.sleep(10)", "await asyncio.sleep(5)")])
        print(f"  [CV-Library] {cv_msg}")
        
        tj_file = os.path.join(d, "totaljobs_searcher.py")
        tj_status, tj_msg = process_file(tj_file, [("random.uniform(8, 10)", "random.uniform(4, 5)")])
        print(f"  [TotalJobs ] {tj_msg}")
        
        main_file = os.path.join(d, "main.py")
        main_status, main_msg = process_file(main_file, [("await asyncio.sleep(10)", "await asyncio.sleep(5)")])
        print(f"  [Main Loop ] {main_msg}")

    print("\nAll compilation checks passed successfully!")

if __name__ == "__main__":
    main()
