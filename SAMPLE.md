# Sample Markdown file — probability case studies

This file demonstrates the linter tag syntax on four famous probability-fallacy cases.  

Lint with:

```bash
python linter.py -f SAMPLE.md
```

Expected output:

```
SAMPLE.md:39:1: info: block 'sally-clark': P(~m | d) = 0.900000
SAMPLE.md:91:1: info: block 'mammography': P(c | t) = 0.077640
```

---

## Sally Clark (UK, 1999)

Roy Meadow argued that two SIDS deaths in one family had probability **1 in 73 million** (squaring 1/8500 and assuming independence). The prosecution treated this as `P(innocent | two deaths) ≈ 1/73,000,000`.

<block id="sally-clark" />

<symbol name="d">Two infants are dead.</symbol>

Evaluating if the <symbol name="m">mother is a murderess</symbol>.

<constraint expr="~(~d & m)" />

<prob target="m" value="0.0001" />

<prob target="d" value="0.001" />

<query target="~m" given="d" />

---

## Mammography screening (Eddy, 1982)

With 1% prevalence, 80% sensitivity, and 9.6% false-positive rate, physicians often estimate `P(cancer | positive test) ≈ 80%` instead of the correct **~7.8%** — a classic base-rate neglect problem.

<block id="mammography" />

<symbol name="c">The patient has breast cancer.</symbol>
<symbol name="t">The mammogram is positive.</symbol>

<prob target="c" value="0.01" />
<prob target="t" given="c" value="0.80" />
<prob target="t" given="~c" value="0.096" />

<query target="t" given="c" />
<query target="c" given="t" />
