from dataclasses import dataclass
from typing import Optional

@dataclass
class Settings:
    ollama_chat_url: str
    openai_api_base: str
    ollama_host: str

# Default settings - these will be overridden by config.json
settings = Settings(
    ollama_chat_url="http://localhost:11434/api/chat",
    openai_api_base="http://localhost:11434/v1",
    ollama_host="http://localhost:11434"
)

# Load configuration from file if it exists
import json
import os
from pathlib import Path

config_path = Path(__file__).parent / "config.json"

if config_path.exists():
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    # Override settings with values from config.json
    if 'ollama_chat_url' in config_data:
        settings.ollama_chat_url = config_data['ollama_chat_url']
    if 'openai_api_base' in config_data:
        settings.openai_api_base = config_data['openai_api_base']
    if 'ollama_host' in config_data:
        settings.ollama_host = config_data['ollama_host']
