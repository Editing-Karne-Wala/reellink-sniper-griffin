import importlib
import types  # Standard way to check types

def explore_module(module, depth=1, max_depth=2):
    """ Recursively explore a module to reveal available attributes and submodules. """
    if depth > max_depth:
        return
    
    try:
        module_name = module.__name__
    except AttributeError:
        module_name = str(module)

    print(f"\n🔍 Exploring: {module_name} (Depth: {depth})")
    
    attributes = dir(module)

    for attr in attributes:
        if attr.startswith("__"): 
            continue

        try:
            attr_obj = getattr(module, attr)
            
            if isinstance(attr_obj, types.ModuleType):
                print(f"  📦 {attr} -> SUBMODULE")
                explore_module(attr_obj, depth + 1, max_depth)
            
            elif callable(attr_obj):
                print(f"  📌 {attr} -> FUNCTION/CLASS")
            
            else:
                print(f"  🏷  {attr} -> ATTRIBUTE")
                
        except Exception as e:
            print(f"  ❌ {attr} -> Could not retrieve: {e}")

# 🚀 Usage
LIBRARY_NAME = "src.processor" 
SUBMODULE_NAME = "" 

try:
    lib = importlib.import_module(LIBRARY_NAME)
    print(f"\n✅ Successfully imported {LIBRARY_NAME}")
    explore_module(lib)

except ModuleNotFoundError:
    print(f"\n❌ Failed to import {LIBRARY_NAME}. Is it installed?")