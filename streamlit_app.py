from __future__ import annotations

import pandas as pd
import streamlit as st

from ccs_core import (
    authenticate,
    create_ticket,
    get_license_status,
    get_metrics,
    initialize_database,
    list_audit_entries,
    list_tickets,
    record_audit,
    update_ticket,
)
from knowledge_ai import (
    APPROVAL_STATUSES,
    PRIVACY_LEVELS,
    add_governed_article,
    generate_assistant_answer,
    import_document,
    initialize_knowledge_ai,
    list_assistant_runs,
    list_documents,
    list_governed_articles,
    search_governed_knowledge,
    set_article_status,
    set_document_status,
)

st.set_page_config(
    page_title="CCS Agent Support",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_database()
initialize_knowledge_ai()

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
      [data-testid="stMetricValue"] {font-size: 1.8rem;}
      .ccs-title {font-size: 2rem; font-weight: 750; margin-bottom: .15rem;}
      .ccs-subtitle {color: #52606d; margin-bottom: 1rem;}
      .ccs-badge {display:inline-block; padding:.2rem .55rem; border-radius:.4rem;
                  background:#e8f3fa; margin-right:.35rem; font-size:.82rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

STATUS_LABELS = {
    "draft": "Entwurf",
    "approved": "Freigegeben",
    "rejected": "Abgelehnt",
}
PRIVACY_LABELS = {
    "public": "Öffentlich",
    "internal": "Intern",
    "confidential": "Vertraulich",
}


def login_view() -> None:
    st.markdown('<div class="ccs-title">Compelec AI Business Platform</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ccs-subtitle">CCS Agent Support · Knowledge & AI Core 0.2</div>',
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
    st.caption("Compelec AI Business Platform · 0.2.0")
    st.write(f"**{user['display_name']}**")
    st.caption(f"Rolle: {user['role']}")
    st.divider()

    page = st.radio(
        "Navigation",
        ["Dashboard", "Tickets", "Wissensbasis", "Dokumente", "KI-Assistent", "Audit"],
    )

    st.divider()
    if license_status.mode == "demo":
        st.warning("Demomodus")
    else:
        st.success("Lizenz aktiv")

    st.caption("Aktiver Provider: local-evidence")
    if st.button("Abmelden", use_container_width=True):
        record_audit(user["username"], "LOGOUT", "session")
        st.session_state.clear()
        st.rerun()

st.markdown('<div class="ccs-title">CCS Agent Support</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="ccs-subtitle">Kontrollierte Supportprozesse, Wissen und quellengebundene Assistenz</div>',
    unsafe_allow_html=True,
)

if page == "Dashboard":
    metrics = get_metrics()
    documents = list_documents()
    articles = list_governed_articles(include_unapproved=True)
    assistant_runs = list_assistant_runs(limit=500)
    approved_sources = sum(1 for item in documents if item["approval_status"] == "approved")
    approved_sources += sum(1 for item in articles if item["approval_status"] == "approved")

    columns = st.columns(6)
    columns[0].metric("Tickets gesamt", metrics["total"])
    columns[1].metric("Offen", metrics["open"])
    columns[2].metric("In Bearbeitung", metrics["active"])
    columns[3].metric("Kritisch", metrics["critical"])
    columns[4].metric("Freigegebene Quellen", approved_sources)
    columns[5].metric("Assistenzläufe", len(assistant_runs))

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

    st.subheader("Governance-Status")
    pending_documents = sum(1 for item in documents if item["approval_status"] == "draft")
    pending_articles = sum(1 for item in articles if item["approval_status"] == "draft")
    col1, col2, col3 = st.columns(3)
    col1.metric("Dokumente zur Prüfung", pending_documents)
    col2.metric("Artikel zur Prüfung", pending_articles)
    col3.metric("Aktiver KI-Provider", "Lokal")
    st.info(
        "Version 0.2 nutzt ausschließlich lokal gespeicherte und freigegebene Quellen. "
        "Externe KI-Aufrufe sind technisch nicht aktiviert."
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
    st.subheader("Freigegebenes Wissen durchsuchen")
    col1, col2 = st.columns([3, 1])
    query = col1.text_input("Suchbegriffe", placeholder="z. B. Datenbank Verbindung")
    privacy_level = col2.selectbox(
        "Max. Datenschutzstufe",
        PRIVACY_LEVELS,
        index=1,
        format_func=lambda value: PRIVACY_LABELS[value],
    )
    results = search_governed_knowledge(query, privacy_level=privacy_level)

    if results:
        for article in results:
            with st.expander(f"{article['title']} · {article['category']}"):
                st.write(article["content"])
                st.caption(
                    f"Quelle: {article.get('source') or 'nicht angegeben'} · "
                    f"Datenschutz: {PRIVACY_LABELS[article['privacy_level']]} · "
                    f"Status: {STATUS_LABELS[article['approval_status']]}"
                )
    else:
        st.warning("Keine passenden freigegebenen Wissenseinträge gefunden.")

    if user["role"] == "admin":
        st.subheader("Wissensartikel erfassen")
        with st.form("knowledge_form", clear_on_submit=True):
            title = st.text_input("Titel")
            col1, col2 = st.columns(2)
            category = col1.text_input("Kategorie", value="Support")
            source = col2.text_input("Quelle")
            col3, col4 = st.columns(2)
            approval_status = col3.selectbox(
                "Freigabestatus",
                APPROVAL_STATUSES,
                index=0,
                format_func=lambda value: STATUS_LABELS[value],
            )
            article_privacy = col4.selectbox(
                "Datenschutzstufe",
                PRIVACY_LEVELS,
                index=1,
                format_func=lambda value: PRIVACY_LABELS[value],
            )
            content = st.text_area("Inhalt", height=150)
            submitted = st.form_submit_button("Artikel speichern")
        if submitted:
            try:
                article_id = add_governed_article(
                    title=title,
                    category=category,
                    content=content,
                    source=source,
                    approval_status=approval_status,
                    privacy_level=article_privacy,
                    actor=user["username"],
                )
                st.success(f"Wissensartikel {article_id} wurde gespeichert.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

        all_articles = list_governed_articles(include_unapproved=True)
        if all_articles:
            st.subheader("Artikelprüfung")
            selected = st.selectbox(
                "Artikel auswählen",
                all_articles,
                format_func=lambda item: (
                    f"#{item['id']} · {item['title']} · {STATUS_LABELS[item['approval_status']]}"
                ),
            )
            new_status = st.selectbox(
                "Neuer Status",
                APPROVAL_STATUSES,
                index=APPROVAL_STATUSES.index(selected["approval_status"]),
                format_func=lambda value: STATUS_LABELS[value],
                key="article_status",
            )
            if st.button("Artikelstatus speichern"):
                set_article_status(selected["id"], new_status, user["username"])
                st.success("Freigabestatus wurde aktualisiert.")
                st.rerun()

elif page == "Dokumente":
    st.subheader("Dokumenten-RAG vorbereiten")
    st.write(
        "TXT-, PDF- und DOCX-Dateien werden lokal extrahiert, segmentiert und zunächst als "
        "Entwurf gespeichert. Erst freigegebene Dokumente stehen dem Assistenten zur Verfügung."
    )

    if user["role"] == "admin":
        with st.form("document_import_form", clear_on_submit=True):
            uploaded = st.file_uploader("Dokument", type=["txt", "pdf", "docx"])
            col1, col2 = st.columns(2)
            category = col1.text_input("Kategorie", value="Support")
            source = col2.text_input("Quellenbezeichnung")
            document_privacy = st.selectbox(
                "Datenschutzstufe",
                PRIVACY_LEVELS,
                index=1,
                format_func=lambda value: PRIVACY_LABELS[value],
            )
            submitted = st.form_submit_button("Dokument importieren")
        if submitted:
            if uploaded is None:
                st.error("Bitte ein Dokument auswählen.")
            else:
                try:
                    document_id = import_document(
                        filename=uploaded.name,
                        data=uploaded.getvalue(),
                        category=category,
                        source=source,
                        privacy_level=document_privacy,
                        actor=user["username"],
                    )
                    st.success(f"Dokument {document_id} wurde als Entwurf importiert.")
                    st.rerun()
                except (ValueError, RuntimeError) as exc:
                    st.error(str(exc))
    else:
        st.info("Dokumentimport und Freigabe sind Administratoren vorbehalten.")

    documents = list_documents()
    if not documents:
        st.info("Noch keine Dokumente importiert.")
    else:
        st.dataframe(pd.DataFrame(documents), use_container_width=True, hide_index=True)
        if user["role"] == "admin":
            selected_document = st.selectbox(
                "Dokument zur Prüfung",
                documents,
                format_func=lambda item: (
                    f"#{item['id']} · {item['filename']} · {STATUS_LABELS[item['approval_status']]}"
                ),
            )
            document_status = st.selectbox(
                "Neuer Dokumentstatus",
                APPROVAL_STATUSES,
                index=APPROVAL_STATUSES.index(selected_document["approval_status"]),
                format_func=lambda value: STATUS_LABELS[value],
            )
            if st.button("Dokumentstatus speichern"):
                set_document_status(selected_document["id"], document_status, user["username"])
                st.success("Dokumentstatus wurde aktualisiert.")
                st.rerun()

elif page == "KI-Assistent":
    st.subheader("Quellengebundener Support-Assistent")
    st.info(
        "Aktiver Provider: local-evidence. Es erfolgt kein externer API-Aufruf. "
        "Verwendet werden ausschließlich freigegebene Quellen innerhalb der gewählten Datenschutzstufe."
    )
    privacy_level = st.selectbox(
        "Datenschutzstufe der Anfrage",
        PRIVACY_LEVELS,
        index=1,
        format_func=lambda value: PRIVACY_LABELS[value],
    )
    question = st.text_area(
        "Supportfrage",
        placeholder="Beschreibe das Problem und den gewünschten nächsten Schritt.",
        height=130,
    )
    if st.button("Antwortentwurf erzeugen"):
        try:
            response = generate_assistant_answer(
                question=question,
                privacy_level=privacy_level,
                actor=user["username"],
            )
            st.markdown("### Antwortentwurf")
            st.markdown(response.answer)
            st.caption(
                f"Lauf #{response.run_id} · Provider: {response.provider} · "
                f"Datenschutz: {PRIVACY_LABELS[response.privacy_level]}"
            )
            if response.evidence:
                st.markdown("### Verwendete Quellen")
                for index, evidence in enumerate(response.evidence, start=1):
                    with st.expander(f"{index}. {evidence.title} · Score {evidence.score}"):
                        st.write(evidence.content)
                        st.caption(
                            f"Quelle: {evidence.source} · Typ: {evidence.source_type} · "
                            f"Datenschutz: {PRIVACY_LABELS[evidence.privacy_level]}"
                        )
        except ValueError as exc:
            st.error(str(exc))

    if user["role"] == "admin":
        runs = list_assistant_runs(limit=50)
        if runs:
            with st.expander("Letzte Assistenzläufe"):
                st.dataframe(pd.DataFrame(runs), use_container_width=True, hide_index=True)

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
