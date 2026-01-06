from typing import Iterable, List, Optional

import streamlit as st

_EMPTY_LABEL = "(empty)"
_ADD_LABEL = "Add new..."
_NO_MATCHES = "(no matches)"


def typeahead_multi_select(label: str, options: Iterable[str], key: str) -> List[Optional[str]]:
    state_key = f"{key}_selected"
    if state_key not in st.session_state:
        st.session_state[state_key] = []

    option_list = list(options)
    search = st.text_input(f"Search {label}", key=f"{key}_search")
    filtered = [opt for opt in option_list if search.lower() in opt.lower()]
    display_options = filtered if filtered else [_NO_MATCHES]

    selection = st.selectbox(f"Add {label}", display_options, key=f"{key}_select")
    if st.button(f"Add {label}", key=f"{key}_add"):
        if selection != _NO_MATCHES and selection not in st.session_state[state_key]:
            st.session_state[state_key].append(selection)

    selected: List[str] = st.session_state[state_key]
    if selected:
        remove_choice = st.selectbox(f"Remove {label}", selected, key=f"{key}_remove")
        if st.button(f"Remove selected {label}", key=f"{key}_remove_btn"):
            st.session_state[state_key] = [item for item in selected if item != remove_choice]

    if st.button(f"Clear {label}", key=f"{key}_clear"):
        st.session_state[state_key] = []

    return list(st.session_state[state_key])


def typeahead_single_select(
    label: str,
    options: Iterable[str],
    key: str,
    include_empty: bool = True,
) -> Optional[str]:
    option_list = list(options)
    search = st.text_input(f"Search {label}", key=f"{key}_search")
    filtered = [opt for opt in option_list if search.lower() in opt.lower()]
    display_options = filtered if filtered else [_NO_MATCHES]
    if include_empty:
        display_options = [_EMPTY_LABEL] + display_options

    selection = st.selectbox(label, display_options, key=f"{key}_select")
    if selection in (_NO_MATCHES, _EMPTY_LABEL):
        return None
    return selection


def select_or_add(
    label: str,
    options: Iterable[str],
    key: str,
    allow_empty: bool = True,
    current: Optional[str] = None,
) -> Optional[str]:
    option_list = list(options)
    if current and current not in option_list:
        option_list.insert(0, current)
    choices: List[str] = []
    if allow_empty:
        choices.append(_EMPTY_LABEL)
    choices.extend(option_list)
    choices.append(_ADD_LABEL)

    if current is None and allow_empty:
        index = 0
    elif current in choices:
        index = choices.index(current)
    else:
        index = 0

    selection = st.selectbox(label, choices, index=index, key=key)
    if selection == _ADD_LABEL:
        new_value = st.text_input(f"New {label}", key=f"{key}_new")
        return new_value.strip() or None
    if selection == _EMPTY_LABEL:
        return None
    return selection
