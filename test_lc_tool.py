import asyncio
from langchain_core.tools import StructuredTool

def my_func(a: int, b: str) -> str:
    """This does something."""
    return f"{a} {b}"

t = StructuredTool.from_function(my_func)
print(t.name)
print(t.description)
print(t.args_schema.schema())
