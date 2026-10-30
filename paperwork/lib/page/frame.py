"""Wrap a page's content in the shared frame, and measure that frame in a browser."""
import contextlib
import html
import pathlib
import re

ASSETS = pathlib.Path(__file__).resolve().parent / "assets"
SECTION_TOP_LIMIT = 120
TIMEOUT_MS = 5000
MARK_WAIT_MS = 1000
PHONE_WIDTH = 390
SCREEN_WIDTH = 1200
NARROW_WIDTHS = (PHONE_WIDTH, 820)
SHORT_SCREEN = 500
OUTSIDE_POINT = (PHONE_WIDTH - 10, 600)
TEXT_SIZES = {13, 15, 17, 19, 22, 24}
CORNERS = {0, 4, 6, 8, 10}
TITLE_LOOK = {SCREEN_WIDTH: ["24px", "600"], PHONE_WIDTH: ["22px", "600"]}
NAV_ROWS = {SCREEN_WIDTH: {".lnb-item > .lnb-link": 40, ".lnb-subitem a": 32}, PHONE_WIDTH: {".lnb-item > .lnb-link": 44, ".lnb-subitem a": 44}}
TOUCH_HEIGHT = 44
CONTRAST = 4.5
TEXTS = """() => { const walker = document.createTreeWalker(document.querySelector(".frame"), NodeFilter.SHOW_TEXT), found = new Set();
    while (walker.nextNode()) {
      const element = walker.currentNode.parentElement;
      if (walker.currentNode.textContent.trim() && element.getClientRects().length && getComputedStyle(element).visibility === "visible"
          && !element.closest("style, script, .sr-only")) found.add(element);
    }
    return [...found]; }"""
OFF_SCALE = f"""() => {{ const sizes = {sorted(TEXT_SIZES)};
    return ({TEXTS})().filter(e => !sizes.includes(parseFloat(getComputedStyle(e).fontSize)))
      .map(e => e.tagName + "." + e.className + " " + getComputedStyle(e).fontSize); }}"""
OFF_CORNERS = f"""() => {{ const allowed = {sorted(CORNERS)};
    return [...document.querySelectorAll(".frame, .frame *")].filter(e => e.getClientRects().length && getComputedStyle(e).visibility === "visible").filter(e => {{
      const box = e.getBoundingClientRect(), round = Math.min(box.width, box.height) / 2;
      return ["TopLeft", "TopRight", "BottomLeft", "BottomRight"].some(corner => {{
        const value = getComputedStyle(e)["border" + corner + "Radius"], number = parseFloat(value);
        return !value.includes("%") && !allowed.includes(number) && number < round; }}); }})
      .map(e => e.tagName + "." + e.className + " " + getComputedStyle(e).borderTopLeftRadius); }}"""
LOW_CONTRAST = f"""() => {{
    const channels = text => text.match(/[\\d.]+/g).map(Number);
    const light = ([r, g, b]) => {{ const part = v => (v /= 255) <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4;
      return .2126 * part(r) + .7152 * part(g) + .0722 * part(b); }};
    const behind = element => {{ for (let e = element; e; e = e.parentElement) {{
      const [r, g, b, a = 1] = channels(getComputedStyle(e).backgroundColor);
      if (a === 1) return [r, g, b]; }} return [255, 255, 255]; }};
    return ({TEXTS})().filter(e => !(e instanceof SVGElement) && !e.closest("[disabled], [aria-disabled=true]")).filter(e => {{
      const [hi, lo] = [light(channels(getComputedStyle(e).color)), light(behind(e))].sort((a, b) => b - a);
      return (hi + .05) / (lo + .05) < {CONTRAST}; }}).map(e => e.tagName + "." + e.className + " " + e.textContent.trim().slice(0, 30)); }}"""
