import argparse
import json

from etf_pressure.pipeline import restore, run, snapshot


def main():
    parser = argparse.ArgumentParser(description="ETF Pressure Lab research pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("run")
    command.add_argument("--mode", choices=["download", "cached"], default="cached")
    command.add_argument("--start", default="2021-01-01")
    command.add_argument("--end", default=None, help="Exclusive YYYY-MM-DD; defaults to tomorrow")
    command.add_argument("--data-dir", default="data")
    command.add_argument("--output", default="artifacts")
    command = sub.add_parser("snapshot")
    command.add_argument("--destination", default="artifacts/research-snapshot.zip")
    command = sub.add_parser("restore")
    command.add_argument("source")
    command = sub.add_parser(
        "publish-report", help="Export derived dashboard evidence for zero-setup hosting"
    )
    command.add_argument("--artifacts", default="artifacts")
    command.add_argument("--destination", default="reports/dashboard.json")
    args = vars(parser.parse_args())
    operation = args.pop("command")
    if operation == "run":
        print(json.dumps(run(**args), indent=2))
    elif operation == "snapshot":
        print(snapshot(**args))
    elif operation == "publish-report":
        from etf_pressure.dashboard import publish_report

        print(publish_report(**args))
    else:
        restore(**args)


if __name__ == "__main__":
    main()
