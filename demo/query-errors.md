# error -- brak target
<query />

# warning -- Query skipped: probability block was not solved
<block id="skipped" />
<query target="a" />

# warning -- Query skipped (blok sprzeczny, solve nieudany)
<block id="after-contradiction" />
<prob target="d" value="0.5" />
<prob target="d" value="0.9" />
<query target="d" />

# error -- nieparsowalne wyrażenie (target)
<block id="parse-target" />
<prob target="d" value="0.5" />
<query target="d &" />

# error -- nieparsowalne wyrażenie (given)
<block id="parse-given" />
<prob target="d" value="0.5" />
<query target="d" given="& m" />

# error -- nieznany literał w zapytaniu
<block id="unknown-symbol" />
<prob target="d" value="0.5" />
<query target="m" given="d" />

# error -- warunek o zerowym prawdopodobieństwie
<block id="impossible-condition" />
<prob target="d" value="0.5" />
<query target="d" given="d & ~d" />