SHORT_CONTROLS = f"""() => [...document.querySelectorAll("button, input, select, textarea, summary, .frame-nav a")]
    .filter(e => e.getClientRects().length && getComputedStyle(e).visibility === "visible" && e.getBoundingClientRect().height < {TOUCH_HEIGHT})
    .map(e => e.tagName + "." + e.className + " " + e.getBoundingClientRect().height)"""
ROW_HEIGHTS = """selector => [...document.querySelectorAll(".frame-nav " + selector)].filter(e => e.getClientRects().length).filter(e => {
      const style = getComputedStyle(e), lines = (e.getBoundingClientRect().height - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom)) / parseFloat(style.lineHeight);
      return Math.round(lines) === 1; }).map(e => e.getBoundingClientRect().height)"""
BLANK_TAGS = """() => [...document.querySelectorAll(".frame-tag")].filter(e => e.getClientRects().length && getComputedStyle(e).visibility === "visible" && !e.innerText.trim()).map(e => e.outerHTML)"""
CONTROL_WORDS = {"#frame-copy": "Copy this view", "#frame-reset": "Back to start", "#frame-theme": "Light or dark"}
# Fixed English around Korean content leaves Hangul at about a third of the letters; a quoted Korean word stays under this.
KOREAN_SHARE = 0.1
OUTSIDE_PROSE = re.compile(r"<style.*?</style>|<script(?![^>]*json).*?</script>|<[^>]*>", re.S)
BACKGROUND = "getComputedStyle(document.body).backgroundColor"


def read(name):
    return (ASSETS / name).read_text(encoding="utf-8")


def links(nav):
    """List items for (target, label) or (target, label, children) entries, the children one level down."""
    out = []
    for target, label, *children in nav:
        link = f'<a class="lnb-btn lnb-link" href="#{html.escape(target)}">{html.escape(label)}</a>'
        below = "".join(f'<li class="lnb-subitem"><a class="lnb-btn lnb-link" href="#{html.escape(child)}">{html.escape(name)}</a></li>'
                        for child, name in (children[0] if children else ()))
        # A submenu stays open, since these links jump within one page and hide nothing behind a toggle.
        out.append(f'<li class="lnb-item active">{link}<div class="lnb-submenu"><ul>{below}</ul></div></li>' if below
                   else f'<li class="lnb-item">{link}</li>')
    return "".join(out)


def language(content):
    """ko when Hangul is a real share of the letters a reader meets, else en."""
    prose = OUTSIDE_PROSE.sub("", content)
    hangul, latin = len(re.findall("[\uac00-\ud7a3]", prose)), len(re.findall("[A-Za-z]", prose))
    return "ko" if hangul > KOREAN_SHARE * (hangul + latin) else "en"


def build(title, content, nav):
    """One self-contained page: the frame's css and script are inlined, so it opens with nothing beside it."""
    fills = {"__LANGUAGE__": language(content), "__TITLE__": html.escape(title), "__NAV__": links(nav), "__CONTENT__": content,
             "__STYLE__": "".join(read(name) for name in ("tokens.css", "parts.css", "frame.css")), "__SCRIPT__": read("frame.js")}
    # One pass, so a title or label that reads like a placeholder stays as written.
    return re.sub("|".join(fills), lambda found: fills[found.group()], read("frame.html"))


@contextlib.contextmanager
def opened(browser, url, width, scheme="light", permissions=(), requests=None, height=900):
    context = browser.new_context(viewport={"width": width, "height": height}, color_scheme=scheme, permissions=list(permissions))
    context.set_default_timeout(TIMEOUT_MS)
    page = context.new_page()
    if requests is not None:
        page.on("request", lambda request: requests.append(request.url))
    page.goto(url)
    yield page
    context.close()


def section_top(page, link):
    return page.evaluate("id => document.getElementById(id).getBoundingClientRect().top", link.get_attribute("href")[1:])


