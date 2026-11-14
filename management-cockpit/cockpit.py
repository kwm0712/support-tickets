import json
import os
from datetime import datetime, timezone

import requests
import streamlit as st

st.set_page_config(page_title="COMPELEC ONE – Management Cockpit", page_icon="🧭", layout="wide")

BLUE = "#1769AA"
DEFAULT_REPO = os.getenv("COMPELEC_GITHUB_REPO", "kwm0712/support-tickets")
API = "https://api.github.com"

st.markdown("""
<style>
.stApp { background: #f5f8fc; }
h1,h2,h3 { color: #164a78; }
div[data-testid="stMetric"] { background: white; padding: 14px; border: 1px solid #dce6f1; border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

st.title("COMPELEC ONE – Management Cockpit")
st.caption("V0.4 · Lokaler Betrieb · GitHub / CI / Release-Governance")
st.info("Die Anwendung läuft lokal. GitHub-Daten werden live gelesen; Freigabe-Checkboxen bleiben zunächst nur in dieser Sitzung. Es werden keine Daten in GitHub verändert.")

with st.sidebar:
    st.header("Verbindung")
    repo = st.text_input("GitHub-Repository", value=DEFAULT_REPO, help="Format: owner/repository")
    token = st.text_input("GitHub-Token (optional)", type="password", help="Nur für höhere API-Limits oder private Repositories. Wird nicht gespeichert.")
    st.caption("Für öffentliche Repositories ist normalerweise kein Token erforderlich.")
    refresh = st.button("Daten jetzt aktualisieren", use_container_width=True)
    st.divider()
    st.caption("COMPELEC-Blau · Deutsche Oberfläche")

if not repo or "/" not in repo:
    st.error("Bitte ein Repository im Format owner/name angeben.")
    st.stop()

def gh_get(path, token_value=""):
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token_value:
        headers["Authorization"] = f"Bearer {token_value}"
    response = requests.get(f"{API}{path}", headers=headers, timeout=20)
    if response.status_code == 404:
        return None, "Nicht gefunden oder keine Berechtigung (404)."
    if response.status_code == 403:
        return None, "GitHub-API-Limit erreicht oder Zugriff verweigert (403)."
    response.raise_for_status()
    return response.json(), None

@st.cache_data(ttl=60, show_spinner=False)
def load_data(repository, token_value, _refresh_key):
    encoded = repository.strip()
    result = {"repo": None, "pulls": [], "runs": [], "error": None}
    try:
        result["repo"], err = gh_get(f"/repos/{encoded}", token_value)
        if err:
            result["error"] = err
            return result
        result["pulls"], err = gh_get(f"/repos/{encoded}/pulls?state=open&per_page=30", token_value)
        if err:
            result["error"] = err
            return result
        result["runs"], err = gh_get(f"/repos/{encoded}/actions/runs?per_page=15", token_value)
        if err:
            result["error"] = err
            return result
        result["runs"] = result["runs"].get("workflow_runs", [])
    except requests.RequestException as exc:
        result["error"] = f"Verbindungsfehler: {exc}"
    return result

data = load_data(repo, token, datetime.now().timestamp() if refresh else 0)
if data["error"]:
    st.error(data["error"])
    st.stop()
if not data["repo"]:
    st.error("Repository konnte nicht geladen werden.")
    st.stop()

repo_info = data["repo"]
pulls = data["pulls"] or []
runs = data["runs"] or []
latest = runs[0] if runs else {}
failed = [r for r in runs if r.get("conclusion") == "failure"]
success = [r for r in runs if r.get("conclusion") == "success"]

st.caption(f"Repository: {repo_info['full_name']} · Standardbranch: {repo_info['default_branch']} · Sichtbarkeit: {repo_info['visibility']}")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Offene Pull Requests", len(pulls))
m2.metric("CI erfolgreich (letzte 15)", len(success))
m3.metric("CI fehlgeschlagen (letzte 15)", len(failed))
m4.metric("Letzter Workflow", latest.get("conclusion", "Noch kein Lauf").replace("_", " ").title())

tab1, tab2, tab3, tab4 = st.tabs(["Übersicht", "Pull Requests", "Release-Gates", "Bericht"])

with tab1:
    st.subheader("CI/CD – letzte Workflow-Läufe")
    if not runs:
        st.warning("Für dieses Repository wurden keine Workflow-Läufe gefunden.")
    for run in runs[:10]:
        conclusion = run.get("conclusion") or run.get("status") or "unbekannt"
        color = "🟢" if conclusion == "success" else ("🔴" if conclusion == "failure" else "🟡")
        with st.expander(f"{color} {run.get('name','Workflow')} · #{run.get('run_number','?')} · {conclusion} · {run.get('created_at','')[:10]}"):
            st.write(run.get("head_branch", ""), "·", run.get("head_sha", "")[:10])
            st.write(run.get("display_title") or run.get("head_commit", {}).get("message", ""))
            st.link_button("Workflow in GitHub öffnen", run.get("html_url", f"https://github.com/{repo}/actions"))
            try:
                jobs, err = gh_get(f"/repos/{repo}/actions/runs/{run['id']}/jobs?per_page=50", token)
                if err:
                    st.warning(err)
                else:
                    for job in jobs.get("jobs", []):
                        st.write(f"**{job['name']}** — {job.get('conclusion') or job.get('status')}")
                        for step in job.get("steps", []):
                            if step.get("conclusion") == "failure":
                                st.error(f"Fehlerhafter Schritt: {step['name']}")
            except requests.RequestException as exc:
                st.warning(f"Jobdetails nicht verfügbar: {exc}")
            try:
                artifacts, artifact_err = gh_get(f"/repos/{repo}/actions/runs/{run['id']}/artifacts", token)
                if artifact_err:
                    st.caption(f"Artefakte: {artifact_err}")
                else:
                    available = artifacts.get("artifacts", [])
                    if available:
                        st.write("**Build-Artefakte**")
                        for artifact in available:
                            st.write(f"- {artifact.get('name')} · {artifact.get('size_in_bytes', 0):,} Bytes · Ablauf: {artifact.get('expires_at', '')[:10]}")
                        st.caption("Zum Herunterladen den Workflow öffnen und den Bereich Artifacts verwenden.")
                    else:
                        st.caption("Keine Build-Artefakte für diesen Lauf veröffentlicht.")
            except requests.RequestException as exc:
                st.caption(f"Artefaktliste nicht verfügbar: {exc}")

    if failed:
        st.subheader("Fehlerdiagnose – Priorität")
        for run in failed[:5]:
            st.error(f"{run.get('name')} #{run.get('run_number')}: {run.get('display_title','Workflow fehlgeschlagen')}")
            st.write(f"Branch: {run.get('head_branch')} · Commit: {run.get('head_sha','')[:10]}")
            st.link_button("Fehlerdetails / Logs prüfen", run.get("html_url", f"https://github.com/{repo}/actions"))

with tab2:
    st.subheader("Offene Entwicklungszweige")
    if not pulls:
        st.success("Keine offenen Pull Requests.")
    for pr in pulls:
        state = "Draft" if pr.get("draft") else "Zur Prüfung"
        with st.expander(f"PR #{pr['number']} · {pr['title']} · {state}"):
            st.write(pr.get("body") or "Keine Beschreibung vorhanden.")
            st.write(f"Branch: {pr['head']['ref']} → {pr['base']['ref']}")
            st.link_button("Pull Request öffnen", pr["html_url"])

with tab3:
    st.subheader("Verbindliche Freigabekriterien")
    st.warning("Die Häkchen sind eine lokale Abnahme-Notiz. Sie werden nicht automatisch aus CI abgeleitet und stellen keine technische Bestätigung dar.")
    gates = [
        "Python- und Datenbanktests vollständig erfolgreich",
        "Windows-Build erfolgreich erstellt",
        "Installation und Deinstallation auf sauberem Windows geprüft",
        "OIDC / Entra-ID in Zielumgebung abgenommen",
        "Mandantentrennung und Rollenrechte geprüft",
        "Backup und Restore in Zielumgebung nachgewiesen",
        "Lizenzdatei signiert und validiert",
        "Datenschutz- und Sicherheitsfreigabe erteilt",
        "Geschäftsführungsfreigabe dokumentiert",
    ]
    approved = []
    for gate in gates:
        if st.checkbox(gate, key=f"gate_{gate}"):
            approved.append(gate)
    st.progress(len(approved) / len(gates))
    st.write(f"Lokale Checkliste: {len(approved)} von {len(gates)} Punkten markiert.")
    if len(approved) != len(gates):
        st.error("Release bleibt gesperrt: Nicht alle Abnahmepunkte sind markiert.")
    else:
        st.warning("Alle Punkte wurden lokal markiert. Eine tatsächliche Freigabe erfordert weiterhin dokumentierte Nachweise und autorisierte Entscheidung.")

with tab4:
    st.subheader("Managementbericht")
    report = {
        "erstellt_utc": datetime.now(timezone.utc).isoformat(),
        "repository": repo_info.get("full_name"),
        "default_branch": repo_info.get("default_branch"),
        "offene_pull_requests": [{"nummer": p["number"], "titel": p["title"], "draft": p["draft"], "url": p["html_url"]} for p in pulls],
        "workflow_laeufe": [{"name": r.get("name"), "run": r.get("run_number"), "status": r.get("status"), "ergebnis": r.get("conclusion"), "branch": r.get("head_branch"), "url": r.get("html_url")} for r in runs],
        "fehlgeschlagene_laeufe": len(failed),
        "erfolgreiche_laeufe": len(success),
        "hinweis": "Live-Metadaten aus GitHub. Keine lokale Checkliste als technische Freigabe interpretieren."
    }
    st.json(report)
    st.download_button("Bericht als JSON herunterladen", json.dumps(report, ensure_ascii=False, indent=2), file_name="COMPELEC_ONE_Managementbericht.json", mime="application/json")

st.divider()
st.caption("COMPELEC ONE · Management Cockpit V0.4 · Lokale Ausführung · Keine externen kostenpflichtigen Dienste eingebunden")
