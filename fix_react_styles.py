import os
import re

react_dir = "frontend-react/src/pages"

def fix_style(match):
    style_content = match.group(1).strip()
    if "'" in style_content or '"' in style_content:
        if "display: 'flex'" in style_content or "cursor: 'pointer'" in style_content or "padding: '2rem'" in style_content:
            return match.group(0) # Already ok
        if "color: 'var(--error)'" in style_content:
            return match.group(0)

    # If it ends with semicolon, strip it
    style_content = style_content.strip(';')
    pairs = style_content.split(';')
    
    new_pairs = []
    for pair in pairs:
        if ':' not in pair: continue
        k, v = pair.split(':', 1)
        k = k.strip()
        v = v.strip()
        
        # camelCase the key
        k_parts = k.split('-')
        k_camel = k_parts[0] + ''.join(x.title() for x in k_parts[1:])
        
        # If value is purely numeric, we can leave it as string or number
        # React expects strings for things with px/rem.
        new_pairs.append(f"'{k_camel}': '{v}'")
        
    return "style={{ " + ", ".join(new_pairs) + " }}"

for filename in os.listdir(react_dir):
    if filename.endswith(".jsx"):
        path = os.path.join(react_dir, filename)
        with open(path, 'r') as f:
            content = f.read()
        
        content = re.sub(r'style=\{\{\s*(.*?)\s*\}\}', fix_style, content)
        # Also fix class= that might have slipped through
        content = content.replace("class=", "className=")
        # Fix onchange= -> onChange=
        content = content.replace("onchange=", "onChange=")
        content = content.replace("onclick=", "onClick=")
        content = content.replace("onsubmit=", "onSubmit=")
        content = content.replace("colspan=", "colSpan=")
        
        with open(path, 'w') as f:
            f.write(content)

print("Fixed styles!")
