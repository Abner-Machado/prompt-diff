#!/usr/bin/env python3
"""
prompt-diff - Compare two versions of an AI agent prompt and estimate token impact.
Line-by-line diff with token cost per change.
Zero dependencies. Python 3.8+.

Usage: python prompt_diff.py old.md new.md [--json] [--context N] [--no-color]
       python prompt_diff.py --version
       python prompt_diff.py --help
"""

import sys
import difflib
import json
from pathlib import Path

VERSION = "1.1.0"
TOKENS_PER_CHAR = 0.25
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

USAGE = (
    "Usage: python prompt_diff.py <old.md> <new.md> [--json] [--context N] "
    "[--no-color]\n"
    "       python prompt_diff.py --version\n"
    "       python prompt_diff.py --help"
)


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text) * TOKENS_PER_CHAR))


def load_file(filepath: str) -> tuple:
    path = Path(filepath)
    if not path.exists():
        return None, f"File not found: {filepath}"
    if not path.is_file():
        return None, f"Not a file: {filepath}"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return None, f"Cannot read {filepath}: {exc}"
    return text.splitlines(), None


def diff_prompts(old_lines, new_lines):
    sm = difflib.SequenceMatcher(None, old_lines, new_lines)
    changes = []
    stats = {"added": 0, "removed": 0, "modified": 0}

    def add_change(kind, old_no, new_no, old_text, new_text, token_delta):
        changes.append({
            "type": kind,
            "old_line": old_no,
            "new_line": new_no,
            "old_text": old_text,
            "new_text": new_text,
            "token_delta": token_delta,
        })
        stats[kind] += 1

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue

        old_block = old_lines[i1:i2]
        new_block = new_lines[j1:j2]

        if tag == "insert":
            for k, line in enumerate(new_block, j1 + 1):
                add_change("added", None, k, None, line.strip()[:120],
                           estimate_tokens(line))
        elif tag == "delete":
            for k, line in enumerate(old_block, i1 + 1):
                add_change("removed", k, None, line.strip()[:120], None,
                           -estimate_tokens(line))
        elif tag == "replace":
            common = min(len(old_block), len(new_block))
            for k in range(common):
                old_line = old_block[k]
                new_line = new_block[k]
                delta = estimate_tokens(new_line) - estimate_tokens(old_line)
                add_change("modified", i1 + k + 1, j1 + k + 1,
                           old_line.strip()[:120], new_line.strip()[:120], delta)
            for k in range(common, len(old_block)):
                add_change("removed", i1 + k + 1, None,
                           old_block[k].strip()[:120], None,
                           -estimate_tokens(old_block[k]))
            for k in range(common, len(new_block)):
                add_change("added", None, j1 + k + 1,
                           None, new_block[k].strip()[:120],
                           estimate_tokens(new_block[k]))

    return changes, stats


def print_diff(changes, old_tokens, new_tokens, old_lines, new_lines, context, no_color):
    red = "" if no_color else RED
    green = "" if no_color else GREEN
    yellow = "" if no_color else YELLOW
    cyan = "" if no_color else CYAN
    bold = "" if no_color else BOLD
    reset = "" if no_color else RESET

    delta = new_tokens - old_tokens
    pct = abs(delta) / max(1, old_tokens) * 100
    sign = "+" if delta >= 0 else ""

    print(f"Old: {old_tokens} tokens -> New: {new_tokens} tokens")
    print(f"Delta: {bold}{sign}{delta} tokens ({sign}{pct:.1f}%){reset}")
    print()

    if not changes:
        print(f"{green}No changes detected.{reset}")
        return

    added_count = sum(1 for c in changes if c["type"] == "added")
    removed_count = sum(1 for c in changes if c["type"] == "removed")
    modified_count = sum(1 for c in changes if c["type"] == "modified")
    print(f"{cyan}--- Changes ({added_count} added, {removed_count} removed, "
          f"{modified_count} modified) ---{reset}")
    print()

    for c in changes:
        if c["type"] == "added":
            if context > 0:
                _print_context("new", new_lines, c["new_line"], context, green, no_color)
            prefix = f"{green}+ L{c['new_line']}"
            detail = f"(+{c['token_delta']} tok)"
            print(f"  {prefix} {detail}{reset}: \"{c['new_text']}\"")
        elif c["type"] == "removed":
            if context > 0:
                _print_context("old", old_lines, c["old_line"], context, red, no_color)
            prefix = f"{red}- L{c['old_line']}"
            detail = f"({c['token_delta']} tok)"
            print(f"  {prefix} {detail}{reset}: \"{c['old_text']}\"")
        elif c["type"] == "modified":
            if context > 0:
                _print_context("old", old_lines, c["old_line"], context, red, no_color)
                _print_context("new", new_lines, c["new_line"], context, green, no_color)
            sign2 = "+" if c["token_delta"] >= 0 else ""
            prefix = f"{yellow}~ L{c['old_line']}"
            detail = f"({sign2}{c['token_delta']} tok)"
            print(f"  {prefix} {detail}{reset}: \"{c['old_text']}\" -> \"{c['new_text']}\"")

    print()
    savings = delta * -1
    cost_usd = savings * 0.000002
    if savings > 0:
        line = f"{green}Saved {savings} tokens.{reset}"
        if cost_usd >= 0.001:
            line += f" {cyan}That's about ${cost_usd:.4f} at GPT-4o pricing.{reset}"
        print(line)
    elif savings < 0:
        print(f"{yellow}Added {abs(savings)} tokens.{reset}")


