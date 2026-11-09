#!/usr/bin/env python3
"""
prompt-diff — Compare two versions of an AI agent prompt and estimate token impact.
Line-by-line diff with token cost per change.
Zero dependencies. Python 3.8+.

Usage: python prompt_diff.py old.md new.md [--json] [--context N] [--no-color]
"""

import sys
import difflib
import json
from pathlib import Path

TOKENS_PER_CHAR = 0.25
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text) * TOKENS_PER_CHAR))


def load_file(filepath: str) -> tuple:
    path = Path(filepath)
    if not path.exists():
        return None, f"File not found: {filepath}"
    text = path.read_text(encoding="utf-8", errors="replace")
    return text.splitlines(), None


def diff_prompts(old_lines, new_lines, context=2, no_color=False):
    red = "" if no_color else RED
    green = "" if no_color else GREEN
    yellow = "" if no_color else YELLOW
    cyan = "" if no_color else CYAN
    bold = "" if no_color else BOLD
    reset = "" if no_color else RESET

    sm = difflib.SequenceMatcher(None, old_lines, new_lines)
    changes = []
    stats = {"added": 0, "removed": 0, "modified": 0}

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue

        old_block = old_lines[i1:i2]
        new_block = new_lines[j1:j2]

        for line_num, line in enumerate(old_block, i1 + 1):
            tk = estimate_tokens(line)
            changes.append({
                "type": "removed",
                "old_line": line_num,
                "new_line": None,
                "old_text": line.strip()[:120],
                "new_text": None,
                "token_delta": -tk
            })
            stats["removed"] += 1

        for line_num, line in enumerate(new_block, j1 + 1):
            tk = estimate_tokens(line)
            changes.append({
                "type": "added",
                "old_line": None,
                "new_line": line_num,
                "old_text": None,
                "new_text": line.strip()[:120],
                "token_delta": tk
            })
            stats["added"] += 1

    return changes, stats


def print_diff(changes, old_tokens, new_tokens, context, no_color):
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

    print(f"{cyan}--- Changes ({added_count} added, {removed_count} removed) ---{reset}")
    print()

    for c in changes:
        if c["type"] == "added":
            prefix = f"{green}+ L{c['new_line']}"
            detail = f"(+{c['token_delta']} tok)"
            print(f"  {prefix} {detail}{reset}: \"{c['new_text']}\"")
        elif c["type"] == "removed":
            prefix = f"{red}- L{c['old_line']}"
            detail = f"({c['token_delta']} tok)"
            print(f"  {prefix} {detail}{reset}: \"{c['old_text']}\"")

    print()
    savings = delta * -1
    if savings > 0:
        print(f"{green}Saved {savings} tokens. {cyan}That's about ${savings * 0.000002:.4f} at GPT-4o pricing.{reset}")
    elif savings < 0:
        print(f"{yellow}Added {abs(savings)} tokens.{reset}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    if len(args) < 2:
        print("Usage: python prompt_diff.py <old.md> <new.md> [--json] [--context N] [--no-color]")
        sys.exit(1)

    old_path, new_path = args[0], args[1]
    as_json = "--json" in flags
    no_color = "--no-color" in flags
    context = 2
    for i, f in enumerate(flags):
        if f == "--context" and i + 1 < len(flags):
            try:
                context = int(flags[i + 1])
            except ValueError:
                pass

    old_lines, err = load_file(old_path)
    if err:
        print(err, file=sys.stderr)
        sys.exit(1)

    new_lines, err = load_file(new_path)
    if err:
        print(err, file=sys.stderr)
        sys.exit(1)

    old_text = "\n".join(old_lines)
    new_text = "\n".join(new_lines)
    old_tokens = estimate_tokens(old_text)
    new_tokens = estimate_tokens(new_text)

    changes, stats = diff_prompts(old_lines, new_lines, context, no_color)

    if as_json:
        result = {
            "old_file": old_path,
            "new_file": new_path,
            "old_tokens": old_tokens,
            "new_tokens": new_tokens,
            "token_delta": new_tokens - old_tokens,
            "change_pct": round(abs(new_tokens - old_tokens) / max(1, old_tokens) * 100, 1),
            "stats": stats,
            "changes": changes
        }
        print(json.dumps(result, indent=2))
    else:
        print_diff(changes, old_tokens, new_tokens, context, no_color)

    sys.exit(0)


if __name__ == "__main__":
    main()