"""The message port's adapter for herdr: `tell` types the text into the receiver's pane once it is ready, since herdr queues nothing."""
import time

import agent
import session

POLL, SEEN = 1.0, 10.0  # how long a taken prompt may take to show, as work or as text on the screen


def tell(name, text, timeout):
    """(delivered, what happened): `after its turn`, `after <n> retries`, or why it was not delivered."""
    if not text.strip():  # an empty text shows on every screen, so the confirm would pass with nothing sent
        return False, "the text is empty"
    deadline, retries, waited = time.time() + timeout, 0, False
    while True:
        a = session.agent(name)
        if not a:
            return False, "not live"
        if a.get("agent") == agent.KIND:  # a session of the team's own kind has its own message adapter, which waits for no turn
            return False, f"a {agent.KIND} session; tell it by {agent.TELL} to {name}"
        if a.get("agent_status") not in ("idle", "done"):
            waited = True
            if not session.wait_idle(name, max(deadline - time.time(), 0)):
                status = (session.agent(name) or {}).get("agent_status")
                return False, f"{'blocked at a tool prompt' if status == 'blocked' else f'still {status}'} after {timeout:g}s"
            continue
        error = session.prompt(name, text)  # the name, which herdr resolves on each call, since it may move the pane
        if error == "agent_blocked" and time.time() < deadline:  # it reached a tool prompt between the read and the send
            retries += 1
            time.sleep(POLL)
            continue
        if error:
            return False, error
        if not seen(name, text):
            return False, "sent, but the session never showed it"
        return True, f"after {retries} {'retry' if retries == 1 else 'retries'}" if retries else "after its turn" if waited else ""


def seen(name, text):
    """Whether the session turned to work or shows the text, so a prompt herdr took also reached it."""
    deadline = time.time() + SEEN
    while time.time() < deadline:
        if (session.agent(name) or {}).get("agent_status") == "working" or text[:40] in session.screen(name):
            return True
        time.sleep(POLL)
    return False
