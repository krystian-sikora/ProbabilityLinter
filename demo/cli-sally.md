<!--suppress HtmlUnknownTag -->

# CLI demo — Sally Clark (ten sam model co query-example)

Uruchomienie (z katalogu MarkdownLinter):

```bash
python linter.py -f demo/cli-sally.md
```

Oczekiwany wynik (jedna linia info):

```
demo/cli-sally.md:25:1: info: block 'sally-clark': P(~m | d) = 0.900000
```

---

<block id="sally-clark" />

<symbol name="d">Two infants are dead.</symbol>
Evaluating if the <symbol name="m">mother is a murderess</symbol>.

<constraint expr="~(~d & m)" />
<prob target="m" value="0.0001" />
<prob target="d" value="0.001" />
<query target="~m" given="d" />
