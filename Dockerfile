# NashForge 运行镜像（演示端到端 ≤60s）。作者：晨星。
FROM python:3.12-slim

WORKDIR /app

# 先装锁定依赖（利用层缓存）
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt

# 再装包本体
COPY pyproject.toml ./
COPY nashforge ./nashforge
COPY examples ./examples
RUN pip install --no-cache-dir -e .

# 默认运行端到端 demo（精确 oracle + 四条门禁）
CMD ["python", "examples/run_demo.py"]
