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


Two infants are dead.

Evaluating if the mother is a murderess.





---

## Mammography screening (Eddy, 1982)

With 1% prevalence, 80% sensitivity, and 9.6% false-positive rate, physicians often estimate `P(cancer | positive test) ≈ 80%` instead of the correct **~7.8%** — a classic base-rate neglect problem.


The patient has breast cancer.
The mammogram is positive.


