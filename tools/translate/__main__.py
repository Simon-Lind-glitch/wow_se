"""Stage 2 entry point: `python -m translate`.

Needs no API key and no network. Two commands:

    python -m translate --export-pending out.json   # what still needs doing
    python -m translate --import-file  out.json     # read it back, validated
"""

import argparse
import sys

from translate import exchange


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="translate", description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--export-pending", metavar="FILE", help="write untranslated strings to FILE"
    )
    group.add_argument("--import-file", metavar="FILE", help="read translations back from FILE")
    group.add_argument(
        "--status", action="store_true", help="report how much is translated and stop"
    )
    parser.add_argument("--limit", type=int, help="export at most N strings")
    parser.add_argument(
        "--field", help="restrict export to a field, e.g. quest or quest.objectives"
    )
    parser.add_argument(
        "--translator",
        default="manual",
        help="provenance recorded against imported entries (default: manual)",
    )
    args = parser.parse_args(argv)

    units = exchange.load_units()
    entries = exchange.load_translations()

    if args.status:
        done = sum(len(v) for v in entries.values())
        by_field: dict[str, list[int]] = {}
        for unit in units:
            slot = by_field.setdefault(unit.field, [0, 0])
            slot[1] += 1
            if unit.key in entries.get(unit.field, {}):
                slot[0] += 1
        print(f"{done} of {len(units)} strings translated")
        for name in sorted(by_field):
            got, total = by_field[name]
            print(f"  {name:20} {got:>5} / {total}")
        return 0

    if args.export_pending:
        count = exchange.export_pending(
            args.export_pending, limit=args.limit, field_prefix=args.field
        )
        print(f"exported {count} pending string(s) to {args.export_pending}")
        return 0

    exchange.import_file(args.import_file, translator=args.translator)
    return 0


if __name__ == "__main__":
    sys.exit(main())
