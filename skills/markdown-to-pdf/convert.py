#!/usr/bin/env python3
import sys
import os
import markdown
from playwright.sync_api import sync_playwright

def parse_and_enhance_resume(md_content):
    # Split content by line
    lines = md_content.strip().split('\n')
    
    if len(lines) < 2:
        # Fallback if file is too short
        return markdown.markdown(md_content)
        
    name = lines[0].strip()
    title = lines[1].strip()
    
    # Locate intro paragraph
    intro = ""
    start_idx = 2
    for i in range(2, len(lines)):
        if lines[i].strip() and not lines[i].strip().startswith('*') and len(lines[i].strip()) > 50:
            intro = lines[i].strip()
            start_idx = i + 1
            break
            
    rest = lines[start_idx:]
    
    # Group lines into sections dynamically
    current_section = None
    sections_data = {
        'experience': [],
        'education': [],
        'achievements': []
    }
    
    for line in rest:
        stripped = line.strip()
        if not stripped:
            if current_section:
                sections_data[current_section].append(line)
            continue
            
        if 'experience' in stripped.lower():
            current_section = 'experience'
            continue
        elif 'education' in stripped.lower():
            current_section = 'education'
            continue
        elif 'achievement' in stripped.lower() or 'publication' in stripped.lower():
            current_section = 'achievements'
            continue
            
        if current_section:
            sections_data[current_section].append(line)
            
    # Process Experience Section
    exp_html_parts = []
    exp_lines = sections_data['experience']
    current_job_entry = []
    
    for line in exp_lines:
        stripped = line.strip()
        if not stripped:
            continue
            
        # Check if it's a company name (not a bullet, not containing a pipe)
        is_company = not stripped.startswith('*') and not stripped.startswith('#') and '|' not in stripped
        
        if is_company:
            # Save the previous job entry if any exists
            if current_job_entry:
                exp_html_parts.append(current_job_entry)
                current_job_entry = []
            current_job_entry.append(f"### {stripped}")
        elif '|' in stripped and not stripped.startswith('*'):
            # Role and Date line
            parts = stripped.split('|')
            role = parts[0].strip()
            date = parts[1].strip()
            current_job_entry.append(f'<div class="job-role-line"><span class="job-role">{role}</span><span class="job-date">{date}</span></div>')
        else:
            current_job_entry.append(line)
            
    if current_job_entry:
        exp_html_parts.append(current_job_entry)
        
    # Wrap each job entry in a div that prevents internal page breaks
    exp_html = ""
    for entry in exp_html_parts:
        entry_md = "\n".join(entry)
        entry_html = markdown.markdown(entry_md, extensions=['extra'])
        exp_html += f'<div class="job-entry">\n{entry_html}\n</div>\n'
        
    # Process Education Section
    edu_lines = []
    for line in sections_data['education']:
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith('*') and not stripped.startswith('#') and ('–' in stripped or '-' in stripped):
            edu_lines.append(f'* {stripped}')
        else:
            edu_lines.append(line)
            
    edu_md = "\n".join(edu_lines)
    edu_html = markdown.markdown(edu_md, extensions=['extra'])
    
    # Process Achievements Section
    ach_lines = []
    for line in sections_data['achievements']:
        stripped = line.strip()
        if not stripped:
            continue
        ach_lines.append(line)
        
    ach_md = "\n".join(ach_lines)
    ach_html = markdown.markdown(ach_md, extensions=['extra'])
    
    # Build clean modular HTML sections
    exp_section_html = ""
    if exp_html:
        exp_section_html = f"""
    <div class="resume-section">
        <h2>Experience</h2>
        {exp_html}
    </div>"""

    edu_section_html = ""
    if sections_data['education']:
        edu_section_html = f"""
    <div class="resume-section avoid-break">
        <h2>Education & Post Research</h2>
        {edu_html}
    </div>"""
    
    ach_section_html = ""
    if sections_data['achievements']:
        ach_section_html = f"""
    <div class="resume-section avoid-break">
        <h2>Achievements & Publications</h2>
        {ach_html}
    </div>"""
    
    # Beautiful CSS Styling tailored for professional resumes
    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{name} - Resume</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #2d3748;
            line-height: 1.45;
            margin: 0;
            padding: 10px;
            font-size: 12.5px;
        }}
        .header {{
            text-align: center;
            border-bottom: 2.5px solid #2b6cb0;
            padding-bottom: 12px;
            margin-bottom: 16px;
        }}
        .header h1 {{
            font-size: 26px;
            font-weight: 700;
            margin: 0 0 4px 0;
            color: #1a365d;
            letter-spacing: -0.5px;
        }}
        .header .title {{
            font-size: 14.5px;
            font-weight: 500;
            color: #4a5568;
            margin: 0;
            letter-spacing: 0.2px;
        }}
        .intro-p {{
            font-size: 12.5px;
            color: #4a5568;
            margin-bottom: 16px;
            text-align: justify;
        }}
        h2 {{
            font-size: 14px;
            font-weight: 700;
            color: #1a365d;
            border-bottom: 1px solid #cbd5e0;
            padding-bottom: 3px;
            margin-top: 20px;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        h3 {{
            font-size: 13px;
            font-weight: 600;
            color: #2d3748;
            margin-top: 12px;
            margin-bottom: 2px;
        }}
        .job-role-line {{
            display: flex;
            justify-content: space-between;
            font-weight: 500;
            color: #4a5568;
            margin-bottom: 6px;
            font-size: 12px;
        }}
        .job-role {{
            font-style: italic;
        }}
        .job-date {{
            color: #718096;
            font-weight: 400;
        }}
        ul {{
            margin: 0 0 8px 0;
            padding-left: 18px;
        }}
        li {{
            margin-bottom: 4px;
            text-align: justify;
        }}
        
        /* Avoid breaks inside sections/job entries */
        .resume-section.avoid-break {{
            break-inside: avoid;
            -webkit-column-break-inside: avoid;
        }}
        .job-entry {{
            break-inside: avoid;
            -webkit-column-break-inside: avoid;
            margin-bottom: 12px;
        }}
        
        /* A4 Page Formatting for print/export */
        @page {{
            size: A4;
            margin: 12mm 15mm;
        }}
        @media print {{
            body {{
                padding: 0;
            }}
            h2 {{
                page-break-after: avoid;
            }}
            h3, .job-role-line {{
                page-break-after: avoid;
            }}
            ul {{
                page-break-inside: auto;
            }}
            li {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{name}</h1>
        <div class="title">{title}</div>
    </div>
    
    {f'<div class="intro-p">{intro}</div>' if intro else ''}
    
    {exp_section_html}
    
    {edu_section_html}
    
    {ach_section_html}
</body>
</html>
"""
    return html_template

def convert_md_to_pdf(md_path, pdf_path):
    print(f"Converting {md_path} -> {pdf_path}...")
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
        
    html_content = parse_and_enhance_resume(md_content)
    temp_html_path = md_path + ".temp.html"
    
    with open(temp_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            absolute_html_url = 'file://' + os.path.abspath(temp_html_path)
            page.goto(absolute_html_url)
            page.wait_for_load_state('networkidle')
            
            # Print page to PDF
            page.pdf(
                path=pdf_path,
                format='A4',
                print_background=True,
                margin={
                    'top': '12mm',
                    'bottom': '12mm',
                    'left': '15mm',
                    'right': '15mm'
                }
            )
            browser.close()
        print(f"Success! Created {pdf_path}")
    finally:
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 convert.py <file.md> [output.pdf]")
        print("  python3 convert.py --all [dir]")
        sys.exit(1)
        
    arg1 = sys.argv[1]
    
    if arg1 == '--all':
        target_dir = sys.argv[2] if len(sys.argv) > 2 else '.'
        if not os.path.isdir(target_dir):
            print(f"Error: {target_dir} is not a directory.")
            sys.exit(1)
            
        print(f"Processing all Markdown files in directory: {target_dir}")
        for filename in os.listdir(target_dir):
            if filename.endswith('.md'):
                md_path = os.path.join(target_dir, filename)
                pdf_filename = filename[:-3] + '.pdf'
                pdf_path = os.path.join(target_dir, pdf_filename)
                try:
                    convert_md_to_pdf(md_path, pdf_path)
                except Exception as e:
                    print(f"Failed converting {filename}: {e}")
    else:
        md_path = arg1
        if not os.path.exists(md_path):
            print(f"Error: File {md_path} does not exist.")
            sys.exit(1)
            
        if len(sys.argv) > 2:
            pdf_path = sys.argv[2]
        else:
            pdf_path = md_path[:-3] + '.pdf' if md_path.endswith('.md') else md_path + '.pdf'
            
        convert_md_to_pdf(md_path, pdf_path)

if __name__ == '__main__':
    main()
