import datetime as dt
import streamlit as st

st.set_page_config(page_title="COMPELEC ONE – Business AI", page_icon="🟦", layout="wide")

BLUE = "#123B70"
LIGHT = "#EAF3FC"

st.markdown(f"""
<style>
.stApp {{ background: #F7F9FC; }}
[data-testid="stSidebar"] {{ background: {BLUE}; }}
[data-testid="stSidebar"] * {{ color: white !important; }}
h1, h2, h3 {{ color: {BLUE}; }}
div.stButton > button {{ border-radius: 8px; border: 1px solid {BLUE}; }}
div.stButton > button[kind="primary"] {{ background: {BLUE}; color: white; }}
div[data-testid="stMetric"] {{ background: white; padding: 14px; border-radius: 10px; border: 1px solid #DCE5EF; }}
</style>
""", unsafe_allow_html=True)

if "tickets" not in st.session_state:
    st.session_state.tickets = [
        {"Nr.": "SUP-1001", "Kunde": "Muster GmbH", "Betreff": "PMS32 – Datenimport", "Priorität": "Hoch", "Status": "Offen", "Eingang": "14.11.2026"},
        {"Nr.": "SUP-1002", "Kunde": "Beispiel KG", "Betreff": "InGenius-Office – Benutzerfrage", "Priorität": "Normal", "Status": "In Bearbeitung", "Eingang": "14.11.2026"},
    ]
if "mails" not in st.session_state:
    st.session_state.mails = []

st.sidebar.markdown("## COMPELEC ONE")
st.sidebar.caption("BUSINESS AI · V1.0 PILOT")
page = st.sidebar.radio("Arbeitsbereich", [
    "Übersicht", "Support AI", "Sales AI", "Phone AI", "Mail AI", "Wissensbereich", "Einstellungen"
])
st.sidebar.divider()
st.sidebar.caption("Demonstrator – keine produktive Systemanbindung")

st.title("COMPELEC ONE – Business AI")
st.caption("Zentrale Arbeitsoberfläche für Support, Vertrieb und Kundenkommunikation")
st.info("V1.0 läuft im Demonstrationsmodus. Es werden keine externen KI-Dienste aufgerufen und keine E-Mails oder Telefonate tatsächlich versendet bzw. geführt.")

if page == "Übersicht":
    st.subheader("Unternehmens-Cockpit")
    a,b,c,d = st.columns(4)
    a.metric("Supportvorgänge", len(st.session_state.tickets))
    b.metric("Offen", sum(t["Status"] == "Offen" for t in st.session_state.tickets))
    c.metric("E-Mail-Entwürfe", len(st.session_state.mails))
    d.metric("Telefonie", "Nicht verbunden")
    st.subheader("Arbeitsbereiche")
    cols = st.columns(3)
    for col, title, desc in zip(cols, ["Support AI", "Sales AI", "Phone & Mail AI"],
                                ["Anfragen erfassen und Lösungswege vorbereiten", "Kundenansprache und Angebotsvorbereitung", "Telefonnotizen und E-Mail-Entwürfe zentral verwalten"]):
        with col:
            st.markdown(f"**{title}**")
            st.write(desc)
    st.subheader("Aktuelle Supportvorgänge")
    st.dataframe(st.session_state.tickets, use_container_width=True, hide_index=True)

