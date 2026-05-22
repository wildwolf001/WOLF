"""
Synthetic Output Tool - Generate synthetic/mock data for testing
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any
import random
import string

router = APIRouter()


class SyntheticTextInput(BaseModel):
    length: int = 100
    pattern: Optional[str] = None  # lorem, code, json, etc.


class SyntheticJSONInput(BaseModel):
    data_schema: dict
    count: int = 1


class SyntheticCodeInput(BaseModel):
    language: str = "python"
    lines: int = 10


@router.post("/synthetic/text")
async def generate_text(input: SyntheticTextInput) -> dict:
    """Generate synthetic text content"""
    if input.pattern == "lorem":
        words = ["lorem", "ipsum", "dolor", "sit", "amet", "consectetur",
                 "adipiscing", "elit", "sed", "do", "eiusmod", "tempor"]
        text = " ".join(random.choice(words) for _ in range(input.length // 5))
    elif input.pattern == "code":
        text = "def example():\n" + "    pass\n" * (input.length // 10)
    elif input.pattern == "json":
        import json
        obj = {"data": [random.randint(0, 100) for _ in range(10)]}
        text = json.dumps(obj, indent=2)
    else:
        # Random alphanumeric
        text = ''.join(random.choices(string.ascii_letters + string.digits, k=input.length))

    return {"text": text, "length": len(text)}


@router.post("/synthetic/json")
async def generate_json(input: SyntheticJSONInput) -> List[dict]:
    """Generate synthetic JSON data matching a schema"""
    import json

    def generate_from_schema(schema: dict) -> dict:
        result = {}
        for key, value in schema.items():
            if isinstance(value, dict):
                result[key] = generate_from_schema(value)
            elif isinstance(value, list):
                # Generate one item for now
                if value:
                    item_schema = value[0] if isinstance(value[0], dict) else {"type": value[0]}
                    result[key] = [generate_from_schema(item_schema) if isinstance(item_schema, dict) else type(item_schema[0])()]
            elif isinstance(value, str):
                if value == "string":
                    result[key] = "sample_" + ''.join(random.choices(string.ascii_lowercase, k=5))
                elif value == "number":
                    result[key] = random.randint(0, 100)
                elif value == "boolean":
                    result[key] = random.choice([True, False])
                else:
                    result[key] = value
            else:
                result[key] = value
        return result

    return [generate_from_schema(input.data_schema) for _ in range(input.count)]


@router.post("/synthetic/code")
async def generate_code(input: SyntheticCodeInput) -> dict:
    """Generate synthetic code"""
    if input.language == "python":
        code = "def function():\n"
        code += "    \"\"\"Sample function\"\"\"\n"
        code += "    result = []\n"
        for i in range(input.lines - 3):
            code += f"    # Line {i + 1}\n"
            code += f"    value_{i} = {random.randint(0, 100)}\n"
        code += "    return result\n"
    elif input.language == "javascript":
        code = "function example() {\n"
        for i in range(input.lines - 2):
            code += f"  const value{i} = {random.randint(0, 100)};\n"
        code += "  return value0;\n"
        code += "}\n"
    else:
        code = f"// {input.language} code ({input.lines} lines)\n"
        for i in range(input.lines - 1):
            code += f"line {i + 1};\n"

    return {"code": code, "language": input.language, "lines": input.lines}