def left_navigation(browser, url, **_):
    with opened(browser, url, SCREEN_WIDTH) as page:
        nav, body = page.locator(".frame-nav").bounding_box(), page.locator(".frame-body").bounding_box()
        if nav["x"] + nav["width"] > body["x"]:
            return "the navigation does not stand left of the body"
        for link in page.locator(".frame-nav a").all():
            link.click()
            if not 0 <= section_top(page, link) <= SECTION_TOP_LIMIT:
                return f"{link.inner_text()} does not reach the top of the body"
    return None


def right_body(browser, url, **_):
    with opened(browser, url, PHONE_WIDTH) as page:
        body = page.locator(".frame-body").bounding_box()
        if body["x"] != 0 or body["width"] != PHONE_WIDTH:
            return f"the body is {body['width']} px wide at x {body['x']}"
        if page.evaluate("document.documentElement.scrollWidth") > PHONE_WIDTH:
            return "the page scrolls wider than the screen"
        if page.locator(".frame-nav").is_visible():
            return "the navigation covers the body before a press"
        page.locator("#frame-menu").focus()
        page.keyboard.press("Enter")
        if not page.evaluate("document.activeElement.closest('.frame-nav') !== null"):
            return "the keyboard does not reach the navigation"
        page.keyboard.press("Escape")
        if page.locator(".frame-nav").is_visible() or page.evaluate("document.activeElement.id") != "frame-menu":
            return "Escape does not close the navigation and return to the menu"
        page.locator("#frame-menu").click()
        if not page.locator(".frame-nav").is_visible():
            return "a press does not show the navigation"
        link = page.locator(".frame-nav a").last
        link.click()
        if page.locator(".frame-nav").is_visible():
            return "the navigation stays over the body after a choice"
        if not 0 <= section_top(page, link) <= SECTION_TOP_LIMIT:
            return f"{link.inner_text()} does not reach the top of the body"
    return None


def copy(browser, url, copied, **_):
    with opened(browser, url, SCREEN_WIDTH, permissions=("clipboard-read", "clipboard-write")) as page:
        page.evaluate("navigator.clipboard.writeText('before')")
        page.locator("#frame-copy").click()
        page.wait_for_function("document.getElementById('frame-status').textContent !== ''")
        held = page.evaluate("navigator.clipboard.readText()")
        if held != copied:
            return f"the clipboard holds {held[:40]!r}"
    return None


def reset(browser, url, change, state, **_):
    with opened(browser, url, SCREEN_WIDTH) as page:
        before = page.evaluate(state)
        page.evaluate(change)
        if page.evaluate(state) == before:
            return "the change made no difference to measure"
        page.locator("#frame-reset").click()
        if page.evaluate(state) != before:
            return "a press does not undo the change"
    return None


def theme(browser, url, **_):
    for scheme, other in (("light", "dark"), ("dark", "light")):
        with opened(browser, url, SCREEN_WIDTH, scheme=scheme) as page:
            read_theme = "document.documentElement.dataset.theme"
            if page.evaluate(read_theme) != scheme:
                return f"the page does not open in the system's {scheme} theme"
            colour = page.evaluate(BACKGROUND)
            page.locator("#frame-theme").click()
            pressed = page.evaluate(BACKGROUND)
            if page.evaluate(read_theme) != other or pressed == colour:
                return f"a press does not change the {scheme} page's colours"
            page.reload()
            if page.evaluate(read_theme) != other or page.evaluate(BACKGROUND) != pressed:
                return "a reload loses the choice"
    return None


def root(browser, url, **_):
    requests = []
    with opened(browser, url, SCREEN_WIDTH, requests=requests) as page:
        if (size := page.evaluate("getComputedStyle(document.documentElement).fontSize")) != "16px":
            return f"the root is {size}"
        if fonts := page.evaluate("document.fonts.size"):
            return f"{fonts} fonts load"
    if left := [request for request in requests if not request.startswith(("file:", "data:"))]:
        return f"a request left for {left[0]}"
    return None


