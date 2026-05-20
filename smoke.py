"""离线冒烟。直接读本地 parquet，无需 token / 网络。

默认数据目录为仓库根的 data/screener_daily/daily/；
如在别处运行，先 export SCREENER_DATA_DIR=/path/to/daily。
"""
import screener_data as d


def main():
    dates = d.list_available_dates()
    print(f"available days: {len(dates)}, range: {dates[0]} ~ {dates[-1]}")

    latest = dates[-1]
    day = d.load_day(latest)
    print(f"day {latest}: {day.shape[0]} rows x {day.shape[1]} cols")

    hit = day[(day.pattern_first_limit == 1) & (day.pe < 20)]
    print(f"  首板且 PE<20: {len(hit)} 只")

    span = dates[-3:] if len(dates) >= 3 else dates
    panel = d.load_range(span[0], span[-1])
    print(f"range {span[0]}~{span[-1]}: {panel.shape[0]} rows, "
          f"{panel.trade_date.nunique()} trade days")


if __name__ == "__main__":
    main()
