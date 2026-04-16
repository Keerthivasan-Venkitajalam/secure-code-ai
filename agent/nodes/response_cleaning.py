"""Helpers for normalizing LLM code responses."""


def clean_python_code_response(response: str) -> str:
    """Extract raw Python code from a model response.

    Removes markdown fences when present and trims whitespace.
    """
    if not response:
        return ""

    # Remove markdown code blocks
    if "```python" in response:
        start = response.find("```python") + len("```python")
        end = response.find("```", start)
        if end != -1:
            response = response[start:end]
    elif "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        if end != -1:
            response = response[start:end]

    return response.strip()
