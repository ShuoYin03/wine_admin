from pathlib import Path


def build_spider_log_file(filename: str) -> str:
    logs_dir = Path(__file__).resolve().parents[2] / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return str(logs_dir / filename)
