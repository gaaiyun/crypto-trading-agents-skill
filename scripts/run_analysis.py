"""legacy 入口：转发到 ``python __main__.py analyze <ticker>``。

旧版本依赖一个不在本仓库的 external/CryptoTradingAgents/cli 路径，无法工作。
新流程直接调顶层 ``__main__.py analyze``。这个文件保留只为不破坏老调用。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    # 把 sys.argv 转发：scripts/run_analysis.py --ticker BTC -> __main__.py analyze BTC
    args = sys.argv[1:]
    # 简单兼容：把 --ticker X 拿出来当位置参数
    ticker = None
    new_args = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--ticker", "-t") and i + 1 < len(args):
            ticker = args[i + 1]
            i += 2
            continue
        if a in ("--output", "-o") and i + 1 < len(args):
            new_args.extend(["-o", args[i + 1]])
            i += 2
            continue
        # 其他参数原样透传
        new_args.append(a)
        i += 1

    if ticker is None:
        sys.stderr.write("[error] 需要 --ticker BTC 或位置参数\n")
        sys.stderr.write("[hint] 新接口：python __main__.py analyze BTC\n")
        return 1

    import importlib.util
    cli_path = Path(__file__).resolve().parent.parent / "__main__.py"
    spec = importlib.util.spec_from_file_location("crypto_cli", cli_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main(["analyze", ticker, *new_args])


if __name__ == "__main__":
    sys.exit(main())
