import langfuse
import pkgutil

print(f"Langfuse version: {getattr(langfuse, '__version__', 'unknown')}")
print(f"Langfuse location: {langfuse.__file__}")
print("Submodules:")
for loader, module_name, is_pkg in pkgutil.walk_packages(langfuse.__path__):
    print(f"- {module_name}")
