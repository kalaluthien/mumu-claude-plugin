# Formats

How every renderer shows a `meta` entry, so a value reads the same in chat and on a page. The grammar,
[../schema/assets/schema.json](../schema/assets/schema.json), lists the formats and reserved keys; this file gives each
one display.

A renderer shows each entry as `<name>: <display>` beside the element it annotates. For a reserved key, `<name>` is the key itself. For any other key, it is the key without its `-<format>` ending, so `wait-ms` reads `wait`.

| format or key | display |
| --- | --- |
| `text` | the text as written |
| `number` | the number as written, a whole number without `.0` |
| `url` | a link whose text is the name: `page` for `page-url` |
| `ms` | the number followed by ` ms` |
| `percent` | the number followed by `%` |
| `date` | the date as written, `YYYY-MM-DD` |
| `bool` | `yes` or `no` |
| `note` | the remark in italics |
| `diff` | the change after its sign, `+ added`, `− removed` or `~ changed`, and the element tinted green, red or amber |
| `evidence` | each pointer as code, or as a link when it is a url, joined by commas |
| `constraint` | each requirement as code, joined by commas |
