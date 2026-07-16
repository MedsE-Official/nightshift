#!/bin/zsh

export OPENAI_API_BASE="http://localhost:11434/v1"
export OPENAI_API_KEY="ollama"

aider \
  --model openai/qwen3-coder:latest \
  --no-show-model-warnings \
  --no-pretty \
  --yes-always \
  --no-auto-commits \
  "$@"
