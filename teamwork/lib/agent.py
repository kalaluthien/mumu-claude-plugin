"""The agent port: the coding agent a session runs, done by the adapter `agent_<TEAMWORK_AGENT>` (default `claude`).

Every adapter has these names:
- `KIND` the agent's kind for the session port's `start`; `command(name, plugin_dir, model, effort, off)` its arguments after that
- `TOOLS_OFF` the tools each role has off, comma-joined by role; `kickoff(args)` the prompt that starts a role
- `TRUST` the folder trust dialog's text and the keys that accept it; `EXIT` the prompt that ends a session, and `DIALOGS`
  the text of each dialog it may show then, with the key that exits without saving anything"""
import importlib
import os

adapter = importlib.import_module(f"agent_{os.environ.get('TEAMWORK_AGENT', 'claude')}")


def __getattr__(name):
    return getattr(adapter, name)
