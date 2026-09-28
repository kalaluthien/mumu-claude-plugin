---
type: regex
target: {source: file, path: trend.html}
match: contains
flags: is
pattern: ^(?=.*?<main\b[^>]*>(?:<script\b(?:(?!</script>).)*</script>|<!--(?:(?!-->).)*-->|<(?!script\b|!--|/main\b)[^>]*>|[^<])*?(?<![0-9])214(?![0-9]))(?=.*?<main\b[^>]*>(?:<script\b(?:(?!</script>).)*</script>|<!--(?:(?!-->).)*-->|<(?!script\b|!--|/main\b)[^>]*>|[^<])*?(?<![0-9])120(?![0-9]))
---
