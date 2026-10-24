## Definition of done
1. [check] **plain**: `echo x | tr a-z A-Z` prints `OK`; on base prints `no`.
2. [check] **escaped**: `echo x \| cat` prints `x | cat`; on base prints `no`.
3. [check] **compound**: `cd /tmp && echo x | cat` prints `ok`; on base prints `no`.
