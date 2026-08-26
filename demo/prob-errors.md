# error -- brak target
<block id="missing-target" />
<prob value="0.0001" />

# error -- brak value
<block id="missing-value" />
<prob target="c" />

# error -- value nie jest liczbą
<block id="non-numeric" />
<prob target="a" value="2x" />

# error -- value poza [0, 1]
<block id="out-of-range" />
<prob target="b" value="2" />

# error -- nieparsowalne target
<block id="parse-target" />
<prob target="c &&& d" value="0.5" />

# error -- nieparsowalne given
<block id="parse-given" />
<prob target="e" value="0.5" given="f &" />

# warning -- value równe 0
<block id="value-zero" />
<prob target="zero" value="0" />

# warning -- value równe 1
<block id="value-one" />
<prob target="one" value="1" />

# warning -- duplikat P(target | given)
<block id="duplicate-prob" />
<prob target="duplicate" value="0.1" />
<prob target="duplicate" value="0.1" />

# error -- układ sprzeczny (przy solve)
<block id="contradictory" />
<prob target="d" value="0.5" />
<prob target="d" value="0.9" />

# poprawne (bez diagnostyki na samym prob)
<block id="ok" />
<prob target="valid" value="0.9" />
