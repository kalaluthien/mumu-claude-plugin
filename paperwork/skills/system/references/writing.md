# writing

Word every text of a contract so that a reader takes each level's point from its first line and meets one word for one concept.

## Domain

- **name**: a title, a label, a term or an edge's label. It is English and shows as written.
- **description**: every other text: a `purpose`, an `about`, a `meaning`, an item's text, a step's `note`, a `statement`, a question's `asks`. It is English, or Korean when the reader asks for Korean, one language through the contract.
- **lead**: the description a reader meets before what sits under it. The contract's `purpose` leads the levels, a level's `about` its areas, an area's `purpose` item, or its `why` where its tag has no `purpose`, its nodes, a node's `purpose` its items, a scenario's `purpose` its steps.
- **other word**: a second word for the concept a term names. A term lists them in `avoid`, and the checker refuses each in every text.
- **settled word**: a Korean word that 표준국어대사전 (`https://stdict.korean.go.kr`) holds in the sense meant, or that the subject's own Korean documents use more than its transliteration.

## Steps

1. List the terms: each word of the subject's business, technique, theory, profession or guideline that a reader must take in one sense becomes a `term` with its `meaning`, and its `avoid` lists the other words the sources, a translation or habit would say for it.
2. Write the names, then the leads from the top down.
3. Write what sits under each lead: the items, the notes, the statements.
4. Read from the top: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/scripts/check-contract.py outline <contract> [level]` prints each lead with its parts. The first line must raise the question each level's lead answers; then hold each level against the rules under Structure, and rewrite until none breaks.
5. Check: the `check` call refuses what its `rules` call lists; every other rule here is the writer's to keep.

## Rules

### Structure

- **Lead says the point**: a lead states what is true of all under it, in words a reader could deny, such as "A courier and a receiver never meet; one code joins them". It never only announces what follows, such as "The parts of the locker" or "Who takes part and what passes between them".
- **Lead covers its parts**: a lead is true of every part under it and promises nothing that no part delivers. A part the lead does not cover moves to the level whose lead does, or the lead is rewritten.
- **Parts split cleanly**: every fact has exactly one part to sit under: no two purposes claim one job, and the parts together leave nothing of their lead out. A fact two parts share sits in one, and the other names that part as `{id}`.
- **Parts read alike**: the purposes under one lead share one form, each opening with the verb that says what its part is for, an area's and a state's included, and so do the entries of one list.
- **Order by one principle**: the parts under a lead come in an order a reader can name in a phrase, such as the order of flow, the order of time or from the outside in. Nodes are written in that order.
- **Each text stands alone**: a description is understood without the text before it. It points at nothing outside itself by `it`, `this`, `the above` or `그것`, and ties to its lead by a word of the lead or a sibling named as `{id}`, the known word first and the new fact last.
- **Detail under the narrowest lead**: a detail sits under the lowest lead that covers it: a fact about one node goes into that node's item, never into the level's `about`. No item only repeats its purpose.
- **One idea a sentence**: a description is one sentence of 25 words at most, in the active voice, its subject the thing that acts; only a lead that must name each of its parts runs longer. A statement holds one condition a test could pass or fail, with no "and/or", "where possible" or "some".

### Words

- **One word per concept**: a concept keeps one word in every text, and a word is never varied for style, since a second word reads as a second thing. A term is written as the term in a Korean description too, such as `code를 누르면 엽니다`, never by a Korean word for it, which belongs in the term's `avoid`.
- **Names stay English**: every title, label, term and edge label is English whatever the language of the descriptions, since the page's own words, its tag names, item labels and controls, are English and one name must read the same beside them.
- **Label names a thing**: a node's label is a noun phrase that opens in lower case with its article, such as "the checker", so it reads inside a sentence; an area's names a group or a place the same way, such as "the three jobs" or "outside the skill".
- **Edge reads as a sentence**: a static edge's label opens with a verb, so that `<from label> <label> <to label>` is a true, grammatical sentence that ends where the `to` label follows, such as "writes" or "takes its items from". An `access` edge to a file reads "reads", "writes" or "appends a line to".
- **Name, never spell**: a text names a node, an edge or an area as `{id}` and never spells its label, a level's and a scenario's title included, such as `Inside {server}`, so a new name changes one record. Words are matched whatever the space between them; a plural or another spelling is the writer's to find. Only a name, a source's own words, an item of the code form and the subject's words between backticks stay as written. The name shows with a capital where it opens the text or follows a full stop, unless its first word is the subject's own, such as a file name.
- **Note adds, never repeats**: a step's note says what this step alone shows, in 60 characters at most. It names neither end of its own edge, copies no purpose, quotes no label between backticks, which a rename would leave stale, and is left out when it has nothing to add.
- **No drawing**: no text says how a thing is drawn: no position, colour, size or markup, since the page's code decides them. The `text-plain` rule refuses the commonest forms; a hex colour of four or eight digits, a unit other than `px`, such as `2rem` or `50%`, an entity such as `&lt;` and words such as "shown in red" are the writer's to keep out. The subject's own colour, length or style goes between backticks or in an item of the code form.
- **Angle words between backticks**: a placeholder, a comparison or the subject's own markup goes between backticks, such as `` `<plugin>` ``, or in an item of the `code` form, which the page draws as written. The checker refuses a table cell or a tree note that is no text.

### Korean descriptions

- **Settled word first**: a word of business, technique, theory, a profession or a guideline that is no term of the contract is chosen in this order: a settled Sino-Korean word, such as 운영 체제, 의존성 or 조건부 확률; else the transliteration as 표준국어대사전 or 외래어 표기법 spells it, such as 콘텐츠, 메시지 or 디렉터리, never 컨텐츠 or 메세지; else the English word as written. So 오퍼레이팅 시스템 is wrong where 운영 체제 is settled. A transliteration the reader may not know carries its English once, in brackets with no space, such as 프롬프트(prompt). An identifier, a file name, a command and a product name stay as the subject writes them. The word chosen is kept in one spelling and one spacing, and one that must never vary becomes a term.
- **Both particles after a name**: after `{id}` write a particle of one form, such as 의, 에, 에서, 도 or 만, or both forms of one that has two. The label shows there without its article. After a term or an English word, whose sound the writer knows, write the one form that sound takes. A particle joins the word before it with no space: `{door}을(를)`, `code를`, `URL로`.
- **Polite ending**: a sentence closes in `-니다`. An entry or a note that is no sentence is a phrase with no full stop.
- **Korean, not translated**: the actor is the subject of an active verb. Write a plain particle or verb for `~에 의해`, `~를 통해`, `되어지다`, `~를 수행합니다` and `~를 가지고 있습니다`, and drop a chain of `의`, a `들` on each noun, and `그것` or `이것`.
