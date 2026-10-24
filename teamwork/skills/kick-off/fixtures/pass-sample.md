## Definition of done
1. [check] **plain**: `echo x | tr a-z A-Z` prints `OK`; on base prints `no`.
2. [check] **escaped**: `echo x \| cat` prints `x | cat`; on base prints `no`.
3. [check] **compound**: `cd /tmp && echo x | cat` prints `ok`; on base prints `no`.
4. [check] **or-list**: `false || echo x | tr a-z A-Z` prints `X`; on base prints `no`.
5. [check] **quoted backslash**: `echo "a\"|b" | cat` prints `a"|b`; on base prints `no`.
6. [check] **quoted substitution**: `echo "$(echo "a|b")" | tr a-z A-Z` prints `A|B`; on base prints `no`.
