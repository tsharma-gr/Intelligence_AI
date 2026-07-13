import os

def load_prompt(filename: str) -> str:
    """Load prompt template from the current directory."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Prompt template {filename} not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
