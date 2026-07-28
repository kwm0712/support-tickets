from __future__ import annotations

import pandas as pd
import streamlit as st

from ccs_core import (
    add_knowledge_article,
    authenticate,
    create_ticket,
    get_license_status,
    get_metrics,
    initialize_database,
    list_audit_entries,
    list_tickets,
    record_audit,
    search_knowledge,
    update_ticket,
)

st.set_page_config(
    page_title="CCS Agent Support",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_database()

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
      [data-testid="stMetricValue"] {font-size: 1.8rem;}
      .ccs-title {font-size: 2rem; font-weight: 750; margin-bottom: .15rem;}
      .ccs-subtitle {color: #52606d; margin-bottom: 1rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def login_view() -> None:
    st.markdown('<div class="ccs-title">Compelec AI Business Platform</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ccs-subtitle">CCS Agent Support · MVP Pilot</div>',
        unsafe_allow_html=True,
    )

    license_status = get_license_status()
    if license_status.valid:
        st.info(license_status.message)
    else:
        st.error(license_status.message)
        st.stop()

    with st.form("login_form"):
        username = st.text_input("Benutzername", value="admin")
        password = st.text_input("Kennwort", type="password")
        submitted = st.form_submit_button("Anmelden", use_container_width=True)

    with st.expander("MVP-Zugänge"):
        st.code(
            "admin / Compelec-Start!\n"
            "support / Support-Start!\n"
            "demo / Demo-Start!"
        )
        st.caption("Kennwörter vor einem realen Pilotbetrieb zwingend ändern.")

    if submitted:
        user = authenticate(username, password)
        if user:
            st.session_state.user = user
            record_audit(user["username"], "LOGIN", "session")
            st.rerun()
        st.error("Anmeldung fehlgeschlagen.")


if "user" not in st.session_state:
    login_view()
    st.stop()

user = st.session_state.user
license_status = get_license_status()

with st.sidebar:
    st.markdown("## CCS Agent Support")
    st.caption("Compelec AI Business Platform")
    st.write(f"**{user['display_name']}**")
    st.caption(f"Rolle: {user['role']}")
    st.divider()

    page = st.radio(
        "Navigation",
        ["Dashboard", "Tickets", "Wissensbasis", "KI-Assistent", "Audit"],
    )

    st.divider()
    if license_status.mode == "demo":
        st.warning("Demomodus")
    else:
        st.success("Lizenz aktiv")

    if st.button("Abmelden", use_container_width=True):
        record_audit(user["username"], "LOGOUT", "session")
        st.session_state.clear()
        st.rerun()

st.markdown('<div class="ccs-title">CCS Agent Support</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="ccs-subtitle">Kontrollierte Supportprozesse, Wissen und Nachvollziehbarkeit</div>',
    unsafe_allow_html=True,
)

if page == "Dashboard":
    metrics = get_metrics()
    columns = st.columns(5)
    columns[0].metric("Tickets gesamt", metrics["total"])
    columns[1].metric("Offen", metrics["open"])
    columns[2].metric("In Bearbeitung", metrics["active"])
    columns[3].metric("Kritisch", metrics["critical"])
    columns[4].metric("Wissensartikel", metrics["knowledge"])

    st.subheader("Operativer Überblick")
    tickets = list_tickets()
    if tickets:
        st.dataframe(
            pd.DataFrame(tickets)[
                ["ticket_no", "subject", "customer", "status", "priority", "assignee", "updated_at"]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Noch keine Tickets vorhanden.")

    st.subheader("MVP-Grenzen")
    st.write(
        "Dieser Stand ist ein belastbarer Pilotkern. Noch nicht enthalten sind "
        "Produktiv-SSO, PostgreSQL/pgvector, E-Mail-Integration, Signierung, "
        "mandantenfähige Rechteverwaltung und ein echter LLM-Provider."
    )

elif page == "Tickets":
    st.subheader("Ticket erfassen")
    if user["role"] == "viewer":
        st.info("Viewer dürfen Tickets einsehen, aber nicht verändern.")
    else:
        with st.form("create_ticket_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            customer = col1.text_input("Kunde / Organisation")
            priority = col2.selectbox("Priorität", ["Mittel", "Hoch", "Niedrig"])
            subject = st.text_input("Betreff")
            description = st.text_area("Fehlerbild / Anforderung", height=130)
            submitted = st.form_submit_button("Ticket anlegen")
        if submitted:
            try:
                ticket_no = create_ticket(
                    subject=subject,
                    description=description,
                    customer=customer,
                    priority=priority,
                    actor=user["username"],
                )
                st.success(f"Ticket {ticket_no} wurde angelegt.")
            except ValueError as exc:
                st.error(str(exc))

    st.subheader("Tickets bearbeiten")
    tickets = list_tickets()
    if not tickets:
        st.info("Noch keine Tickets vorhanden.")
    else:
        selected_ticket = st.selectbox(
            "Ticket auswählen",
            tickets,
            format_func=lambda item: f"{item['ticket_no']} · {item['subject']}",
        )
        st.write(selected_ticket["description"])
        col1, col2, col3 = st.columns(3)
        status = col1.selectbox(
            "Status",
            ["Offen", "In Bearbeitung", "Gelöst"],
            index=["Offen", "In Bearbeitung", "Gelöst"].index(selected_ticket["status"]),
            disabled=user["role"] == "viewer",
        )
        priority = col2.selectbox(
            "Priorität",
            ["Hoch", "Mittel", "Niedrig"],
            index=["Hoch", "Mittel", "Niedrig"].index(selected_ticket["priority"]),
            disabled=user["role"] == "viewer",
        )
        assignee = col3.text_input(
            "Bearbeiter",
            value=selected_ticket["assignee"] or "",
            disabled=user["role"] == "viewer",
        )
        if st.button("Änderungen speichern", disabled=user["role"] == "viewer"):
            update_ticket(
                ticket_no=selected_ticket["ticket_no"],
                status=status,
                priority=priority,
                assignee=assignee,
                actor=user["username"],
            )
            st.success("Ticket wurde aktualisiert.")
            st.rerun()

        with st.expander("Gesamtliste"):
            st.dataframe(pd.DataFrame(tickets), use_container_width=True, hide_index=True)

elif page == "Wissensbasis":
    st.subheader("Wissen durchsuchen")
    query = st.text_input("Suchbegriffe", placeholder="z. B. Datenbank Verbindung")
    results = search_knowledge(query)

    if results:
        for article in results:
            with st.expander(f"{article['title']} · {article['category']}"):
                st.write(article["content"])
                st.caption(
                    f"Quelle: {article.get('source') or 'nicht angegeben'} · "
                    f"Erfasst von: {article['created_by']}"
                )
    else:
        st.warning("Keine passenden Wissenseinträge gefunden.")

    if user["role"] == "admin":
        st.subheader("Wissensartikel ergänzen")
        with st.form("knowledge_form", clear_on_submit=True):
            title = st.text_input("Titel")
            col1, col2 = st.columns(2)
            category = col1.text_input("Kategorie", value="Support")
            source = col2.text_input("Quelle")
            content = st.text_area("Inhalt", height=150)
            submitted = st.form_submit_button("Artikel speichern")
        if submitted:
            try:
                article_id = add_knowledge_article(
                    title=title,
                    category=category,
                    content=content,
                    source=source,
                    actor=user["username"],
                )
                st.success(f"Wissensartikel {article_id} wurde gespeichert.")
            except ValueError as exc:
                st.error(str(exc))

elif page == "KI-Assistent":
    st.subheader("Kontrollierter Support-Assistent")
    st.info(
        "Der MVP arbeitet bewusst ohne externen KI-Provider. Er liefert nachvollziehbare "
        "Antwortentwürfe ausschließlich aus der lokalen Wissensbasis."
    )
    question = st.text_area(
        "Supportfrage",
        placeholder="Beschreibe das Problem und den gewünschten nächsten Schritt.",
        height=130,
    )
    if st.button("Antwortentwurf erzeugen"):
        results = search_knowledge(question)
        record_audit(
            user["username"],
            "GENERATE_DRAFT",
            "assistant",
            details=question[:500],
        )
        if not results:
            st.warning(
                "Kein belastbarer Wissensbezug gefunden. Fall als Ticket erfassen und "
                "fachlich prüfen lassen."
            )
        else:
            top_results = results[:3]
            st.markdown("### Antwortentwurf")
            st.write(
                "Auf Basis der freigegebenen Wissensbasis sollten zunächst folgende "
                "Prüfschritte durchgeführt werden:"
            )
            for index, article in enumerate(top_results, start=1):
                st.write(f"{index}. **{article['title']}** – {article['content']}")
            st.warning(
                "Vor Versand fachlich prüfen. Der Entwurf ersetzt keine technische "
                "Freigabe und führt keine Aktionen selbstständig aus."
            )

elif page == "Audit":
    st.subheader("Audit-Protokoll")
    if user["role"] != "admin":
        st.warning("Das Audit-Protokoll ist nur für Administratoren sichtbar.")
    else:
        entries = list_audit_entries()
        if entries:
            st.dataframe(pd.DataFrame(entries), use_container_width=True, hide_index=True)
        else:
            st.info("Noch keine Audit-Einträge vorhanden.")
