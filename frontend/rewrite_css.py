import re

with open("css/styles.css", "r") as f:
    css = f.read()

# 1. Update :root
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
}"""

css = re.sub(r':root\s*\{.*?\n\}', new_root, css, flags=re.DOTALL)

# 2. Update font family
css = css.replace("font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;",
                  "font-family: 'Airbnb Cereal VF', Circular, -apple-system, system-ui, Roboto, 'Helvetica Neue', sans-serif;\n    font-weight: 500;\n    letter-spacing: -0.18px;")

# 3. Update body background mesh (remove it)
css = re.sub(r'\.bg-mesh\s*\{.*?\n\}', '.bg-mesh { display: none; }', css, flags=re.DOTALL)

# 4. Fix main CTA buttons
css = re.sub(r'\.btn-primary\s*\{.*?\n\}', '.btn-primary {\n    background: #ff385c;\n    color: #ffffff;\n    border-radius: var(--radius-sm);\n    box-shadow: none;\n    padding: 0px 24px;\n    height: 48px;\n}', css, flags=re.DOTALL)
css = re.sub(r'\.btn-primary:hover\s*\{.*?\n\}', '.btn-primary:hover {\n    background: #e00b41;\n    transform: none;\n    box-shadow: var(--shadow-hover);\n}', css, flags=re.DOTALL)

# 5. Fix cards to use shadows!
css = re.sub(r'\.card\s*\{.*?\n\}', '.card {\n    background: #ffffff;\n    border: none;\n    border-radius: var(--radius-lg);\n    padding: 1.5rem;\n    box-shadow: var(--shadow-card);\n    transition: var(--transition-normal);\n}', css, flags=re.DOTALL)
css = re.sub(r'\.stat-card\s*\{.*?\n\}', '.stat-card {\n    background: #ffffff;\n    border: none;\n    border-radius: var(--radius-lg);\n    padding: 1.25rem;\n    box-shadow: var(--shadow-card);\n    transition: var(--transition-normal);\n    position: relative;\n    overflow: hidden;\n}', css, flags=re.DOTALL)

# Make headers pop properly
css = css.replace("color: var(--text-bright);", "color: #222222; font-weight: 700; letter-spacing: -0.44px;")

# Circular avatars / generic controls
css = re.sub(r'\.user-avatar\s*\{.*?\n\}', '.user-avatar {\n    width: 36px;\n    height: 36px;\n    border-radius: 50%;\n    background: #ff385c;\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    font-weight: 700;\n    font-size: 0.8rem;\n    color: #ffffff;\n    flex-shrink: 0;\n}', css, flags=re.DOTALL)

with open("css/styles.css", "w") as f:
    f.write(css)

print("CSS Rewritten")