elif page == "Support AI":
    st.subheader("Support AI")
    st.write("Supportanfragen strukturiert erfassen und eine nachvollziehbare Erstbewertung vorbereiten.")
    with st.form("ticket_form", clear_on_submit=True):
        customer = st.text_input("Kunde / Organisation")
        subject = st.text_input("Betreff / betroffenes System")
        description = st.text_area("Fehlerbeschreibung und bisherige Prüfschritte")
        priority = st.selectbox("Priorität", ["Normal", "Hoch", "Kritisch"])
        submitted = st.form_submit_button("Supportvorgang anlegen", type="primary")
    if submitted:
        if not customer.strip() or not subject.strip() or not description.strip():
            st.error("Bitte Kunde, Betreff und Fehlerbeschreibung ausfüllen.")
        else:
            number = 1001 + len(st.session_state.tickets)
            st.session_state.tickets.append({"Nr.": f"SUP-{number}", "Kunde": customer, "Betreff": subject,
                "Priorität": priority, "Status": "Offen", "Eingang": dt.date.today().strftime("%d.%m.%Y")})
            st.success("Vorgang wurde lokal in dieser Sitzung angelegt.")
            st.session_state.last_support = (customer, subject, description, priority)
    if "last_support" in st.session_state:
        customer, subject, description, priority = st.session_state.last_support
        st.markdown("#### Strukturierte Erstbewertung (Regel-Demonstrator)")
        st.write(f"**Kunde:** {customer}  ·  **Thema:** {subject}  ·  **Priorität:** {priority}")
        st.write("**Nächste Prüfschritte:**")
        st.markdown("- Reproduzierbarkeit und Zeitpunkt des Fehlers dokumentieren.\n- Betroffene Programmversion und Systemumgebung feststellen.\n- Fehlermeldung bzw. Protokollauszug sichern.\n- Letzte Änderungen und Schnittstellenstatus prüfen.\n- Ergebnis dokumentieren und bei Bedarf an den zuständigen Mitarbeiter eskalieren.")
        st.caption("Diese Checkliste ist eine allgemeine Vorlage, keine KI-Diagnose und keine Aussage über die tatsächliche Fehlerursache.")
    st.subheader("Vorgangsliste")
    st.dataframe(st.session_state.tickets, use_container_width=True, hide_index=True)

elif page == "Sales AI":
    st.subheader("Sales AI")
    st.write("Vertriebsansprache und Gesprächsvorbereitung als Entwurf erstellen.")
    with st.form("sales_form"):
        prospect = st.text_input("Interessent / Unternehmen")
        product = st.selectbox("Lösungsbereich", ["PMS32", "InGenius-Office", "Professional ERP", "EPLAN / PMS-Data", "COMPELEC ONE"])
        need = st.text_area("Bekannter Bedarf / Gesprächsanlass")
        make = st.form_submit_button("Gesprächsvorbereitung erstellen", type="primary")
    if make:
        if not prospect.strip() or not need.strip():
            st.warning("Bitte Interessent und Bedarf angeben.")
        else:
            st.markdown("#### Gesprächsleitfaden – Entwurf")
            st.write(f"**Interessent:** {prospect}  ·  **Lösungsbereich:** {product}")
            st.markdown(f"**Ausgangslage**\n\n{need}")
            st.markdown("**Gesprächsstruktur**\n1. Ausgangssituation und Ziele des Interessenten klären.\n2. Heutige Abläufe, Medienbrüche und Engpässe aufnehmen.\n3. Passende COMPELEC-Lösung und Integrationsbedarf abgleichen.\n4. Nutzen, Aufwand, Risiken und nächste Schritte gemeinsam festhalten.")
            st.warning("Keine Preis-, Leistungs- oder Lieferzusage ohne Prüfung durch den Vertrieb.")

elif page == "Phone AI":
    st.subheader("Phone AI")
    st.write("Telefonassistent – V1.0 Gesprächsprotokoll und Rückrufmanagement.")
    st.warning("STARFACE ist noch nicht angebunden. Diese Oberfläche nimmt keine Anrufe entgegen und startet keine ausgehenden Anrufe.")
    with st.form("call_form", clear_on_submit=True):
        caller = st.text_input("Anrufer / Unternehmen")
        phone = st.text_input("Rückrufnummer")
        reason = st.text_area("Anliegen / Gesprächsnotiz")
        callback = st.checkbox("Rückruf erforderlich")
        owner = st.text_input("Zuständiger Mitarbeiter")
        saved = st.form_submit_button("Gesprächsnotiz speichern", type="primary")
    if saved:
        if not caller.strip() or not reason.strip():
            st.error("Anrufer und Gesprächsnotiz sind erforderlich.")
        else:
            st.session_state.setdefault("calls", []).append({"Zeit": dt.datetime.now().strftime("%d.%m.%Y %H:%M"), "Anrufer": caller, "Telefon": phone, "Anliegen": reason, "Rückruf": "Ja" if callback else "Nein", "Zuständig": owner})
            st.success("Gesprächsnotiz in dieser Sitzung gespeichert.")
    if st.session_state.get("calls"):
        st.dataframe(st.session_state.calls, use_container_width=True, hide_index=True)

