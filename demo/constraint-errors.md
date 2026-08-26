# error -- brak expr
<constraint />

# error -- nieparsowalne expr
<constraint expr="a &&& b" />

# warning -- niezamknięty tag
<constraint expr="~(a & m)">

# poprawne (bez diagnostyki)
<constraint expr="~(~d & m)" />
