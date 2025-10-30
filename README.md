# ollama-model-keeper
Reloads a specified model when no other models are loaded.
Vibe coded with Grok 3.

## Configuration

The script can be configured using environment variables:

- `TARGET_MODEL`: The model to keep loaded (default: "gemma3")
- `OLLAMA_URI`: Ollama server URI (default: "http://localhost:11434")
- `CYCLE_INTERVAL`: Time in seconds between cycles (default: 5)
- `MONITOR_INTERVAL`: Time in seconds between monitoring checks (default: 60)
- `CONTEXT_LENGTH`: Context window size for model loading (default: 4096)
- `LOG_LEVEL`: Logging level (default: "INFO")
