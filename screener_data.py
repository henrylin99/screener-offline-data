"""离线读取 screener_daily 大宽表（Hive 分区 parquet），无网络依赖。

数据目录默认相对仓库根：data/screener_daily/daily/
可用环境变量 SCREENER_DATA_DIR 覆盖。
"""
import os
import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(
    os.environ.get(
        "SCREENER_DATA_DIR",
        Path(__file__).resolve().parents[2] / "data" / "screener_daily" / "daily",
    )
)


def list_available_dates() -> list[str]:
    """枚举数据集中实际存在的交易日，返回升序 YYYYMMDD 字符串列表。"""
    dates = []
    for p in DATA_DIR.glob("year=*/month=*/day=*/data.parquet"):
        y, m, d = re.search(r"year=(\d+)/month=(\d+)/day=(\d+)", p.as_posix()).groups()
        dates.append(f"{int(y):04d}{int(m):02d}{int(d):02d}")
    return sorted(dates)


def load_day(date: str) -> pd.DataFrame:
    """读单个交易日的大宽表，date 为 YYYYMMDD。"""
    y, m, d = date[:4], int(date[4:6]), int(date[6:8])
    return pd.read_parquet(DATA_DIR / f"year={y}/month={m:02d}/day={d:02d}/data.parquet")


def load_range(start: str, end: str) -> pd.DataFrame:
    """读区间内所有交易日并拼成面板数据（含 trade_date 列）。"""
    days = [x for x in list_available_dates() if start <= x <= end]
    if not days:
        raise ValueError(f"区间内无数据: {start} - {end}")
    return pd.concat([load_day(x) for x in days], ignore_index=True)
