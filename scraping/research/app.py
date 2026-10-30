import asyncio

import streamlit as st

from scraping.research.adapter import search_query


def validate_query(query: str) -> str:
    """Return the trimmed query if it contains at least two letters."""
    query = query.strip()

    # Count letters rather than all characters, so numbers alone cannot pass.
    letter_count = 0
    for character in query:
        if character.isalpha():
            letter_count += 1

    if letter_count < 2:
        raise ValueError("Enter a search query containing at least two letters.")
    return query


def main() -> None:
    """Search public sources and count the selected result rows."""

    st.set_page_config(page_title="MedBrief research", layout="wide")
    st.title("MedBrief research")
    st.caption("Search public sources and select links for later export.")

    # Initialize once; checkbox clicks must not erase the saved search.
    if "research_index" not in st.session_state:
        st.session_state["research_index"] = None
        st.session_state["research_table_version"] = 0

    query = st.text_input("Search query", key="research_query")
    # Validate only when Search is clicked, not when the table selection changes.
    if st.button("Search"):
        try:
            cleaned_query = validate_query(query)
        except ValueError as error:
            st.error(str(error))
        else:
            # Replace the old search and reset selection, even for an empty answer.
            st.session_state["research_index"] = None
            st.session_state["research_table_version"] += 1
            try:
                with st.spinner("Searching..."):
                    st.session_state["research_index"] = asyncio.run(search_query(cleaned_query))
            except Exception as error:
                # Keep unexpected search errors visible on subsequent checkbox reruns too.
                st.session_state["research_index"] = {
                    "results": [], "status": "failed", "error": str(error),
                }

    index = st.session_state["research_index"]
    results = index["results"] if index is not None else []
    if index is not None:
        if index["status"] == "failed":
            st.error(index["error"] or "Search failed.")
        elif index["status"] == "partial":
            st.warning(index["error"] or "Some search sources failed. Results may be incomplete.")
        elif index["status"] == "empty":
            st.info("No results found.")

    # Reserve a place above the table; we can fill it after reading the selection.
    count_placeholder = st.empty()
    # Let the table track selection while the article details stay read-only.
    selection_event = st.dataframe(
        results,
        hide_index=True,
        key=f"research_row_selection_{st.session_state['research_table_version']}",
        on_select="rerun",
        selection_mode="multi-row",
        alt="Public research results with row selection and source links.",
        column_config={
            "id": "ID",
            "title": "Title",
            "url": st.column_config.LinkColumn("Source", display_text="Open source"),
            "snippet": "Description",
        },
    )

    # The table returns selected row positions; the list length is our count.
    selected_rows = selection_event["selection"]["rows"]
    count = len(selected_rows)
    count_placeholder.write(f"Selected: {count}")


if __name__ == "__main__":
    main()
