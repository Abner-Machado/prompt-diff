# prompt-diff

Compare two versions of an AI agent prompt and see exactly what changed — with token impact estimates.

**Zero dependencies.** Python 3.8+, no pip install.

## Why

When you iterate on agent prompts, you need to know: did this edit save tokens or burn them? prompt-diff shows line-by-line changes with token cost per change.

## Usage

```bash
python prompt_diff.py old_prompt.md new_prompt.md
python prompt_diff.py old.md new.md --json
python prompt_diff.py old.md new.md --context 3
```

## Example

```
prompt-diff v1.0.0
old.md (3240 tokens) -> new.md (2891 tokens)
Delta: -349 tokens (-10.8%)

--- Changes ---
+ L12 (+12 tok): "You must validate all inputs before processing."
- L8  (-45 tok): "Please feel free to let me know if you have any questions..."
~ L23 (-8 tok):  "Use declarative instructions only." -> "Use declarative style."
```

## Options

| Flag | Description |
|------|-------------|
| `--json` | Machine-readable JSON output |
| `--context N` | Show N lines around each change |
| `--no-color` | Disable ANSI colors |

## License

MIT