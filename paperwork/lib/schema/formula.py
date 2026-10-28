"""Formulas in Alloy 6 notation: tokens, a parser, the names a formula uses, and a readable layout.

The model writes rules (guards among them), pre and post conditions in Alloy itself, with English keywords
(not, and, or, implies, iff) and every logic Alloy 6 has: predicate, relational, integer and temporal.
The next state is written only with `after`; a primed name is refused.
"""
import re

KEYWORDS = {
    "abstract", "all", "and", "as", "assert", "but", "check", "disj", "else", "enum", "exactly", "expect",
    "extends", "fact", "for", "fun", "iden", "iff", "implies", "in", "Int", "int", "let", "lone", "module", "no",
    "none", "not", "one", "open", "or", "pred", "private", "run", "seq", "set", "sig", "some", "steps", "String",
    "sum", "this", "univ", "var", "always", "eventually", "after", "before", "historically", "once", "until",
    "releases", "since", "triggered",
}
# words the translation itself declares; a model may not use them as names
OWN = {"Now", "Call", "happens", "at", "self", "result", "stutter", "behaviour", "assumptions"}
RESERVED = KEYWORDS | OWN

QUANTIFIERS = {"all", "some", "no", "lone", "one", "sum"}
MULTIPLICITIES = {"no", "some", "lone", "one", "set"}
UNARY_OPERATORS = {"not", "always", "eventually", "after", "before", "historically", "once"}
BINARY_TEMPORAL = {"until", "releases", "since", "triggered", ";"}
COMPARISONS = {"in", "=", "!=", "<", ">", "=<", ">="}
CONSTANTS = {"none", "univ", "iden", "Int"}
REFUSE = {"&&": "and", "||": "or", "=>": "implies", "<=>": "iff", "!": "not", "!in": "not in"}

TOKEN_PATTERN = re.compile(r"""
    (?P<ws>\s+) | (?P<num>\d+) | (?P<name>[A-Za-z][A-Za-z0-9_]*) |
    (?P<quote>"[^"]*"|'[^'\s]*') | (?P<prime>') |
    (?P<op><=>|=>|=<|>=|!=|!in|&&|\|\||->|<:|:>|\+\+|<<|>>>|>>|[-+&#.~^*;=<>!|,:\[\](){}@])
""", re.X)


class FormulaError(Exception):
    def __init__(self, message, position=None):
        super().__init__(message)
        self.position = position


def tokens(text):
    out, i = [], 0
    while i < len(text):
        match = TOKEN_PATTERN.match(text, i)
        if not match:
            raise FormulaError(f"cannot read '{text[i]}'", i)
        kind = match.lastgroup
        value = match.group(kind)
        if kind == "prime":
            raise FormulaError("write the next state with after, not a prime", i)
        if kind == "quote":
            raise FormulaError(f"a value is a name, not a string: write {value.strip(chr(39) + chr(34)).replace(' ', '')}", i)
        if kind == "op" and value in REFUSE:
            raise FormulaError(f"write {REFUSE[value]}, not {value}", i)
        if kind != "ws":
            out.append((kind, value, i))
        i = match.end()
    out.append(("end", "", len(text)))
    return out


