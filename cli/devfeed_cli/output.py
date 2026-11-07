"""Prints tables and detail lines for the terminal.

Text from the API (titles, notes, tags) is cleaned before printing, so a
title containing terminal control characters can't change the terminal.
"""

import shutil
import unicodedata

FALLBACK_TERMINAL_COLUMNS = 100
COLUMN_GAP = "  "


def clean_text(text):
    """Replace control characters (escape codes, newlines, tabs) with spaces."""
    if text is None:
        return ""
    return "".join(
        " " if unicodedata.category(character) == "Cc" else character
        for character in str(text)
    )


def format_date(iso_timestamp):
    """Turn "2026-11-03T14:05:00Z" into "2026-11-03"; "-" when missing."""
    if not iso_timestamp:
        return "-"
    return str(iso_timestamp)[:10]


def shorten(text, maximum_width):
    """Cut text to maximum_width characters, ending in "…" when cut."""
    if maximum_width <= 0:
        return ""
    if len(text) <= maximum_width:
        return text
    if maximum_width == 1:
        return "…"
    return text[: maximum_width - 1] + "…"


def print_table(column_headers, rows):
    """Print aligned columns; the last column is shortened to fit the terminal."""
    cleaned_rows = [[clean_text(cell) for cell in row] for row in rows]
    all_rows = [list(column_headers)] + cleaned_rows

    # Width of every column except the last, from its longest cell
    fixed_column_widths = [
        max(len(row[column_index]) for row in all_rows)
        for column_index in range(len(column_headers) - 1)
    ]
    terminal_columns = shutil.get_terminal_size((FALLBACK_TERMINAL_COLUMNS, 24)).columns
    used_width = sum(fixed_column_widths) + len(COLUMN_GAP) * len(fixed_column_widths)
    # Keep at least 10 characters for the last column on narrow terminals
    last_column_width = max(terminal_columns - used_width, 10)

    for row in all_rows:
        padded_cells = [
            row[column_index].ljust(fixed_column_widths[column_index])
            for column_index in range(len(fixed_column_widths))
        ]
        padded_cells.append(shorten(row[-1], last_column_width))
        print(COLUMN_GAP.join(padded_cells).rstrip())


def print_details(labeled_values):
    """Print "Label:  value" lines with the labels aligned."""
    label_width = max(len(label) for label, _ in labeled_values) + 1
    for label, value in labeled_values:
        print(f"{(label + ':').ljust(label_width)}  {clean_text(value)}")
