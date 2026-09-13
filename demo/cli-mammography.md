# CLI / e2e demo — mammography (Eddy, base-rate neglect)

Prevalence 1%, sensitivity 80%, false-positive rate 9.6%.
Physicians often confuse P(t | c) ≈ 80% with P(c | t).

```bash
python linter.py -f demo/cli-mammography.md
```

Expected:

```
demo/cli-mammography.md:28:1: info: block 'mammography': P(t | c) = 0.800000
demo/cli-mammography.md:29:1: info: block 'mammography': P(c | t) = 0.077640
```

---

<block id="mammography" />

<symbol name="c">The patient has breast cancer.</symbol>
<symbol name="t">The mammogram is positive.</symbol>

<prob target="c" value="0.01" />
<prob target="t" given="c" value="0.80" />
<prob target="t" given="~c" value="0.096" />

<query target="t" given="c" />
<query target="c" given="t" />
