import os

react_dir = "frontend-react/src/pages"
for filename in os.listdir(react_dir):
    if filename.endswith(".jsx"):
        path = os.path.join(react_dir, filename)
        with open(path, 'r') as f:
            content = f.read()
        
        content = content.replace("htmlhtmlFor=", "htmlFor=")
        
        with open(path, 'w') as f:
            f.write(content)

print("Fixed htmlhtmlFor!")
