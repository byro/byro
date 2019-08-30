import re
import sys

import canonicaljson
from django.core.management.base import BaseCommand

from byro.common.models.log import LogEntry


class Command(BaseCommand):
    help = "Export the log-chain in JSON format"

    def add_arguments(self, parser):
        parser.add_argument(
            "-a",
            "--data-include-actions",
            default=r"^.*$",
            type=str,
            help="action_types for which to include the log 'data' member (Regex)",
        )
        parser.add_argument(
            "-A",
            "--data-exclude-actions",
            default=None,
            type=str,
            help="action_types for which to exclude the log 'data' member (Regex)",
        )

    def handle(self, *args, **options):
        include_re = re.compile(options["data_include_actions"])
        exclude_re = (
            re.compile(options["data_exclude_actions"])
            if options["data_exclude_actions"]
            else None
        )

        outstream = sys.stdout

        outstream.write("[")
        is_first = True
        last = None
        current = LogEntry.objects.get_chain_end()

        while current and current != last:
            data = {
                "hash": current.auth_hash,
                "entry": current.get_authenticated_dict(),
            }

            if include_re.search(current.action_type) and (
                exclude_re is None or not exclude_re.search(current.action_type)
            ):
                data["data"] = current.data

            data_pretty = canonicaljson.encode_pretty_printed_json(data).decode("utf-8")

            if not is_first:
                outstream.write(",\n    ")
            else:
                outstream.write("\n    ")

            outstream.write("\n    ".join(data_pretty.split("\n")))

            is_first = False
            last = current
            current = current.auth_prev

        outstream.write("\n]\n")
