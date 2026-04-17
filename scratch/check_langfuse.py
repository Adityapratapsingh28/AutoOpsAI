from langfuse import Langfuse
import inspect

print(f"Langfuse init signature: {inspect.signature(Langfuse.__init__)}")
print(f"Langfuse methods: {[m for m in dir(Langfuse) if not m.startswith('_')]}")
