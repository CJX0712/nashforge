# NashForge Makefile。作者：晨星。
# 注意：recipe 行必须以 Tab 缩进（非空格）。

.PHONY: install lint test demo ci

install:
	pip install -r requirements.lock.txt
	pip install -e .

lint:
	ruff check .

test:
	pytest -q

demo:
	python examples/run_demo.py

ci: lint test
