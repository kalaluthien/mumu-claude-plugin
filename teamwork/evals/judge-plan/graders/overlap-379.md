---
type: regex
target: {source: file, path: verdict-379.txt}
match: contains
flags: i
pattern: '(?=[^\n]*374)(?=[^\n]*(check\.py|test_scripts\.py))(?=[^\n]*(overlap|both|same file|shared file|two tasks))'
---