class Parser:
    """Pratt parser over Alloy 6 formulas and expressions. Nodes are tuples whose first item is the kind."""

    def __init__(self, text):
        self.token_list = tokens(text)
        self.i = 0

    def peek(self, offset=0):
        return self.token_list[min(self.i + offset, len(self.token_list) - 1)]

    def value(self, offset=0):
        return self.peek(offset)[1]

    def take(self, want=None):
        token = self.token_list[self.i]
        if want is not None and token[1] != want:
            raise FormulaError(f"expected {want}, found {token[1] or 'the end'}", token[2])
        self.i += 1
        return token

    def parse(self):
        node = self.expression(0)
        if self.peek()[0] != "end":
            raise FormulaError(f"unexpected {self.value()}", self.peek()[2])
        return node

    # binding powers, lowest first; quantifiers and let take the rest of the formula
    BINDING_POWERS = [({"or"}, 10), ({"iff"}, 20), ({"implies"}, 30), ({"and"}, 40), (BINARY_TEMPORAL, 50), (COMPARISONS | {"not"}, 70),
           ({"<<", ">>", ">>>"}, 85), ({"+", "-"}, 90), ({"++"}, 100), ({"&"}, 110), ({"->"}, 120), ({"<:", ":>"}, 130)]

    def binding_power(self):
        symbol, kind = self.value(), self.peek()[0]
        if kind not in ("op", "name"):
            return None
        if symbol == "not" and self.value(1) == "in":
            return 70
        if symbol == "not":
            return None
        for operators, power in self.BINDING_POWERS:
            if symbol in operators:
                return power
        return None

    def expression(self, min_binding_power, operand=False):
        left = self.prefix(operand)
        while True:
            symbol = self.value()
            if symbol == "[":
                left = self.box(left)
                continue
            if symbol == "." and min_binding_power <= 150:
                position = self.take()[2]
                right = self.prefix(True, dot=True)
                left = ("join", left, right, position)
                continue
            power = self.binding_power()
            if power is None or power < min_binding_power or (power == min_binding_power and symbol != "implies"):
                break
            if symbol == "not":
                self.take()
                self.take("in")
                operator = "not in"
            else:
                operator = self.take()[1]
            if operator == "implies":
                right = self.expression(power, True)
                if self.value() == "else":
                    self.take()
                    other = self.expression(power, True)
                    left = ("ite", left, right, other)
                    continue
                left = ("bin", operator, left, right)
                continue
            right = self.expression(power + 1, True)
            if operator in COMPARISONS | {"not in"} and self.value() in COMPARISONS | {"not"} and self.binding_power() == 70:
                raise FormulaError("chain comparisons with and", self.peek()[2])
            left = ("bin", operator, left, right)
        return left

    def box(self, target):
        self.take("[")
        arguments = [] if self.value() == "]" else [self.expression(0)]
        while self.value() == ",":
            self.take()
            arguments.append(self.expression(0))
        self.take("]")
        return ("box", target, arguments)

    def declarations(self):
        out = []
        while True:
            is_disjoint = self.value() == "disj"
            if is_disjoint:
                self.take()
            names = [self.name()]
            while self.value() == ",":
                self.take()
                names.append(self.name())
            self.take(":")
            multiplicity = self.take()[1] if self.value() in MULTIPLICITIES else None
            out.append((names, is_disjoint, multiplicity, self.expression(60, True)))
            if self.value() != ",":
                return out
            self.take()

    def name(self):
        token = self.take()
        if token[0] != "name" or token[1] in KEYWORDS:
            raise FormulaError(f"expected a variable name, found {token[1] or 'the end'}", token[2])
        return token[1]

    def is_declaration(self):
        offset = 0
        if self.value(offset) == "disj":
            offset += 1
        while self.peek(offset)[0] == "name" and self.value(offset) not in KEYWORDS:
            if self.value(offset + 1) == ":":
                return True
            if self.value(offset + 1) != ",":
                return False
            offset += 2
        return False

    def prefix(self, operand=False, dot=False):
        kind, symbol, position = self.peek()
        if dot:   # after a dot: a field, an operation, or a parenthesised expression
            if kind == "name" and symbol not in KEYWORDS - {"Int"}:
                self.take()
                return ("name", symbol, position)
            if symbol == "(":
                return self.prefix()
            if symbol in {"~", "^", "*"}:
                self.take()
                return ("un", symbol, self.prefix(True, dot=True))
            raise FormulaError(f"expected a field or operation after the dot, found {symbol or 'the end'}", position)
        if symbol in QUANTIFIERS and self.value(1) != "[" and (self.is_declaration_at(1)):
            self.take()
            declared = self.declarations()
            self.take("|")
            return ("quant", symbol, declared, self.expression(0), position)
        if symbol == "let":
            self.take()
            binds = []
            while True:
                variable = self.name()
                self.take("=")
                binds.append((variable, self.expression(60, True)))
                if self.value() != ",":
                    break
                self.take()
            self.take("|")
            return ("let", binds, self.expression(0), position)
        if symbol in UNARY_OPERATORS:
            self.take()
            if operand and self.value() in QUANTIFIERS | {"let"} and self.is_declaration_at(1) | (self.value() == "let"):
                raise FormulaError(f"put parentheses round the formula after {symbol}", position)
            return ("un", symbol, self.expression(60, operand))
        if symbol in MULTIPLICITIES and self.value(1) not in {"[", ".", ")", ",", "]", "|"}:
            self.take()
            return ("mult", symbol, self.expression(80, True))
        if symbol == "#":
            self.take()
            return ("un", "#", self.expression(100, True))
        if symbol in {"~", "^", "*"}:
            self.take()
            return ("un", symbol, self.expression(160, True))
        if symbol == "-" and self.peek(1)[0] == "num":
            self.take()
            return ("num", "-" + self.take()[1])
        if symbol == "(":
            self.take()
            inner = self.expression(0)
            self.take(")")
            return ("paren", inner)
        if symbol == "{":
            self.take()
            if self.is_declaration():
                declared = self.declarations()
                self.take("|")
                body = self.expression(0)
                self.take("}")
                return ("compr", declared, body, position)
            items = []
            while self.value() != "}":
                items.append(self.expression(0))
            self.take("}")
            return ("block", items)
        if kind == "num":
            self.take()
            return ("num", symbol)
        if kind == "name":
            if symbol in CONSTANTS or symbol == "this":
                self.take()
                return ("const", symbol)
            if symbol in KEYWORDS:
                raise FormulaError(f"{symbol} cannot start an expression here", position)
            self.take()
            return ("name", symbol, position)
        raise FormulaError(f"unexpected {symbol or 'end of formula'}", position)

    def is_declaration_at(self, offset):
        save = self.i
        self.i += offset
        try:
            return self.is_declaration()
        finally:
            self.i = save