def icons(browser, url, **_):
    with opened(browser, url, SCREEN_WIDTH) as page:
        for button in ("#frame-copy", "#frame-reset"):
            if not page.locator(f"{button} svg").is_visible() or not page.locator(f"{button} .frame-word").inner_text().strip():
                return f"{button} lacks an inline icon or a name a screen reader reads"
            shown = page.locator(f"{button} svg").evaluate("e => [getComputedStyle(e).backgroundColor, getComputedStyle(e).fill]")
            if shown != ["rgba(0, 0, 0, 0)", "none"]:
                return f"{button}'s icon is painted over as a solid block"
    return None


def views(page):
    """The page as it opens, then with each navigation link pressed, since a section may stay hidden until then."""
    yield page
    for link in page.locator(".frame-nav a").all():
        if not link.is_visible():
            page.locator("#frame-menu").click()
        link.click()
        yield page


def swept(browser, url, measure, widths=(SCREEN_WIDTH, PHONE_WIDTH), schemes=("light",)):
    """The first thing measure finds wrong, opening every fold first, with each view walked."""
    for width in widths:
        for scheme in schemes:
            with opened(browser, url, width, scheme=scheme) as page:
                page.evaluate("document.querySelectorAll('details').forEach(fold => { fold.open = true; })")
                for shown in views(page):
                    if found := shown.evaluate(measure):
                        return f"at {width} px in {scheme}: {found[0]}"
    return None


def type_scale(browser, url, **_):
    return swept(browser, url, OFF_SCALE)


def corners(browser, url, **_):
    return swept(browser, url, OFF_CORNERS)


def title_style(browser, url, **_):
    for width, look in TITLE_LOOK.items():
        with opened(browser, url, width) as page:
            found = page.locator("h1:visible").first.evaluate("e => [getComputedStyle(e).fontSize, getComputedStyle(e).fontWeight]")
            if found != look:
                return f"at {width} px the title is {found}"
    return None


def text_contrast(browser, url, **_):
    return swept(browser, url, LOW_CONTRAST, widths=(SCREEN_WIDTH,), schemes=("light", "dark"))


def touch_targets(browser, url, **_):
    if found := swept(browser, url, SHORT_CONTROLS, widths=(PHONE_WIDTH,)):
        return found
    with opened(browser, url, PHONE_WIDTH) as page:
        page.locator("#frame-menu").click()
        if found := page.evaluate(SHORT_CONTROLS):
            return f"with the menu open: {found[0]}"
    return None


def navigation_rows(browser, url, **_):
    for width, rows in NAV_ROWS.items():
        with opened(browser, url, width) as page:
            if width == PHONE_WIDTH:
                page.locator("#frame-menu").click()
            for selector, height in rows.items():
                if wrong := [found for found in page.evaluate(ROW_HEIGHTS, selector) if abs(found - height) > .5]:
                    return f"at {width} px {selector} is {wrong[0]} px high"
    return None


def status_words(browser, url, **_):
    return swept(browser, url, BLANK_TAGS, widths=(SCREEN_WIDTH,))


def menu_under_bar(browser, url, **_):
    for width in NARROW_WIDTHS:
        with opened(browser, url, width) as page:
            page.locator("#frame-menu").click()
            bar, nav = page.locator(".frame-top").bounding_box(), page.locator(".frame-nav").bounding_box()
            if abs(nav["y"] - (bar["y"] + bar["height"])) > 1:
                return f"at {width} px the navigation starts at {nav['y']}, the top bar ends at {bar['y'] + bar['height']}"
    return None


def menu_closed(browser, url, **_):
    with opened(browser, url, PHONE_WIDTH) as page:
        if shown := [link for link in page.locator(".frame-nav a").all() if link.is_visible()]:
            return f"{shown[0].inner_text()} shows while the navigation is closed"
    return None