def _print_context(side, lines, line_no, context, color, no_color):
    if line_no is None:
        return
    reset = "" if no_color else RESET
    start = max(0, line_no - 1 - context)
    end = min(len(lines), line_no - 1 + context + 1)
    for idx in range(start, end):
        print(f"    {color}{side} L{idx + 1}: {lines[idx].strip()[:80]}{reset}")


def parse_args(argv):
    """Return (files, options) or raise ValueError with a user-facing message."""
    files = []
    opts = {"json": False, "no_color": False, "context": 2}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--json",):
            opts["json"] = True
            i += 1
        elif arg in ("--no-color", "--no-colour"):
            opts["no_color"] = True
            i += 1
        elif arg == "--context" or arg.startswith("--context="):
            if arg.startswith("--context="):
                raw = arg.split("=", 1)[1]
                i += 1
            else:
                if i + 1 >= len(argv):
                    raise ValueError("--context requires a value")
                raw = argv[i + 1]
                i += 2
            try:
                value = int(raw)
            except ValueError:
                raise ValueError(f"invalid --context value: {raw}")
            if value < 0:
                raise ValueError(f"invalid --context value: {raw} (must be >= 0)")
            opts["context"] = value
        elif arg.startswith("-"):
            raise ValueError(f"unknown option: {arg}")
        else:
            files.append(arg)
            i += 1
    return files, opts


def main():
    argv = sys.argv[1:]

    if "--version" in argv:
        print(f"prompt-diff v{VERSION}")
        return 0
    if "--help" in argv or "-h" in argv:
        print(USAGE)
        return 0

    try:
        files, opts = parse_args(argv)
    except ValueError as exc:
        print(f"prompt-diff: error: {exc}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2

    if len(files) != 2:
        print(USAGE, file=sys.stderr)
        return 2

    old_path, new_path = files
    as_json = opts["json"]
    no_color = opts["no_color"]
    context = opts["context"]

    old_lines, err = load_file(old_path)
    if err:
        print(err, file=sys.stderr)
        return 1

    new_lines, err = load_file(new_path)
    if err:
        print(err, file=sys.stderr)
        return 1

    old_text = "\n".join(old_lines)
    new_text = "\n".join(new_lines)
    old_tokens = estimate_tokens(old_text)
    new_tokens = estimate_tokens(new_text)

    changes, stats = diff_prompts(old_lines, new_lines)

    if as_json:
        result = {
            "version": VERSION,
            "old_file": old_path,
            "new_file": new_path,
            "old_tokens": old_tokens,
            "new_tokens": new_tokens,
            "token_delta": new_tokens - old_tokens,
            "change_pct": round(abs(new_tokens - old_tokens) / max(1, old_tokens) * 100, 1),
            "stats": stats,
            "changes": changes,
        }
        print(json.dumps(result, indent=2))
    else:
        print_diff(changes, old_tokens, new_tokens, old_lines, new_lines, context, no_color)

    return 0


if __name__ == "__main__":
    sys.exit(main())
