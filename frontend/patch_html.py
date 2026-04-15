import os
import re

button_html = """
                </div>
                <button id="themeToggleBtn" onclick="toggleTheme()" style="background: none; border: none; font-size: 1.2rem; cursor: pointer; border-radius: 50%; padding: 4px;">🌙</button>
"""

for root, _, files in os.walk("."):
    for f in files:
        if f.endswith(".html"):
            path = os.path.join(root, f)
            with open(path, "r") as file:
                content = file.read()
            
            # Insert script if not present
            if '<script src="js/theme.js"></script>' not in content:
                content = content.replace("</head>", '    <script src="js/theme.js"></script>\n</head>')
            
            # Insert toggle switch
            if 'onclick="toggleTheme()"' not in content:
                content = re.sub(r'(\s*)</div>(\s*)</aside>', r'\n' + button_html + r'\n\2</aside>', content)

            with open(path, "w") as file:
                file.write(content)

print("HTML Patched")
