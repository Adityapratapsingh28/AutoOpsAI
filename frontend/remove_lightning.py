import os

for root, _, files in os.walk("."):
    for f in files:
        if f.endswith(".html"):
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as file:
                content = file.read()
            
            # Remove lightning emoji
            content = content.replace("⚡ ", "").replace("⚡", "")

            with open(path, "w", encoding="utf-8") as file:
                file.write(content)

print("Lightning removed from HTML files")
