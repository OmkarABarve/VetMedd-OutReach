"""
dashboard.py - Streamlit monitoring dashboard for the outreach pipeline.

Run with:  streamlit run dashboard.py

Read-only: it never writes to the contacts file. It reads the current contacts
sheet and logs/outreach_log.csv to show metrics, tables, charts, and filters.
"""

import pandas as pd
import streamlit as st

import config
import loader


st.set_page_config(page_title="VetApp Outreach Dashboard", page_icon="🐾", layout="wide")


@st.cache_data(ttl=10)
def _load_contacts():
    try:
        df, path = loader.load_contacts()
        return df, path.name
    except Exception as exc:
        return None, str(exc)


@st.cache_data(ttl=10)
def _load_log():
    if not config.LOG_FILE.exists():
        return pd.DataFrame(columns=updater_header())
    return pd.read_csv(config.LOG_FILE)


def updater_header():
    from updater import LOG_HEADER

    return LOG_HEADER


def main():
    st.title("🐾 VetApp GTM Outreach Dashboard")

    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()

    contacts, contacts_name = _load_contacts()
    if contacts is None:
        st.error(f"Could not load contacts: {contacts_name}")
        st.stop()

    log = _load_log()

    # --- Top metrics -------------------------------------------------------
    total_companies = len(contacts)
    contacted = int((contacts["Times Communicated"] > 0).sum())
    do_not_message = int(contacts["Don't Message"].sum())

    sent = skipped = failed = 0
    if not log.empty:
        sent = int((log["status"] == "sent").sum())
        skipped = int(log["status"].str.startswith("skipped").sum())
        failed = int((log["status"] == "failed").sum())

    # Response rate = contacts with a reply / contacts contacted.
    replied = int(contacts["Responses"].apply(loader.response_count).gt(0).sum())
    response_rate = (replied / contacted * 100) if contacted else 0.0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total companies", total_companies)
    c2.metric("Contacted", contacted)
    c3.metric("Total sent (log)", sent)
    c4.metric("Skipped (log)", skipped)
    c5.metric("Failed (log)", failed)
    c6.metric("Response rate", f"{response_rate:.0f}%")

    st.divider()

    # --- Filters -----------------------------------------------------------
    st.subheader("Contacts")
    f1, f2, f3 = st.columns([2, 2, 3])

    classes = ["(all)"] + sorted(c for c in contacts["Classification"].unique() if c)
    sel_class = f1.selectbox("Classification", classes)

    dont_filter = f2.selectbox("Don't Message", ["(all)", "Only flagged", "Hide flagged"])
    search = f3.text_input("Search company name")

    view = contacts.copy()
    if sel_class != "(all)":
        view = view[view["Classification"] == sel_class]
    if dont_filter == "Only flagged":
        view = view[view["Don't Message"]]
    elif dont_filter == "Hide flagged":
        view = view[~view["Don't Message"]]
    if search:
        view = view[view["Company Name"].str.contains(search, case=False, na=False)]

    st.dataframe(view, use_container_width=True)

    st.divider()

    # --- Charts ------------------------------------------------------------
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Contacts by classification")
        by_class = contacts["Classification"].replace("", "(unknown)").value_counts()
        st.bar_chart(by_class)

    with col_b:
        st.subheader("Log status breakdown")
        if not log.empty:
            st.bar_chart(log["status"].value_counts())
        else:
            st.info("No actions logged yet. Run `python main.py` first.")

    if not log.empty and "channel" in log.columns:
        st.subheader("Sends by channel")
        sent_log = log[log["status"] == "sent"]
        if not sent_log.empty:
            st.bar_chart(sent_log["channel"].value_counts())

    st.divider()

    # --- Recent log --------------------------------------------------------
    st.subheader("Recent activity log")
    if log.empty:
        st.info("logs/outreach_log.csv is empty.")
    else:
        st.dataframe(log.iloc[::-1], use_container_width=True)


if __name__ == "__main__":
    main()
