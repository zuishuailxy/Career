# CLI
uv pip install -e . 2>&1 && uv run main.py -p "我感觉这个项目里的代码好像有严重的并发安全问题。请你在这个目录下自行探索，找到问题文件，分析原因，并进行修复和正确性验证" -d "./workspace" -s "cli-07-13-2"  2>&1

# 飞书 mode
# uv pip install -e . 2>&1 && uv run main.py  --mode feishu 2>&1

# run Bunchmark
# uv pip install -e . 2>&1 && uv run run_benchmark.py 2>&1