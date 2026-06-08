# MarkdownLinter

A linter for Markdown documents that validates probability and logic definitions. The project explores integrating formal probability reasoning (via the [ProbabilityIter](https://github.com/kacpertopolnicki/ProbabilityIter) library) into natural-language documents written in Markdown.

## What it does

The linter scans Markdown files for custom XML-like tags that define logical statements, constraints, probability assignments, and queries. It runs two passes:

1. **Syntactic** — required attributes present and non-empty.
2. **Semantic** — SymPy expressions parse correctly, probability values are in `[0, 1]`, the linear system is consistent, and `<query>` tags return computed results.

Results are available in two modes:

- **CLI** — prints diagnostics in GCC-style format (`file:line:col: severity: message`), useful for CI/CD.
- **LSP Server** — provides real-time diagnostics in editors that support the Language Server Protocol (e.g., VS Code, PyCharm, Neovim).

## Markdown syntax

The linter recognizes five custom tags. Logic expressions use [SymPy](https://www.sympy.org/) syntax (e.g. `~`, `&`, `|`). Formal tags are **self-closing**; only `<symbol>` has a visible prose body.

| Tag | Required | Optional | Purpose |
|-----|----------|----------|---------|
| `<block>` | — | `id` | Starts a new probability system. Must be self-closing. Tags before the first `<block />` share one implicit `default` block. |
| `<symbol>` | `name` | — | Optional documentation for a logical symbol. Body is human-readable prose. |
| `<constraint>` | `expr` | — | Logical constraint (SymPy), e.g. `<constraint expr="~(~d & m)" />`. |
| `<prob>` | `target`, `value` | `given` (default `True`) | Declare `P(target \| given) = value`. |
| `<query>` | `target` | `given` (default `True`) | Compute `P(target \| given)`; emits an `info` diagnostic after solving. |

### Example

See `SAMPLE.md` for a full [Sally Clark case](https://en.wikipedia.org/wiki/Sally_Clark) example. Minimal document:

```markdown
<block id="sally-clark" />

<symbol name="d">Two infants are dead.</symbol>
<symbol name="m">The mother is a murderer.</symbol>

<constraint expr="~(~d & m)" />

<prob target="m" value="0.0001" />
<prob target="d" value="0.001" />

<query target="~m" given="d" />
```

Running `python linter.py -f SAMPLE.md` outputs an `info` diagnostic with the computed query:

```
SAMPLE.md:27:1: info: block 'sally-clark': P(~m | d) = 0.900000
```

Syntax problems use `error` severity; successfully computed queries use `info`. A file with a missing attribute might report:

```
example.md:1:1: error: Missing required attribute 'name'
```

## Installation

> ⚠️ `requirements.txt` is encoded as **UTF-16LE with BOM**, which standard text editors may garble. `pip` can still read it correctly.

> ⚠️ `requirements.txt` references `ProbabilityIter` as an editable install from a sibling directory (`../ProbabilityIter/`). Clone that repository next to this one before installing.

```bash
# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies (includes ProbabilityIter if ../ProbabilityIter exists)
pip install -r requirements.txt

# If ProbabilityIter was not installed automatically:
pip install -e ../ProbabilityIter
```

## Usage

### CLI mode

Lint a single Markdown file:

```bash
python linter.py -f SAMPLE.md
```

Enable debug logging:

```bash
python linter.py -f SAMPLE.md -debug
```

### LSP mode

Start the Language Server Protocol server (uses stdio):

```bash
python linter.py -lsp
# or directly:
python lsp.py
```

Hover over a line with diagnostics to see messages in editors that support `textDocument/hover` (e.g. Neovim).

## Architecture

| File | Role |
|------|------|
| `linter.py` | CLI entrypoint. Runs `tokenize` → `lint` → `lint_semantic`; prints GCC-formatted output. |
| `lsp.py` | LSP server using `pygls`. Publishes diagnostics on `didOpen` / `didChange`. |
| `src/tokenizer.py` | Regex-based tokenizer for `<symbol>`, `<constraint>`, `<prob>`, and `<query>` (paired and self-closing). |
| `src/token_parser.py` | Syntactic validation of required attributes. |
| `src/scope_manager.py` | Splits tokens into `ProbabilityBlock` groups using `<block />` anchors. |
| `src/semantic_parser.py` | Validates each block via `PiterInterface`, emits semantic and query diagnostics. |
| `src/PiterInterface.py` | Bridge to the ProbabilityIter engine. Parses SymPy logic, solves `Ax = b`, answers queries. |

Pipeline:

```
Markdown → tokenizer → token_parser (syntax) → semantic_parser (Piter) → LintError → CLI / LSP
```

See `IMPLEMENTATION_PLAN.md` for the development roadmap and `CODEBASE_REVIEW.md` for a codebase assessment.

## ProbabilityIter library

The [ProbabilityIter](https://github.com/kacpertopolnicki/ProbabilityIter) library is maintained in a sibling repository (`../ProbabilityIter/`). It contains a standalone probability engine (`piter/piter.py`) that:

1. Takes SymPy logical symbols and constraints.
2. Generates all possible base elements (conjunctions of symbols, e.g., `d & ~m`).
3. Builds a linear system `Ax = b` from declared probabilities.
4. Solves the system with NumPy.
5. Answers queries of the form `P(target | condition)`.

The library includes unit tests in `../ProbabilityIter/tests/test.py`. See also `../ProbabilityIter/examples/example_constraints.py` and `example_constraints.py` in this repo for the Sally Clark setup.

## Testing

Run the full test suite:

```bash
python -m unittest test.tests test.test_piter_interface
```

Tests cover syntactic linting, semantic integration (contradictions, out-of-range probabilities, invalid SymPy), and `PiterInterface` behavior.

## License

See [LICENSE](LICENSE).
