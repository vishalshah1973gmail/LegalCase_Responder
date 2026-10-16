"""Shared-password gate for public deployments.

Set ``APP_PASSWORD`` in Streamlit secrets (or the environment) to require it.
If it is unset — the normal local case — the gate is inert and nothing changes.
"""
from __future__ import annotations

import hmac
import os

import streamlit as st


def _expected() -> str:
    return (os.getenv("APP_PASSWORD") or "").strip()


def require_password() -> bool:
    """Return True if the visitor may proceed. Renders a prompt and returns
    False otherwise. Call it at the top of every page, right after
    ``st.set_page_config``."""
    expected = _expected()
    if not expected:
        # No APP_PASSWORD configured -> the gate is inert and the app is open.
        # This is the intended default for local development: a password prompt
        # on localhost is friction with no benefit. Set APP_PASSWORD in .env or
        # in Streamlit secrets to switch the gate on. The Home page's
        # Configuration panel reports which mode is active.
        return True
    if st.session_state.get("_authed"):
        return True

    st.markdown("### 🔒 This app is password protected")
    st.caption("The corpus is a demo, but answer generation runs on the owner's "
               "Anthropic API key. Enter the shared password to continue.")
    with st.form("auth", clear_on_submit=False):
        pw = st.text_input("Password", type="password")
        ok = st.form_submit_button("Enter")
    if ok:
        if hmac.compare_digest(pw, expected):
            st.session_state["_authed"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False
