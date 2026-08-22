"""Stage 2 entry point: `python -m translate`.

Needs ANTHROPIC_API_KEY, unless --dry-run. Every other stage runs without it.
"""

import argparse
import sys

import anthropic

from translate import batch as batching
from translate import runner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="translate", description=__doc__)
    parser.add_argument(
        "--model",
        default=batching.DEFAULT_MODEL,
        help=f"model to translate with (default: {batching.DEFAULT_MODEL}, the cheapest capable)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="translate at most N strings — use this to sample quality before a full run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be sent and the estimated cost, then stop",
    )
    parser.add_argument(
        "--remodel",
        action="store_true",
        help="also re-translate strings cached from a different model (quality upgrade pass)",
    )
    parser.add_argument(
        "--export-pending",
        metavar="FILE",
        help="write pending strings to FILE for translation without an API key, then stop",
    )
    parser.add_argument(
        "--import-file",
        metavar="FILE",
        help="load translations from FILE (validated exactly as API output is), then stop",
    )
    parser.add_argument(
        "--translator",
        default="manual",
        help="provenance recorded for --import-file entries (default: manual)",
    )
    parser.add_argument(
        "--field",
        help="restrict --export-pending to one field, e.g. quest.objectives",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=1,
        help="rounds of single-string retries for rejected placeholders (default: 1)",
    )
    args = parser.parse_args(argv)

    if args.model not in batching.PRICES:
        print(
            f"warning: unknown model {args.model!r}; cost estimates will use "
            f"{batching.DEFAULT_MODEL} prices",
            file=sys.stderr,
        )

    if args.export_pending:
        count = runner.export_pending(
            args.export_pending,
            model=args.model,
            limit=args.limit,
            field=args.field,
            remodel=args.remodel,
        )
        print(f"exported {count} pending string(s) to {args.export_pending}")
        return 0

    if args.import_file:
        runner.import_file(args.import_file, translator=args.translator)
        return 0

    try:
        runner.run(
            model=args.model,
            limit=args.limit,
            remodel=args.remodel,
            dry_run=args.dry_run,
            retries=args.retries,
        )
    except anthropic.AuthenticationError:
        print(
            "ANTHROPIC_API_KEY is missing or invalid.\n"
            "Export it on the host before opening the container; only this stage needs it.\n"
            "Run with --dry-run to see the plan and cost without a key.",
            file=sys.stderr,
        )
        return 1
    except anthropic.RateLimitError as exc:
        print(f"rate limited: {exc}", file=sys.stderr)
        return 1
    except anthropic.APIStatusError as exc:
        print(f"API error {exc.status_code}: {exc.message}", file=sys.stderr)
        return 1
    except anthropic.APIConnectionError:
        print("could not reach the API; check the container's network", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