def long_menu(browser, url, **_):
    for width in NARROW_WIDTHS:
        with opened(browser, url, width, height=SHORT_SCREEN) as page:
            page.locator("#frame-menu").click()
            nav = page.locator(".frame-nav").bounding_box()
            if nav["y"] + nav["height"] > SHORT_SCREEN + 1:
                return f"at {width} px the navigation ends at {nav['y'] + nav['height']}, below the screen"
            page.locator(".frame-nav a").last.scroll_into_view_if_needed()
            link = page.locator(".frame-nav a").last.bounding_box()
            if link["y"] + link["height"] > SHORT_SCREEN + 1:
                return f"at {width} px the last link stays below the screen"
    return None


def outside_press(browser, url, **_):
    with opened(browser, url, PHONE_WIDTH) as page:
        page.locator("#frame-menu").click()
        page.mouse.click(*OUTSIDE_POINT)
        if page.locator(".frame-nav").is_visible():
            return "a press outside leaves the navigation open"
    return None


def sub_link_current(browser, url, **_):
    with opened(browser, url, SCREEN_WIDTH) as page:
        links = page.locator(".lnb-subitem a")
        if links.count() < 2:
            return None
        links.nth(1).click()
        look = "e => { const s = getComputedStyle(e); return [s.color, s.backgroundColor, s.fontWeight]; }"
        try:
            page.wait_for_function("document.querySelectorAll('.lnb-subitem a')[1].hasAttribute('aria-current')", timeout=MARK_WAIT_MS)
        except Exception:
            return f"{links.nth(1).inner_text()} is not marked after a press"
        if links.nth(1).evaluate(look) == links.nth(0).evaluate(look):
            return f"{links.nth(1).inner_text()} looks like the links around it"
    return None


def print_light(browser, url, **_):
    with opened(browser, url, SCREEN_WIDTH, scheme="dark") as page:
        page.evaluate("""() => { window.printedTheme = null;
            addEventListener("beforeprint", () => { window.printedTheme = document.documentElement.dataset.theme; }); }""")
        page.pdf()
        found = page.evaluate("[window.printedTheme, document.documentElement.dataset.theme]")
        if found != ["light", "dark"]:
            return f"a print of a dark page reads {found[0]} and leaves it {found[1]}"
    return None


def print_menu(browser, url, **_):
    with opened(browser, url, PHONE_WIDTH) as page:
        page.locator("#frame-menu").click()
        page.emulate_media(media="print")
        if page.locator(".frame-nav").is_visible():
            return "a print of a narrow page shows the open menu"
    return None


def control_words(browser, url, **_):
    with opened(browser, url, SCREEN_WIDTH) as page:
        for button, word in CONTROL_WORDS.items():
            if not page.locator(f"{button} .frame-word").is_visible() or page.locator(button).inner_text().strip() != word:
                return f"{button} does not show {word}"
    with opened(browser, url, PHONE_WIDTH) as page:
        if page.evaluate("document.querySelector('.frame-top').scrollWidth > document.querySelector('.frame-top').clientWidth"):
            return "the top bar runs past the screen"
        if page.locator("#frame-copy .frame-word").inner_text().strip() != CONTROL_WORDS["#frame-copy"]:
            return "a narrow control leaves a screen reader no word"
    return None


FACTS = {"left navigation": left_navigation, "right body": right_body, "copy": copy, "reset": reset, "theme": theme,
         "root": root, "icons": icons, "menu under bar": menu_under_bar, "menu closed": menu_closed, "long menu": long_menu,
         "outside press": outside_press, "sub-link current": sub_link_current, "print light": print_light,
         "print menu": print_menu, "control words": control_words, "type scale": type_scale, "corners": corners, "title style": title_style,
         "text contrast": text_contrast, "touch targets": touch_targets, "navigation rows": navigation_rows, "status words": status_words}


def probe(browser, url, **expected):
    """{fact: why it failed} for a built page; expected gives copied (the clipboard's text) and change and state (scripts)."""
    failures = {}
    for name, measure in FACTS.items():
        # A control that never answers fails its own fact and leaves the other facts measured.
        try:
            why = measure(browser, url, **expected)
        except Exception as e:
            why = str(e).splitlines()[0]
        if why:
            failures[name] = why
    return failures
