"""crypto-trading-agents-skill CLI。

子命令：
    analyze <ticker>            完整三 agent 分析
    fetch <ticker>              拉当前价 + 24h 数据（CoinGecko）
    list-models                 列已配置的 LLM backend

示例：

    python __main__.py analyze BTC --days 90 --headlines headlines.txt
    python __main__.py analyze ETH --synthetic  # 不联网 demo
    python __main__.py fetch SOL
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _read_headlines(path: Optional[str]) -> List[str]:
    if not path:
        return []
    lines = [l.strip() for l in Path(path).read_text(encoding="utf-8").splitlines()]
    return [l for l in lines if l]


def cmd_analyze(args) -> int:
    from scripts.data_fetch import (
        MarketSnapshot, fetch_ohlcv_coingecko,
        fetch_recent_market_data, synthetic_ohlcv,
    )
    from scripts.llm_client import LLMClient
    from scripts.orchestrator import Orchestrator, render_markdown

    if args.synthetic:
        df = synthetic_ohlcv(n_days=args.days)
        source = "synthetic"
        current = df["price"].iloc[-1]
    else:
        try:
            df = fetch_ohlcv_coingecko(args.ticker, days=args.days)
            snap: MarketSnapshot = fetch_recent_market_data(args.ticker)
            source = f"coingecko:{snap.coin_id}"
            current = snap.current_price
            # 用最新价覆盖最后一行收盘价（CoinGecko market_chart 数据稍滞后）
            if len(df):
                df.iloc[-1, df.columns.get_loc("price")] = current
        except Exception as e:
            sys.stderr.write(f"[error] 数据获取失败：{e}\n")
            sys.stderr.write("[hint] 加 --synthetic 用合成数据 demo\n")
            return 2

    headlines = _read_headlines(args.headlines)

    llm = LLMClient(backend=args.backend) if args.use_llm else None
    if args.use_llm and llm and not llm.is_available():
        sys.stderr.write(
            f"[warn] --use-llm 指定了 {args.backend}，但环境变量未配，"
            "情绪 agent 会退化为关键词字典法\n"
        )

    orch = Orchestrator(llm_client=llm)
    report = orch.analyze(
        ticker=args.ticker.upper(),
        prices=df["price"],
        headlines=headlines,
        sentiment_weight=args.sentiment_weight,
        data_source=source,
    )

    if args.output_format == "json":
        out = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    else:
        out = render_markdown(report)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(out, encoding="utf-8")
        sys.stderr.write(f"[ok] 写入 {args.output}\n")
    else:
        print(out)
    return 0


def cmd_fetch(args) -> int:
    from scripts.data_fetch import fetch_recent_market_data
    try:
        snap = fetch_recent_market_data(args.ticker)
    except Exception as e:
        sys.stderr.write(f"[error] {e}\n")
        return 2
    print(json.dumps(snap.to_dict(), ensure_ascii=False, indent=2))
    return 0


def cmd_list_models(args) -> int:
    import os
    rows = [
        ("openai", "gpt-4o-mini", "OPENAI_API_KEY"),
        ("anthropic", "claude-3-5-haiku-20241022", "ANTHROPIC_API_KEY"),
        ("deepseek", "deepseek-chat", "DEEPSEEK_API_KEY"),
    ]
    print(f"{'backend':<12} {'default model':<32} {'env var':<20} configured")
    print("-" * 80)
    for b, m, e in rows:
        cfg = "yes" if os.getenv(e) else "no"
        print(f"{b:<12} {m:<32} {e:<20} {cfg}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="crypto-agents",
        description="加密多 agent 分析：技术 + 情绪（LLM）+ 风控"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("analyze", help="跑完整三 agent 分析")
    sp.add_argument("ticker", help="如 BTC / ETH / SOL")
    sp.add_argument("--days", type=int, default=90, help="历史数据天数")
    sp.add_argument("--headlines", help="新闻文件，每行一条；不传则情绪 agent 不出力")
    sp.add_argument("--use-llm", action="store_true", help="情绪 agent 用 LLM 而非关键词")
    sp.add_argument("--backend", default="deepseek", choices=["openai", "anthropic", "deepseek"])
    sp.add_argument("--sentiment-weight", type=float, default=0.4,
                    help="情绪 agent 在最终决策中的权重（0-1）")
    sp.add_argument("--output-format", default="markdown", choices=["markdown", "json"])
    sp.add_argument("--synthetic", action="store_true",
                    help="用合成数据（无网络场景 demo）")
    sp.add_argument("-o", "--output", help="结果写到文件")
    sp.set_defaults(func=cmd_analyze)

    sp = sub.add_parser("fetch", help="从 CoinGecko 拉当前价 + 24h 数据")
    sp.add_argument("ticker")
    sp.set_defaults(func=cmd_fetch)

    sp = sub.add_parser("list-models", help="列 LLM backend 配置状态")
    sp.set_defaults(func=cmd_list_models)

    return p


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
