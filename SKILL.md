---
name: screener-offline-data
description: 基于离线落盘的 A 股大宽表数据（data/screener_daily）做本地开发与研究——选股、回测、因子分析、板块轮动等，全部用 pandas 直接读 parquet，无需任何网络 API。适用于"用本地历史数据回测这个形态""离线跑一遍多因子选股"这类请求。
---

## 这是什么

一套**离线落盘**的 A 股全市场日线大宽表，按交易日逐日存放在本地磁盘。开发时直接用 pandas 读取 parquet 文件即可，**不依赖任何后端服务、不需要 token、不发网络请求**。

## 数据位置与目录结构

数据按 Hive 分区目录逐日存放：

```
data/screener_daily/daily/
  year=2026/
    month=01/
      day=05/data.parquet
      day=06/data.parquet
      ...
    month=05/
      day=19/data.parquet
```

- 路径模板：`data/screener_daily/daily/year=YYYY/month=MM/day=DD/data.parquet`（month/day 两位零填充）
- 每个 `data.parquet` = **一个交易日的全市场横截面大宽表**：一行 = 一只股票当天的全部特征，约 **5484 行 × 240 列**。
- 当前数据覆盖区间约 `20260105` ~ `20260519`（以实际目录为准，下面给了枚举可用日期的代码）。

## 数据结构（大宽表）

历史按交易日逐日存储，**同一套列结构**，因此把多日 `pd.concat` 起来就是 `(ts_code, trade_date)` 面板数据，可直接用于回测、因子分析、截面/时序统计。

列分为以下几类：

- **标识 / 分类**：`ts_code`(代码) `name`(名称) `industry`(行业) `area`(地区) `trade_date`(YYYYMMDD)
- **行情**：`open` `high` `low` `close` `pre_close` `change` `pct_chg`(涨跌幅%) `vol`(成交量) `amount`(成交额,元) `turnover_rate`(换手率) `volume_ratio`(量比)
- **复权价**：`*_hfq`(后复权) `*_qfq`(前复权)，含 open/high/low/close/pre_close。**回测算收益必须用复权价**，原始 `close` 不连续。
- **估值**：`pe` `pe_ttm` `pb` `ps` `ps_ttm` `dv_ratio`(股息率) `total_mv`(总市值,万元) `circ_mv`(流通市值,万元) `total_share` `float_share` `free_share`
- **资金流**：`net_mf_amount`(主力净流入,千元) `net_mf_vol`，以及大/中/小/特大单的买卖量额 `buy_lg_amount` `sell_elg_vol` 等
- **技术指标**：`macd_dif/dea/macd` `kdj_k/d/j` `rsi_6/12/24` `boll_upper/mid/lower` `cci`
- **财务**（`fin_` 前缀，按最近一期报告填充）：营收 `fin_revenue`、净利 `fin_n_income`、EPS `fin_basic_eps`、资产负债 `fin_total_assets/liab/hldr_eqy`、现金流 `fin_n_cashflow_act`、衍生比率 `fin_gross_margin`(毛利率) `fin_net_margin`(净利率) `fin_debt_ratio`(资产负债率) `fin_current_ratio`(流动比率) 等
- **K线形态信号**（125 个 `pattern_*` 二值列，1=命中）：单K/双K/三K 形态、趋势结构、量价形态、复合形态。例：`pattern_zhangting`/`pattern_first_limit`(首板) `pattern_multi_limit`(连板) `pattern_bullish_engulfing`(阳包阴) `pattern_golden_cross`(均线金叉) `pattern_box_breakout`(箱体放量突破)。
- **动量因子**（二值，1=命中）：`break_high_20/60/120/250`(突破N日新高) `consec_up_3/5`(连涨N日)；`consec_up_days` 是连涨天数计数（非二值），`vol_ratio_5`(5日量比)

> **完整字段字典见同目录 [`宽表数据字典.md`](宽表数据字典.md)。** 上面只是分类速览；当你需要某个字段的精确含义、单位、数据类型、取值范围或样例时（尤其是 `fin_*`、资金流分单级别、复权价等），先读那份字典再写代码，不要靠字段名猜。它按分组列出每一列的中英文说明，并附带某一交易日的实际取值观察。

## 读取数据（pandas）

```python
import pandas as pd
import glob, re
from pathlib import Path

DATA_DIR = Path("data/screener_daily/daily")

def list_available_dates():
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
```

> 也可以一次性用 `pd.read_parquet(DATA_DIR, engine="pyarrow")` 读整个分区树（pyarrow 会自动识别 Hive 分区并把 year/month/day 加成列），但全量约 87 天 × 5484 行较占内存；做区间分析时优先用 `load_range` 按需读。

## 典型场景

1. "今天首板里 PE 低于 20 的"
   ```python
   df = load_day("20260519")
   df[(df.pattern_first_limit == 1) & (df.pe < 20)].sort_values("pe")
   ```
2. "取最近 30 天面板数据做回测"
   ```python
   panel = load_range("20260420", "20260519")
   ```
3. "看某只股票一段时间的走势"
   ```python
   panel[panel.ts_code == "000001.SZ"].sort_values("trade_date")
   ```

## 能开发哪些功能（给 AI 大模型的开发思路）

下面的能力都基于「`load_range` 拿到的面板数据 + pandas」就能本地实现：

- **形态/因子回测**：取某个 `pattern_*` 或 `break_high_*` 信号当天命中的股票，用次日起 N 日的复权价 `close_qfq` 算前瞻收益（`groupby('ts_code')` 后 shift），统计该信号的胜率、平均收益、收益分布。把多个信号对比，就是信号有效性筛选。
- **多因子选股**：在某交易日截面上，对 `pe/pb/turnover_rate/net_mf_amount/rsi_*` 等列做排序打分或分位数分层（`pd.qcut`），加权合成总分选 topN；逐日滚动即组合回测。
- **行业/板块轮动**：`groupby(['trade_date','industry'])` 聚合 `pct_chg` 均值看板块强弱排名随时间变化；资金流 `net_mf_amount` 同理看主力流向。
- **资金流分析**：用大/特大单 `buy_lg_amount - sell_lg_amount` 构造主力净买入序列，找连续净流入 + 价涨的标的。
- **财务质量筛选**：用 `fin_*` 列（毛利率、净利率、负债率、现金流为正）做基本面过滤，再叠加技术形态做"基本面+技术面"双重选股。
- **连板/涨停梯队**：用 `pattern_first_limit/multi_limit/one_word_limit` + `consec_up_days` 统计每日涨停家数、连板高度、晋级率（昨日首板今日是否继续涨停）。
- **指标交叉验证**：用 `macd`/`kdj`/`rsi`/`boll` 列复算交易信号，与内置 `pattern_golden_cross` 等对照，验证或自定义新信号。

开发时关键约定：算收益用复权价(`*_qfq`/`*_hfq`)；金额单位见上(`amount`元、`total_mv`/`circ_mv`万元、`net_mf_amount`千元)；`pattern_*` 是 0/1，`consec_up_days` 是计数；跨日对齐用 `(ts_code, trade_date)`。

## 注意

- 这是**单日切片逐日落盘**的离线数据，每个 parquet 只含一个交易日；做时序/回测一定要先 `load_range` 拼成面板再 `groupby('ts_code')`，不要在单日 DataFrame 上找时序关系。
- 交易日不连续（含节假日停盘），用 `list_available_dates()` 拿真实交易日，别用自然日序列对齐。
