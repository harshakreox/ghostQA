import pandas as pd
import sys
import os
from datetime import datetime

try:
    from jinja2 import Environment, FileSystemLoader
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        f"Module 'jinja2' not found in Python interpreter {sys.executable}.\n"
        f"Install it with: {sys.executable} -m pip install jinja2"
    ) from e



def generate_html_report(excel_path):
    """
    Generates an HTML report from the given Excel results file.
    Embeds screenshots (if present in the Excel data).
    
    Args:
        excel_path: Path to Excel file with test results
        
    Returns:
        Path to generated HTML file
    """
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    # Read Excel file
    df = pd.read_excel(excel_path)
    df = df.where(pd.notna(df), None)
    
    # Expected columns in results Excel
    required_cols = ["TestName", "StepNo", "Action", "Description", "Status", "Error", "Timestamp"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column in Excel: {col}")

    # If screenshot column exists, use it
    if "Screenshot" not in df.columns:
        df["Screenshot"] = None

    # Setup paths
    report_dir = os.path.dirname(excel_path)
    screenshots_dir = os.path.join(report_dir, "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)

    # Update screenshot paths to be relative
    for idx, row in df.iterrows():
        if row["Screenshot"] and os.path.exists(row["Screenshot"]):
            screenshot_name = os.path.basename(row["Screenshot"])
            new_path = os.path.join(screenshots_dir, screenshot_name)
            
            # Copy screenshot if needed
            if os.path.abspath(row["Screenshot"]) != os.path.abspath(new_path):
                try:
                    import shutil
                    shutil.copy2(row["Screenshot"], new_path)
                except Exception as e:
                    print(f"Warning: Could not copy screenshot: {e}")
            
            df.at[idx, "Screenshot"] = os.path.relpath(new_path, report_dir)

    # Calculate summary statistics
    total_tests = df["TestName"].nunique()
    total_steps = len(df)
    passed = (df["Status"] == "PASS").sum()
    failed = (df["Status"] == "FAIL").sum()
    skipped = (df["Status"] == "SKIP").sum()

    # Group steps by test
    grouped = df.groupby("TestName")
    tests = []
    for test_name, group in grouped:
        test_status = "FAIL" if any(group["Status"] == "FAIL") else "PASS"
        tests.append({
            "name": test_name,
            "steps": group.to_dict(orient="records"),
            "status": test_status
        })

    # Load Jinja2 template
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("report_template.html")

    # Render HTML
    html_content = template.render(
        report_title="Automation Test Results",
        generation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_tests=total_tests,
        total_steps=total_steps,
        passed=passed,
        failed=failed,
        skipped=skipped,
        tests=tests
    )

    # Output path
    output_html = excel_path.replace(".xlsx", ".html")
    os.makedirs(os.path.dirname(output_html) or ".", exist_ok=True)

    # Write file
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[OK] HTML report generated at: {output_html}")
    return output_html