from __future__ import annotations

import pandas as pd
import streamlit as st

from architecture import AuthorizationError
from ccs_core import authenticate, get_license_status, initialize_database, record_audit
from v03_runtime import build_support_service


st.set_page_config(
    page_title="CCS Agent Support V0.3",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

STATUS_LABELS = {
    "draft": "Entwurf",
    "approved": "Freigegeben",
    "rejected": "Abgelehnt",
}
PRIVACY_LEVELS = ("public", "internal", "confidential")
PRIVACY_LABELS = {
    "public": "Öffentlich",
    "internal": "Intern",
    "confidential": "Vertraulich",
}


def login_view() -> None:
    st.title("CCS Agent Support V0.3")
    st.caption("PostgreSQL · pgvector · Tenant/RBAC Architecture")
    license_status = get_license_status()
    if not license_status.valid:
        st.error(license_status.message)
        st.stop()
    st.info(license_status.message)

    with st.form("login_v03"):
        username = st.text_input("Benutzername", value="admin")
        password = st.text_input("Kennwort", type="password")
        submitted = st.form_submit_button("Anmelden", use_container_width=True)

    if license_status.mode == "demo":
        with st.expander("MVP-Zugänge"):
            st.code(
                "admin / Compelec-Start!\n"
                "support / Support-Start!\n"
                "demo / Demo-Start!"
            )
            st.caption("Lokale Identität bleibt in V0.3 als SSO-Kompatibilitätspfad bestehen.")

    if submitted:
        user = authenticate(username, password)
        if user:
            st.session_state.user = user
            record_audit(user["username"], "LOGIN", "session", details="V0.3 client")
            st.rerun()
        st.error("Anmeldung fehlgeschlagen.")


try:
    initialize_database()
except RuntimeError as exc:
    st.error(f"Sicherheits- oder Konfigurationsfehler: {exc}")
    st.stop()

if "user" not in st.session_state:
    login_view()
    st.stop()

user = st.session_state.user
try:
    service = build_support_service(user)
except Exception as exc:
    st.error(f"V0.3 PostgreSQL-Laufzeit konnte nicht initialisiert werden: {exc}")
    st.stop()

with st.sidebar:
    st.markdown("## CCS Agent Support")
    st.caption("V0.3.0-dev · PostgreSQL/pgvector")
    st.write(f"**{user['display_name']}**")
    st.caption(f"Rolle: {user['role']}")
    st.caption(f"Datenschutzobergrenze: {PRIVACY_LABELS[service.privacy_ceiling]}")
    st.divider()
    page = st.radio(
        "Navigation",
        ["Dashboard", "Tickets", "Wissensbasis", "Dokumente", "KI-Assistent", "Audit"],
    )
    st.divider()
    st.success("PostgreSQL aktiv")
    st.caption("Embedding: ccs-local-hash-v1 · lokal")
    if st.button("Abmelden", use_container_width=True):
        record_audit(user["username"], "LOGOUT", "session", details="V0.3 client")
        st.session_state.clear()
        st.rerun()

st.title("CCS Agent Support V0.3")
st.caption("Service-/Repository-Architektur mit tenant-sicherem Hybrid Retrieval")

try:
    if page == "Dashboard":
        metrics = service.get_metrics()
        columns = st.columns(6)
        columns[0].metric("Tickets", metrics["total"])
        columns[1].metric("Offen", metrics["open"])
        columns[2].metric("In Bearbeitung", metrics["active"])
        columns[3].metric("Kritisch", metrics["critical"])
        columns[4].metric("Wissen", metrics["knowledge"])
        columns[5].metric("Dokumente", metrics["documents"])
        tickets = service.list_tickets()
        if tickets:
            st.dataframe(pd.DataFrame(tickets), use_container_width=True, hide_index=True)
        else:
            st.info("Noch keine Tickets im aktiven Mandanten.")
        st.info(
            "V0.3 erzwingt Rollen-, Datenschutz- und Mandantengrenzen in der "
            "Service-/Repository-Schicht. Streamlit ist nur Präsentationsschicht."
        )

    elif page == "Tickets":
        st.subheader("Ticket erfassen")
        with st.form("ticket_v03", clear_on_submit=True):
            customer = st.text_input("Kunde / Organisation")
            priority = st.selectbox("Priorität", ["Mittel", "Hoch", "Niedrig"])
            subject = st.text_input("Betreff")
            description = st.text_area("Fehlerbild / Anforderung", height=120)
            submitted = st.form_submit_button("Ticket anlegen")
        if submitted:
            ticket_no = service.create_ticket(
                subject=subject,
                description=description,
                customer=customer,
                priority=priority,
            )
            st.success(f"Ticket {ticket_no} wurde angelegt.")
            st.rerun()

        tickets = service.list_tickets()
        if tickets:
            selected = st.selectbox(
                "Ticket auswählen",
                tickets,
                format_func=lambda item: f"{item['ticket_no']} · {item['subject']}",
            )
            col1, col2, col3 = st.columns(3)
            status = col1.selectbox(
                "Status",
                ["Offen", "In Bearbeitung", "Gelöst"],
                index=["Offen", "In Bearbeitung", "Gelöst"].index(selected["status"]),
            )
            priority = col2.selectbox(
                "Priorität",
                ["Hoch", "Mittel", "Niedrig"],
                index=["Hoch", "Mittel", "Niedrig"].index(selected["priority"]),
            )
            assignee = col3.text_input("Bearbeiter", value=selected["assignee"] or "")
            if st.button("Ticketänderungen speichern"):
                service.update_ticket(
                    ticket_no=selected["ticket_no"],
                    status=status,
                    priority=priority,
                    assignee=assignee,
                )
                st.success("Ticket wurde aktualisiert.")
                st.rerun()
            with st.expander("Gesamtliste"):
                st.dataframe(pd.DataFrame(tickets), use_container_width=True, hide_index=True)
        else:
            st.info("Noch keine Tickets vorhanden.")

    elif page == "Wissensbasis":
        st.subheader("Hybrid Retrieval")
        query = st.text_input("Suchfrage", placeholder="z. B. Datenbank Verbindung prüfen")
        privacy = st.selectbox(
            "Datenschutzstufe",
            PRIVACY_LEVELS,
            index=PRIVACY_LEVELS.index(service.privacy_ceiling),
            format_func=lambda value: PRIVACY_LABELS[value],
        )
        if query:
            evidence = service.search_evidence(query, privacy_level=privacy, limit=10)
            if evidence:
                for item in evidence:
                    with st.expander(
                        f"{item['title']} · Score {item['combined_score']:.3f}"
                    ):
                        st.write(item["content"])
                        st.caption(
                            f"Typ: {item['source_type']} · Quelle: {item['source']} · "
                            f"Lexikalisch: {item['lexical_score']:.3f} · "
                            f"Vektor: {item['vector_score']:.3f}"
                        )
            else:
                st.warning("Keine freigegebene Evidenz gefunden.")

        if user["role"] == "admin":
            st.subheader("Wissensartikel erfassen")
            with st.form("knowledge_v03", clear_on_submit=True):
                title = st.text_input("Titel")
                category = st.text_input("Kategorie", value="Support")
                source = st.text_input("Quelle")
                article_privacy = st.selectbox(
                    "Datenschutz",
                    PRIVACY_LEVELS,
                    index=1,
                    format_func=lambda value: PRIVACY_LABELS[value],
                )
                content = st.text_area("Inhalt", height=130)
                save = st.form_submit_button("Als Entwurf speichern")
            if save:
                article_id = service.add_article(
                    title=title,
                    category=category,
                    content=content,
                    source=source,
                    privacy_level=article_privacy,
                )
                st.success(f"Artikel #{article_id} wurde als Entwurf gespeichert.")
                st.rerun()

            articles = service.list_articles(include_unapproved=True)
            if articles:
                selected = st.selectbox(
                    "Artikelprüfung",
                    articles,
                    format_func=lambda item: (
                        f"#{item['id']} · {item['title']} · "
                        f"{STATUS_LABELS[item['approval_status']]}"
                    ),
                )
                status = st.selectbox(
                    "Neuer Status",
                    ["draft", "approved", "rejected"],
                    index=["draft", "approved", "rejected"].index(
                        selected["approval_status"]
                    ),
                    format_func=lambda value: STATUS_LABELS[value],
                )
                if st.button("Artikelstatus speichern"):
                    service.review_article(selected["id"], status)
                    st.success("Artikelstatus wurde aktualisiert.")
                    st.rerun()

    elif page == "Dokumente":
        st.subheader("Dokumentenimport mit Embedding")
        if user["role"] == "admin":
            with st.form("document_v03", clear_on_submit=True):
                uploaded = st.file_uploader("Dokument", type=["txt", "pdf", "docx"])
                category = st.text_input("Kategorie", value="Support")
                source = st.text_input("Quellenbezeichnung")
                privacy = st.selectbox(
                    "Datenschutzstufe",
                    PRIVACY_LEVELS,
                    index=1,
                    format_func=lambda value: PRIVACY_LABELS[value],
                )
                save = st.form_submit_button("Importieren")
            if save:
                if uploaded is None:
                    st.error("Bitte ein Dokument auswählen.")
                else:
                    document_id = service.import_document(
                        filename=uploaded.name,
                        data=uploaded.getvalue(),
                        category=category,
                        source=source,
                        privacy_level=privacy,
                    )
                    st.success(f"Dokument #{document_id} wurde als Entwurf importiert.")
                    st.rerun()

        documents = service.list_documents()
        if documents:
            st.dataframe(pd.DataFrame(documents), use_container_width=True, hide_index=True)
            if user["role"] == "admin":
                selected = st.selectbox(
                    "Dokumentprüfung",
                    documents,
                    format_func=lambda item: (
                        f"#{item['id']} · {item['filename']} · "
                        f"{STATUS_LABELS[item['approval_status']]}"
                    ),
                )
                status = st.selectbox(
                    "Neuer Dokumentstatus",
                    ["draft", "approved", "rejected"],
                    index=["draft", "approved", "rejected"].index(
                        selected["approval_status"]
                    ),
                    format_func=lambda value: STATUS_LABELS[value],
                )
                if st.button("Dokumentstatus speichern"):
                    service.review_document(selected["id"], status)
                    st.success("Dokumentstatus wurde aktualisiert.")
                    st.rerun()
        else:
            st.info("Keine sichtbaren Dokumente vorhanden.")

    elif page == "KI-Assistent":
        st.subheader("Quellengebundener Hybrid-Assistent")
        st.info(
            "Generative externe KI bleibt deaktiviert. Der lokale Provider erstellt "
            "einen prüfpflichtigen Antwortentwurf aus freigegebener Hybrid-Evidenz."
        )
        privacy = st.selectbox(
            "Datenschutzstufe der Anfrage",
            PRIVACY_LEVELS,
            index=PRIVACY_LEVELS.index(service.privacy_ceiling),
            format_func=lambda value: PRIVACY_LABELS[value],
        )
        question = st.text_area("Supportfrage", height=130)
        if st.button("Antwortentwurf erzeugen"):
            response = service.ask_assistant(
                question=question,
                privacy_level=privacy,
            )
            st.markdown("### Antwortentwurf")
            st.markdown(response.answer)
            st.caption(
                f"Lauf #{response.run_id} · Provider: {response.provider} · "
                f"Datenschutz: {PRIVACY_LABELS[response.privacy_level]}"
            )
            for item in response.evidence:
                with st.expander(f"{item.title} · Score {item.score}"):
                    st.write(item.content)
                    st.caption(f"Quelle: {item.source} · Typ: {item.source_type}")

        if user["role"] == "admin":
            runs = service.list_assistant_runs(limit=50)
            if runs:
                with st.expander("Letzte Assistenzläufe"):
                    st.dataframe(pd.DataFrame(runs), use_container_width=True, hide_index=True)

    elif page == "Audit":
        st.subheader("Audit-Protokoll")
        entries = service.list_audit_entries()
        if entries:
            st.dataframe(pd.DataFrame(entries), use_container_width=True, hide_index=True)
        else:
            st.info("Noch keine Audit-Einträge vorhanden.")

except AuthorizationError as exc:
    st.warning(str(exc))
except (ValueError, RuntimeError) as exc:
    st.error(str(exc))
