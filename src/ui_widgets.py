from typing import Dict, Iterable, List, Optional, Tuple

import streamlit as st

_NO_MATCHES = "(no matches)"
_NONE = "(none)"
_NAV_ITEMS = (
    ("app.py", "HOME"),
    ("pages/1_Tutorial.py", "Tutorial"),
    ("pages/2_Transactions.py", "Transactions"),
    ("pages/3_Import_Export.py", "Import Export"),
    ("pages/4_Manage_Values.py", "Manage Values"),
    ("pages/5_Compare.py", "Compare"),
)


def render_sidebar_nav() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] { display: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    for path, label in _NAV_ITEMS:
        _page_link(path, label)


def _page_link(path: str, label: str) -> None:
    if hasattr(st.sidebar, "page_link"):
        st.sidebar.page_link(path, label=label)
        return
    if hasattr(st, "page_link"):
        with st.sidebar:
            st.page_link(path, label=label)
        return
    if hasattr(st, "switch_page"):
        if st.sidebar.button(label):
            st.switch_page(path)
        return
    st.sidebar.write(label)


def select_or_create(
    label: str,
    options: Iterable[str],
    key: str,
    value: Optional[str] = None,
    allow_empty: bool = True,
) -> Tuple[Optional[str], bool]:
    input_key = f"{key}_input"
    if value is not None and input_key not in st.session_state:
        st.session_state[input_key] = value

    raw_value = st.text_input(label, key=input_key)
    normalized = _normalize_value(raw_value)

    options_list = list(options)
    normalized_options = {opt.lower() for opt in options_list}

    search = normalized or ""
    suggestions = [opt for opt in options_list if search in opt.lower()]
    if not suggestions:
        suggestions = [_NO_MATCHES]
    if allow_empty:
        suggestions = [_NONE] + suggestions

    selection = st.selectbox(
        f"{label} suggestions",
        suggestions,
        key=f"{key}_suggest",
    )

    is_new = False
    chosen_value: Optional[str] = None
    if normalized:
        chosen_value = normalized
        is_new = normalized not in normalized_options
        if is_new:
            st.caption(f"Will create new value: {normalized}")
    elif selection not in {_NO_MATCHES, _NONE}:
        chosen_value = selection
        st.caption(f"Using suggestion: {selection}")

    if not chosen_value:
        return (None if allow_empty else None), False
    return chosen_value, is_new


def select_existing(
    label: str,
    options: Iterable[str],
    key: str,
    allow_empty: bool = True,
) -> Optional[str]:
    search = st.text_input(f"Search {label}", key=f"{key}_search")
    filtered = _filter_options(options, search)
    choices = filtered if filtered else [_NO_MATCHES]
    if allow_empty:
        choices = [_NONE] + choices
    selection = st.selectbox(label, choices, key=key)
    if selection in {_NO_MATCHES, _NONE}:
        return None
    return selection


def multiselect_existing(label: str, options: Iterable[str], key: str) -> List[str]:
    selected = st.session_state.get(key, [])
    option_list = list(options)
    if selected:
        for item in selected:
            if item not in option_list:
                option_list.append(item)
    return st.multiselect(label, options=option_list, default=selected, key=key)


def tags_assign(label: str, options: Iterable[str], key: str) -> Tuple[List[str], str]:
    selected = multiselect_existing(label, options, key=f"{key}_selected")
    new_tag = st.text_input("Add new tag", key=f"{key}_new")
    return selected, new_tag


def tags_filter(label: str, options: Iterable[str], key: str) -> List[str]:
    return multiselect_existing(label, options, key=key)


def subcategory_label_map(
    pairs: Iterable[Tuple[str, str]], categories: Iterable[str]
) -> Tuple[List[str], Dict[str, Tuple[str, str]]]:
    category_list = list(categories)
    filtered = (
        [pair for pair in pairs if pair[0] in category_list] if category_list else list(pairs)
    )
    labels: List[str] = []
    label_map: Dict[str, Tuple[str, str]] = {}
    for category, subcategory in filtered:
        label = f"{category} / {subcategory}"
        label_map[label] = (category, subcategory)
        labels.append(label)
    return labels, label_map


def _normalize_value(value: str) -> str:
    return value.strip().lower()


def _filter_options(options: Iterable[str], search: str) -> List[str]:
    search_clean = (search or "").strip().lower()
    options_list = list(options)
    if not search_clean:
        return options_list
    return [opt for opt in options_list if search_clean in opt.lower()]
