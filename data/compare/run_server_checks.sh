#!/bin/bash
# Memory by `footprint` (six builds), then the same questions behind a local server (three 8-bit builds). Log: run_server_checks.log
cd "$(dirname "$0")"
for spec in "mlx-community/Qwen3-4B-Instruct-2507-4bit qwen3-4b-4bit 8101" "mlx-community/gemma-3-4b-it-4bit gemma3-4b-4bit 8102" "mlx-community/gemma-4-e4b-it-4bit gemma4-e4b-4bit 8103" \
            "mlx-community/Qwen3-4B-Instruct-2507-8bit qwen3-4b-8bit 8104" "mlx-community/gemma-3-4b-it-8bit gemma3-4b-8bit 8105" "mlx-community/gemma-4-e4b-it-8bit gemma4-e4b-8bit 8106"; do
  uv run --quiet --no-project --with mlx-lm python memory_footprint.py $spec
done
for spec in "mlx-community/gemma-3-4b-it-8bit gemma3-4b-8bit 8111" "mlx-community/Qwen3-4B-Instruct-2507-8bit qwen3-4b-8bit 8112" "mlx-community/gemma-4-e4b-it-8bit gemma4-e4b-8bit 8113"; do
  uv run --quiet --no-project --with pandas --with pyarrow --with huggingface_hub python server_rerun.py $spec
done
echo ALL DONE
