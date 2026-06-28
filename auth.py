import os

import streamlit as st


def _check_password(entered: str) -> bool:
    try:
        expected = st.secrets.get("APP_PASSWORD") or os.environ.get("APP_PASSWORD", "")
    except Exception:
        expected = os.environ.get("APP_PASSWORD", "")
    return bool(expected) and entered == expected


def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)


def show_sidebar_login():
    with st.sidebar:
        if is_authenticated():
            if st.button("Log out", key="sidebar_logout"):
                st.session_state["authenticated"] = False
                st.rerun()
        else:
            st.subheader("Login")
            pwd = st.text_input("Password", type="password", key="sidebar_pwd")
            if st.button("Log in", key="sidebar_login_btn"):
                if _check_password(pwd):
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Wrong password")


def show_inline_login():
    st.subheader("Login required to add expenses")
    pwd = st.text_input("Password", type="password", key="inline_pwd")
    if st.button("Log in", key="inline_login_btn"):
        if _check_password(pwd):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Wrong password")
    st.stop()