def parse(text):
    return Parser(text).parse()


def walk(node, bound, use):
    """Call use(kind, name, position, bound) for every name: 'free' (a bare name), 'member' (after a dot) or 'call'."""
    kind = node[0]
    if kind == "name":
        use("free", node[1], node[2], bound)
    elif kind in ("num", "const"):
        return
    elif kind == "paren":
        walk(node[1], bound, use)
    elif kind == "block":
        for child in node[1]:
            walk(child, bound, use)
    elif kind == "un" or kind == "mult":
        walk(node[2], bound, use)
    elif kind == "bin":
        walk(node[2], bound, use)
        walk(node[3], bound, use)
    elif kind == "ite":
        for child in node[1:]:
            walk(child, bound, use)
    elif kind == "join":
        walk(node[1], bound, use)
        right = node[2]
        while right[0] == "un" and right[1] in "~^*":
            right = right[2]
        if right[0] == "name":
            use("member", right[1], right[2], bound)
        else:
            walk(right, bound, use)
    elif kind == "box":
        target = node[1]
        if target[0] == "name":
            use("call", target[1], target[2], bound)
        elif target[0] == "join" and target[2][0] == "name":
            walk(target[1], bound, use)
            use("member", target[2][1], target[2][2], bound)
        else:
            walk(target, bound, use)
        for argument in node[2]:
            walk(argument, bound, use)
    elif kind in ("quant", "compr"):
        declarations = node[2] if kind == "quant" else node[1]
        inner = set(bound)
        for names, _, _, expression in declarations:
            walk(expression, inner, use)
            inner |= set(names)
        walk(node[3] if kind == "quant" else node[2], inner, use)
    elif kind == "let":
        inner = set(bound)
        for name, expression in node[1]:
            walk(expression, inner, use)
            inner.add(name)
        walk(node[2], inner, use)


def uses(text):
    """[(kind, name, position, bound)] for a formula, or raises FormulaError."""
    out = []
    walk(parse(text), set(), lambda *arguments: out.append(arguments))
    return out


def binders(text):
    """Every variable a formula binds with a quantifier, a comprehension or let."""
    out = []

    def grab(node):
        if not isinstance(node, tuple):
            return
        if node[0] in ("quant", "compr"):
            for names, *_ in (node[2] if node[0] == "quant" else node[1]):
                out.extend(names)
        if node[0] == "let":
            out.extend(name for name, _ in node[1])
        for child in node[1:]:
            if isinstance(child, tuple):
                grab(child)
            elif isinstance(child, list):
                for entry in child:
                    if isinstance(entry, tuple):
                        grab(entry)
                        for piece in entry:
                            grab(piece) if isinstance(piece, tuple) else None

    grab(parse(text))
    return out


def free_spans(text, names):
    """Positions of bare, unbound occurrences of the given names, for renaming."""
    return [(position, name) for kind, name, position, bound in uses(text) if kind in ("free", "call") and name in names and name not in bound]


def rename(text, mapping):
    """Replace bare, unbound names (parameters, self, result) by expressions."""
    spans = sorted(free_spans(text, set(mapping)), reverse=True)
    for position, name in spans:
        text = text[:position] + mapping[name] + text[position + len(name):]
    return text


def temporal(text):
    """Whether a formula speaks about time: a temporal operator, or one that only time gives meaning to."""
    return any(symbol in UNARY_OPERATORS - {"not"} or symbol in BINARY_TEMPORAL for _, symbol, _ in tokens(text))


WIDTH = 40   # a formula line holds about 40 mono characters


