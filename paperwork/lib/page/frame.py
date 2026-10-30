"""Wrap a page's content in the shared frame, and measure that frame in a browser."""
import contextlib
import html
import pathlib

ASSETS = pathlib.Path(__file__).resolve().parent / "assets"
SECTION_TOP_LIMIT = 120
TIMEOUT_MS = 5000
PHONE_WIDTH = 390
SCREEN_WIDTH = 1200
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


def build(title, content, nav):
    """One self-contained page: the frame's css and script are inlined, so it opens with nothing beside it."""
    style = "".join(read(name) for name in ("tokens.css", "parts.css", "frame.css"))
    return (read("frame.html").replace("__TITLE__", html.escape(title)).replace("__STYLE__", style)
            .replace("__SCRIPT__", read("frame.js")).replace("__NAV__", links(nav)).replace("__CONTENT__", content))


@contextlib.contextmanager
def opened(browser, url, width, scheme="light", permissions=(), requests=None):
    context = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme, permissions=list(permissions))
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
            if not page.locator(f"{button} svg").is_visible() or not page.locator(f"{button} .sr-only").inner_text().strip():
                return f"{button} lacks an inline icon or a name a screen reader reads"
            shown = page.locator(f"{button} svg").evaluate("e => [getComputedStyle(e).backgroundColor, getComputedStyle(e).fill]")
            if shown != ["rgba(0, 0, 0, 0)", "none"]:
                return f"{button}'s icon is painted over as a solid block"
    return None


FACTS = {"left navigation": left_navigation, "right body": right_body, "copy": copy, "reset": reset, "theme": theme,
         "root": root, "icons": icons}


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
