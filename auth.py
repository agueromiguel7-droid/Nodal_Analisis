import streamlit as st

def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        user_pw = st.session_state.get("password", "")
        if user_pw == st.secrets.get("password", "nodal2026"):
            st.session_state["password_correct"] = True
            if "password" in st.session_state:
                del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Ingrese Contraseña para Nodal Analysis Pro", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Ingrese Contraseña para Nodal Analysis Pro", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Contraseña incorrecta")
        return False
    else:
        # Password correct.
        return True
