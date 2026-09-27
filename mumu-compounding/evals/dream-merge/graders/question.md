---
# one question, multiSelect true, 2 to 4 options; a regex, since an llm judge failed a well-formed file 1 run in 3
type: regex
target: {source: file, path: question-1.json}
match: contains
pattern: '^\s*\{\s*"questions":\s*\[\s*\{(?=[^\[\]]*"multiSelect":\s*true)[^\[\]]*"options":\s*\[\s*(?:\{[^{}]*\}\s*,\s*){1,3}\{[^{}]*\}\s*\][^\[\]]*\}\s*\]\s*\}\s*$'
---
