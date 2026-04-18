import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_STRING: str = f"ollama/{OLLAMA_MODEL}"
PIPELINE_MODE: str = os.getenv("PIPELINE_MODE", "reliable")

DATA_DIR: str = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_DIR: str = os.path.join(os.path.dirname(__file__), "output")
LOG_DIR: str = os.path.join(os.path.dirname(__file__), "logs")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
