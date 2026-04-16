import json
from app.main import app

openapi_schema = app.openapi()
with open("api_documents.json", "w") as f:
    json.dump(openapi_schema, f, indent=2)
print("API documents saved to api_documents.json")
