---
type: regex
target: {source: file, path: verdict-379.txt}
match: contains
flags: i
pattern: '(?=[^\n]*374)(?=[^\n]*(check\.py|test_scripts\.py))(?=[^\n]*((both|two)[^\n]*(touch|edit|chang)|touched by both|same file|shared file))'
---
