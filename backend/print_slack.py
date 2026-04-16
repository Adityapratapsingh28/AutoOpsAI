import json
import logging
from pprint import pprint

def parse_db_output():
    # Read output.log or just re-run test_db_result.py with print
    with open("test_db_result.py", "r") as f:
        content = f.read()
    
    new_content = content.replace("for agent_name, result in tool_results.items():\n", 'import json\n    print(json.dumps(tool_results, indent=2))\n    for agent_name, result in tool_results.items():\n')
    with open("test_db_result2.py", "w") as f:
        f.write(new_content)

parse_db_output()
