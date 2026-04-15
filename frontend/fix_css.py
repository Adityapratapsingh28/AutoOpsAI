import re

with open("css/styles.css", "r") as f:
    css = f.read()

# Original root ends exactly before Reset & Base
original_root_match = re.search(r':root\s*\{.*?\n\}', css, flags=re.DOTALL)
if original_root_match:
    original_root = original_root_match.group(0)
else:
    print("Failed to find root")

def patch_css(css_content):
    # Airbnb Light Theme
    new_root = """:root {
    /* Primary Palette */
    --bg-primary: #ffffff;
    --bg-secondary: #f7f7f7;
    --bg-tertiary: #ebebeb;
    --bg-card: #ffffff;
    --bg-card-hover: #fcfcfc;
    --bg-input: #ffffff;
    --bg-sidebar: #ffffff;

    /* Accent Colors */
    --accent-primary: #ff385c;
    --accent-secondary: #e00b41;
    --accent-gradient: #ff385c;
    --accent-glow: rgba(255, 56, 92, 0.2) 0px 4px 12px;

    /* Status Colors */
    --success: #10b981;
    --success-bg: rgba(16, 185, 129, 0.1);
    --warning: #f59e0b;
    --warning-bg: rgba(245, 158, 11, 0.1);
    --error: #c13515;
    --error-bg: rgba(193, 53, 21, 0.1);
    --info: #428bff;
    --info-bg: rgba(66, 139, 255, 0.1);
    --pending: #92174d;
    --pending-bg: rgba(146, 23, 77, 0.1);

    /* Text Colors */
    --text-primary: #222222;
    --text-secondary: #6a6a6a;
    --text-muted: #929292;
    --text-bright: #222222;

    /* Borders */
    --border-color: #ebebeb;
    --border-color-hover: #c1c1c1;

    /* Shadows */
    --glass-bg: #ffffff;
    --glass-border: rgba(0,0,0,0.04);
    --glass-blur: 0px;
    --shadow-card: rgba(0,0,0,0.02) 0px 0px 0px 1px, rgba(0,0,0,0.04) 0px 2px 6px, rgba(0,0,0,0.1) 0px 4px 8px;
    --shadow-hover: rgba(0,0,0,0.08) 0px 4px 12px;

    /* Spacing */
    --sidebar-width: 260px;
    --sidebar-collapsed: 72px;
    --header-height: 80px;

    /* Radius */
    --radius-sm: 8px;
    --radius-md: 14px;
    --radius-lg: 20px;
    --radius-xl: 32px;

    /* Transitions */
    --transition-fast: 0.15s ease;
    --transition-normal: 0.25s ease;
    --transition-slow: 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    
    /* Mesh display */
    --mesh-display: none;
}"""

    dark_theme = """
[data-theme="dark"] {
    --bg-primary: #06080f;
    --bg-secondary: #0c1020;
    --bg-tertiary: #111631;
    --bg-card: rgba(15, 20, 45, 0.7);
    --bg-card-hover: rgba(20, 28, 58, 0.85);
    --bg-input: rgba(12, 16, 38, 0.8);
    --bg-sidebar: rgba(8, 12, 28, 0.95);

    --accent-primary: #4f7cff;
    --accent-secondary: #7c5cff;
    --accent-gradient: linear-gradient(135deg, #4f7cff 0%, #7c5cff 50%, #c05cff 100%);
    --accent-glow: 0 0 20px rgba(79, 124, 255, 0.3);

    --success: #10b981;
    --success-bg: rgba(16, 185, 129, 0.12);
    --warning: #f59e0b;
    --warning-bg: rgba(245, 158, 11, 0.12);
    --error: #ef4444;
    --error-bg: rgba(239, 68, 68, 0.12);
    --info: #3b82f6;
    --info-bg: rgba(59, 130, 246, 0.12);
    --pending: #8b5cf6;
    --pending-bg: rgba(139, 92, 246, 0.12);

    --text-primary: #e8ecf4;
    --text-secondary: #8892a8;
    --text-muted: #555e72;
    --text-bright: #ffffff;

    --border-color: rgba(79, 124, 255, 0.12);
    --border-color-hover: rgba(79, 124, 255, 0.3);

    --glass-bg: rgba(15, 20, 50, 0.5);
    --glass-border: rgba(79, 124, 255, 0.08);
    --glass-blur: 20px;
    --shadow-card: none;
    --shadow-hover: 0 4px 15px rgba(79, 124, 255, 0.3);
    
    --mesh-display: block;
}
"""

    css_content = re.sub(r':root\s*\{.*?\n\}', new_root + dark_theme, css_content, flags=re.DOTALL)
    
    # Update fonts
    css_content = css_content.replace(
        "font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;",
        "font-family: 'Airbnb Cereal VF', Circular, -apple-system, system-ui, Roboto, 'Helvetica Neue', sans-serif;\n    font-weight: 500;\n    letter-spacing: -0.18px;"
    )

    # BG Mesh
    css_content = css_content.replace(
        ".bg-mesh {\n    position: fixed;",
        ".bg-mesh {\n    display: var(--mesh-display);\n    position: fixed;"
    )

    # Cards (make them use shadow variables instead of just hardcodings)
    css_content = css_content.replace(
        "backdrop-filter: blur(var(--glass-blur));\n    transition: var(--transition-normal);",
        "backdrop-filter: blur(var(--glass-blur));\n    box-shadow: var(--shadow-card);\n    transition: var(--transition-normal);"
    )
    
    # Headers weight override so it matches Airbnb
    # We do NOT hardcode colors! We use variables.
    css_content = css_content.replace(
        "color: var(--text-bright);",
        "color: var(--text-bright);\n    letter-spacing: -0.44px;\n    font-weight: 700;"
    )
    
    return css_content

with open("css/styles.css", "w") as f:
    f.write(patch_css(css))

print("CSS Fixed")
