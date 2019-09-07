import os
from itertools import repeat


def log_initial(*, debug, config_files, db_name, LOG_DIR, plugins):
    from byro.common.console import start_box, end_box, print_line
    from byro import __version__

    if hasattr(os, "geteuid") and os.geteuid() == 0:
        print_line("You are running byro as root, why?", bold=True)

    mode = "development" if debug else "production"
    lines = [
        (
            "This is byro v{__version__} calling, running in {mode} mode.".format(
                __version__=__version__, mode=mode
            ),
            True,
        ),
        ("", False),
        ("Settings:", True),
        ("Read from: " + ", ".join(config_files), False),
        ("Logging:   {LOG_DIR}".format(LOG_DIR=LOG_DIR), False),
    ]
    if plugins:
        lines += [("Plugins:   " + ",".join(plugins), False)]
    else:
        lines += [("", False)]
    image = """
┏━o━━━━o━━━┓
┣━━━o━━━o━━┫
┣━━━━━━━━━━┫
┃   byro   ┃
┗━━━━━━━━━━┛
    """.strip().split(
        "\n"
    )
    img_width = len(image[0])
    image[-1] += " " * (img_width - len(image[-1]))
    image += [" " * img_width for _ in repeat(None, (len(lines) - len(image)))]

    lines = [(image[n] + " " + line[0], line[1]) for n, line in enumerate(lines)]

    size = max(len(line[0]) for line in lines) + 4
    start_box(size)
    for line in lines:
        print_line(line[0], box=True, bold=line[1], size=size)
    end_box(size)


def reduce_dict(data):
    return {
        section_name: {
            key: value for key, value in section_content.items() if value is not None
        }
        for section_name, section_content in data.items()
    }
