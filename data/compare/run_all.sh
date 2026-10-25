#!/bin/zsh
# Runs the three open models one after the other on the same Mac; logs in log_<slug>.txt, results in results_<slug>.json.
cd "$(dirname "$0")"
run() { uv run --quiet --no-project --with mlx-lm --with pandas --with pyarrow --with huggingface_hub python compare_models.py "$1" "$2" > "log_$2.txt" 2>&1; }
run mlx-community/gemma-3-4b-it-8bit gemma3-4b-8bit
run mlx-community/gemma-4-e4b-it-8bit gemma4-e4b-8bit
run mlx-community/Qwen3-4B-Instruct-2507-8bit qwen3-4b-8bit
echo finished > run_all.done
