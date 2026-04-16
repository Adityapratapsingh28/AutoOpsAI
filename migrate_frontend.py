import os
import re

html_files = [
    "dashboard.html", "files.html", "history.html", "index.html", 
    "schedule.html", "settings.html", "workflow.html"
]

src_dir = "frontend/js"
html_dir = "frontend"
react_dir = "frontend-react/src"

def to_camel_case(snake_str):
    components = snake_str.split('-')
    return components[0] + ''.join(x.title() for x in components[1:])

def convert_to_jsx(html):
    # Convert 'class=' to 'className='
    html = html.replace('class=', 'className=')
    # Convert 'for=' to 'htmlFor='
    html = html.replace('for=', 'htmlFor=').replace('For=', 'htmlFor=')
    # Remove HTML comments to avoid syntax issues sometimes
    html = re.sub(r'<!--(.*?)-->', '', html, flags=re.DOTALL)
    # Fix inline styles (very basic fix for this project)
    html = re.sub(r'style="([^"]+)"', r'style={{ \1 }}', html)
    html = html.replace('display:flex;gap:1rem;margin-bottom:2rem;', "display: 'flex', gap: '1rem', marginBottom: '2rem'")
    html = html.replace('display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:0.75rem;', 
                        "display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(250px,1fr))', gap: '0.75rem'")
    html = html.replace('color: var(--error);', "color: 'var(--error)'")
    html = html.replace('background: none; border: none; font-size: 1.2rem; cursor: pointer; border-radius: 50%; padding: 4px;',
                        "background: 'none', border: 'none', fontSize: '1.2rem', cursor: 'pointer', borderRadius: '50%', padding: '4px'")
    html = html.replace('cursor:pointer;', "cursor: 'pointer'")
    html = html.replace('font-size:0.85rem;font-weight:600;color:var(--text-primary);',
                        "fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)'")
    html = html.replace('padding:2rem;', "padding: '2rem'")
    # Remove onclick attributes
    html = re.sub(r'onclick="[^"]*"', '', html)
    html = re.sub(r'onsubmit="[^"]*"', '', html)
    html = html.replace('required minlength="6"', 'required minLength={6}')
    html = html.replace('stroke-width="2"', 'strokeWidth="2"')
    html = html.replace('stroke-linecap="round"', 'strokeLinecap="round"')
    html = html.replace('stroke-linejoin="round"', 'strokeLinejoin="round"')
    html = re.sub(r'<img(.*?)(?<!/)>', r'<img\1 />', html)  # self-close img tags
    html = re.sub(r'<input(.*?)(?<!/)>', r'<input\1 />', html)  # self-close input tags
    return html

def extract_main(html_content, is_index=False):
    if is_index:
        match = re.search(r'<div className="auth-container">(.*?)</div>\s*<div className="toast-container"', html_content, re.DOTALL)
        if match:
            return '<div className="auth-container">\n' + match.group(1) + '\n</div>'
    match = re.search(r'<main className="main-content">(.*?)</main>', html_content, re.DOTALL)
    if match:
        return match.group(1)
    return html_content

# Create React structure
os.makedirs(f"{react_dir}/pages", exist_ok=True)
os.makedirs(f"{react_dir}/components", exist_ok=True)
os.makedirs(f"{react_dir}/utils", exist_ok=True)

frontend_import = ""
app_routes = ""

for html_file in html_files:
    page_name = html_file.replace('.html', '').capitalize()
    if page_name == 'Index':
        page_name = 'SignIn'
    
    with open(f"{html_dir}/{html_file}", 'r') as f:
        raw_html = f.read()
    
    raw_html = convert_to_jsx(raw_html)
    main_content = extract_main(raw_html, is_index=(html_file=='index.html'))
    
    component = f"""import React from 'react';

export default function {page_name}() {{
    return (
        <React.Fragment>
            {main_content}
        </React.Fragment>
    );
}}
"""
    
    with open(f"{react_dir}/pages/{page_name}.jsx", 'w') as f:
        f.write(component)

print("Migration completed.")
