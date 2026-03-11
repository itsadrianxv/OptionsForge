from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行组合策略回测")
    parser.add_argument("--config", type=str, default=None, help="策略配置文件路径")
    parser.add_argument("--start", type=str, default=None, help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default=None, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--capital", type=int, default=None, help="初始资金")
    parser.add_argument("--rate", type=float, default=None, help="手续费率")
    parser.add_argument("--slippage", type=float, default=None, help="滑点")
    parser.add_argument("--size", type=int, default=None, help="合约乘数")
    parser.add_argument("--pricetick", type=float, default=None, help="最小价格变动")
    parser.add_argument(
        "--no-chart",
        action="store_true",
        default=None,
        dest="no_chart",
        help="不显示图表",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def execute(args: argparse.Namespace) -> dict[str, object]:
    from dotenv import load_dotenv

    from src.backtesting.config import BacktestConfig
    from src.backtesting.runner import BacktestRunner
    from src.main.bootstrap.database_factory import DatabaseFactory

    config = BacktestConfig.from_args(args)
    load_dotenv()

    factory = DatabaseFactory.get_instance()
    factory.initialize(eager=True)

    runner = BacktestRunner(config)
    return runner.run()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    execute(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
