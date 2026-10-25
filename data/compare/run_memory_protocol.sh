#!/bin/bash
# The memory readings of the six open builds, taken the way Apple's model was (see memory_protocol.py). Log: run_memory_protocol.log
cd "$(dirname "$0")"
for spec in "mlx-community/Qwen3-4B-Instruct-2507-4bit qwen3-4b-4bit 8121" "mlx-community/gemma-3-4b-it-4bit gemma3-4b-4bit 8122" "mlx-community/gemma-4-e4b-it-4bit gemma4-e4b-4bit 8123" \
            "mlx-community/Qwen3-4B-Instruct-2507-8bit qwen3-4b-8bit 8124" "mlx-community/gemma-3-4b-it-8bit gemma3-4b-8bit 8125" "mlx-community/gemma-4-e4b-it-8bit gemma4-e4b-8bit 8126"; do
  NO_COLOR=1 uv run --quiet --no-project --with mlx-lm python memory_protocol.py $spec
  sleep 3
done
echo ALL DONE
