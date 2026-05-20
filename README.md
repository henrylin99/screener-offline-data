# screener-offline-data skill

基于**离线落盘**的 A 股大宽表数据（`data/screener_daily`）做本地选股 / 回测 / 因子分析，全程 pandas 直接读 parquet，**无网络、无 token、无后端服务依赖**。

## 安装

```bash
pip install -r requirements.txt
```

## 数据位置

Hive 分区目录，逐交易日一个 parquet：

```
data/screener_daily/daily/year=YYYY/month=MM/day=DD/data.parquet
```

默认相对仓库根解析。若在别处运行，用环境变量覆盖：

```bash
export SCREENER_DATA_DIR=/path/to/screener_daily/daily
```

## 用法

```python
import screener_data as d

d.list_available_dates()              # ['20260105', ..., '20260519']
day = d.load_day("20260519")          # 单日截面 5484 x 240
panel = d.load_range("20260420", "20260519")  # 区间面板数据
```

字段含义见同目录 [`宽表数据字典.md`](宽表数据字典.md)，开发思路见 [`SKILL.md`](SKILL.md)。

## 在 openclaw / hermes 中使用

把整个 `screener-offline-data/` 目录复制到 agent 的 skills 路径下，agent 会自动读取 `SKILL.md`；数据需另行落盘到 `SCREENER_DATA_DIR` 指向的位置。

## 冒烟测试

```bash
python smoke.py
```

预期输出：可用交易日数与区间、最新一日的行列数、首板 PE<20 命中数、区间面板行数。
