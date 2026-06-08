# Sample Markdown file — Sally Clark case

This file demonstrates the linter tag syntax. Lint with:

```bash
python linter.py -f SAMPLE.md
```

Expected output:

```
SAMPLE.md:25:1: info: P(~m | d) = 0.900000
```

<symbol name="d">Two infants are dead.</symbol>

Evaluating if the <symbol name="m">mother is a murderer</symbol>.

<constraint expr="~(~d & m)" />

<prob target="m" value="0.0001" />

<prob target="d" value="0.001" />

<query target="~m" given="d" />