def show(node):
    kind = node[0]
    if kind in ("name",):
        return node[1]
    if kind in ("num", "const"):
        return node[1]
    if kind == "paren":
        return "(" + show(node[1]) + ")"
    if kind == "block":
        return "{ " + " ".join(show(item) for item in node[1]) + " }"
    if kind == "un":
        return node[1] + ("" if node[1] in "#~^*" else " ") + show(node[2])
    if kind == "mult":
        return node[1] + " " + show(node[2])
    if kind == "bin":
        separator = "" if node[1] in ("->",) else " "
        return show(node[2]) + separator + node[1] + separator + show(node[3])
    if kind == "ite":
        return f"{show(node[1])} implies {show(node[2])} else {show(node[3])}"
    if kind == "join":
        return show(node[1]) + "." + show(node[2])
    if kind == "box":
        return show(node[1]) + "[" + ", ".join(show(argument) for argument in node[2]) + "]"
    if kind in ("quant", "compr"):
        declarations = node[2] if kind == "quant" else node[1]
        declaration_text = ", ".join(("disj " if is_disjoint else "") + ", ".join(names) + ": " + (multiplicity + " " if multiplicity else "") + show(expression) for names, is_disjoint, multiplicity, expression in declarations)
        body = node[3] if kind == "quant" else node[2]
        return (f"{node[1]} {declaration_text} | {show(body)}" if kind == "quant" else "{" + declaration_text + " | " + show(body) + "}")
    if kind == "let":
        return "let " + ", ".join(f"{name} = {show(expression)}" for name, expression in node[1]) + " | " + show(node[2])
    raise ValueError(kind)


def chain(node, operator):
    if node[0] == "bin" and node[1] == operator:
        return chain(node[2], operator) + chain(node[3], operator)
    return [node]


def lines(node, indent=0):
    """Lay a formula out over lines no wider than WIDTH: a quantifier's body goes below it, long chains break before and, or."""
    flat = show(node)
    pad = "  " * indent
    if len(flat) + len(pad) <= WIDTH:
        return [pad + flat]
    kind = node[0]
    if kind == "quant":
        declaration_texts = [("disj " if is_disjoint else "") + ", ".join(names) + ": " + (multiplicity + " " if multiplicity else "") + show(expression) for names, is_disjoint, multiplicity, expression in node[2]]
        head, rows = pad + node[1] + " ", []
        for i, declaration in enumerate(declaration_texts):   # declarations wrap one per line when the header is too wide
            piece = declaration + ("," if i < len(declaration_texts) - 1 else " |")
            if rows and len(rows[-1]) + 1 + len(piece) > WIDTH:
                rows.append(pad + "    " + piece)
            else:
                rows = rows[:-1] + [(rows[-1] + " " if rows else head) + piece]
        return rows + lines(node[3], indent + 1)
    if kind == "let":
        head = "let " + ", ".join(f"{name} = {show(expression)}" for name, expression in node[1]) + " |"
        return [pad + head] + lines(node[2], indent + 1)
    if kind == "paren":
        inner = lines(node[1], indent + 1)
        return [pad + "(" + inner[0].lstrip()] + inner[1:-1] + [inner[-1] + ")"] if len(inner) > 1 else [pad + "(" + inner[0].lstrip() + ")"]
    if kind == "un" and node[1] not in "#~^*":
        inner = lines(node[2], indent)
        return [pad + node[1] + " " + inner[0].lstrip()] + inner[1:]
    if kind == "bin" and node[1] in ("and", "or"):
        parts = chain(node, node[1])
        out = lines(parts[0], indent)
        for part in parts[1:]:
            inner_lines = lines(part, indent)
            out += [pad + node[1] + " " + inner_lines[0].lstrip()] + inner_lines[1:]
        return out
    if kind in ("bin", "ite") and (kind == "ite" or node[1] in ("implies", "iff")):
        left, right = (node[1], node[2]) if kind == "ite" else (node[2], node[3])
        word = "implies" if kind == "ite" else node[1]
        head = lines(left, indent)
        head[-1] += " " + word
        out = head + lines(right, indent + 1)
        if kind == "ite":
            out += [pad + "else"] + lines(node[3], indent + 1)
        return out
    if kind == "bin" and node[1] in COMPARISONS | {"not in"}:   # a long comparison: its right side goes below
        return lines(node[2], indent) + [pad + "  " + node[1] + " " + line.lstrip() for line in lines(node[3], indent + 1)[:1]] + lines(node[3], indent + 1)[1:]
    return [pad + flat]


def layout(text):
    """The formula over several lines, or the text unchanged when it does not parse."""
    try:
        return "\n".join(lines(parse(text)))
    except FormulaError:
        return text