elif page == "Mail AI":
    st.subheader("Mail AI")
    st.write("E-Mail-Arbeitsplatz – V1.0 Entwurfserstellung.")
    st.warning("Es ist noch kein Postfach verbunden. Es werden keine E-Mails empfangen oder versendet.")
    with st.form("mail_form"):
        recipient = st.text_input("Empfänger")
        subject = st.text_input("Betreff")
        context = st.text_area("Stichpunkte / Anliegen")
        tone = st.selectbox("Tonalität", ["Sachlich und professionell", "Freundlich und serviceorientiert", "Verbindlich und vertrieblich"])
        draft = st.form_submit_button("E-Mail-Entwurf erstellen", type="primary")
    if draft:
        if not recipient.strip() or not subject.strip() or not context.strip():
            st.error("Bitte Empfänger, Betreff und Inhalt angeben.")
        else:
            body = f"Guten Tag,\n\n{context}\n\n{ 'Vielen Dank für Ihre Nachricht. Bei Rückfragen stehen wir Ihnen gerne zur Verfügung.' if 'serviceorientiert' in tone else 'Für die weitere Abstimmung stehe ich gerne zur Verfügung.'}\n\nMit freundlichen Grüßen\nCOMPELEC"
            item = {"Empfänger": recipient, "Betreff": subject, "Entwurf": body}
            st.session_state.mails.append(item)
            st.success("Entwurf erstellt – bitte vor Verwendung fachlich prüfen.")
    for i, mail in enumerate(reversed(st.session_state.mails)):
        with st.expander(f"{mail['Betreff']} – {mail['Empfänger']}"):
            st.text_area("Entwurf", mail["Entwurf"], key=f"mail_{i}", height=180)

elif page == "Wissensbereich":
    st.subheader("Wissensbereich")
    st.write("Vorbereitung der COMPELEC-Wissensbasis für Handbücher, FAQs, technische Dokumentation und freigegebene Lösungen.")
    st.info("RAG, Dokumentenimport, Quellenzitate und PostgreSQL/pgvector sind für den nächsten technischen Ausbauschritt vorgesehen.")
    files = st.file_uploader("Dokumente für einen späteren Wissensimport auswählen", accept_multiple_files=True, type=["pdf","txt","md","docx"])
    if files:
        st.write("Ausgewählte Dateien (noch nicht importiert):")
        for f in files:
            st.write(f"- {f.name} ({f.size:,} Bytes)")

else:
    st.subheader("Einstellungen und Integrationsstatus")
    st.markdown("| Integration | V1.0-Status |")
    st.markdown("|---|---|\n| STARFACE Telefonie | Vorbereitet, nicht verbunden |\n| IMAP / SMTP / Microsoft 365 | Vorbereitet, nicht verbunden |\n| PMS32 / InGenius-Office | Schnittstellenplanung erforderlich |\n| PostgreSQL / pgvector | Noch nicht eingerichtet |\n| Externe KI-Modelle | Nicht aktiviert |")
    st.caption("Vor einer Produktivsetzung sind Authentifizierung, Rollen/Rechte, persistente Datenhaltung, Protokollierung, Datenschutz und Tests umzusetzen.")
    st.subheader("Datenschutz-Hinweis")
    st.write("Keine echten Kunden-, Personal-, Zugangsdaten oder vertraulichen Vorgänge in diesem Demonstrator verwenden. Sitzungsdaten sind nicht als dauerhafte, gesicherte Speicherung ausgelegt.")
