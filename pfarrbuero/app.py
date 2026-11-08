import os
import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from api_client import ApiCaseStore
from oidc_auth import OidcAuthClient

APP = "COMPELEC ONE Pfarrbüro-KI"
VERSION = "2.0.2-dev"
DATA = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "COMPELEC ONE" / "Pfarrbuero-KI"
DATA.mkdir(parents=True, exist_ok=True)
DB = DATA / "pfarrbuero_demo.db"


def demo_db():
    """Explicitly local demo storage. Never used as a silent PostgreSQL fallback."""
    conn = sqlite3.connect(DB)
    conn.execute(
        "create table if not exists cases(id integer primary key, typ text, name text, status text)"
    )
    if conn.execute("select count(*) from cases").fetchone()[0] == 0:
        conn.executemany(
            "insert into cases(typ,name,status) values(?,?,?)",
            [
                ("Taufe", "Familie Beispiel", "Offen"),
                ("Trauung", "Demo-Vorgang", "In Bearbeitung"),
                ("Beerdigung", "Mustermann", "Freigabe"),
            ],
        )
    conn.commit()
    return conn


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP} – V{VERSION}")
        self.geometry("1280x820")
        self.minsize(1000, 700)
        self.configure(bg="#f4f8fb")

        self.api_store = None
        self.auth_client = None
        self.backend_error = None
        self.conn = None
        self.api_url = os.getenv("PFARRBUERO_API_URL", "").rstrip("/")
        if self.api_url:
            try:
                self.auth_client = OidcAuthClient()
                try:
                    token = self.auth_client.access_token()
                    self.api_store = ApiCaseStore(self.api_url, self.auth_client.access_token)
                    self.api_store.health_check()
                    self.backend_label = "SECURE API · ANGEMELDET"
                except RuntimeError as auth_error:
                    self.backend_error = str(auth_error)
                    self.backend_label = "ANMELDUNG ERFORDERLICH"
            except Exception as exc:
                self.backend_error = str(exc)
                self.backend_label = "OIDC-KONFIGURATION FEHLT"
        elif os.getenv("PFARRBUERO_DATABASE_URL"):
            self.backend_error = "Direkter PostgreSQL-Zugriff aus der Desktop-Anwendung ist deaktiviert. Bitte PFARRBUERO_API_URL und OIDC-Clientkonfiguration einrichten."
            self.backend_label = "API-KONFIGURATION FEHLT"
        else:
            self.conn = demo_db()
            self.backend_label = "DEMO-DATEN · SQLite"

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("Nav.TButton", font=("Segoe UI", 11), padding=12, anchor="w")
        self.style.configure(
            "Title.TLabel", font=("Segoe UI", 22, "bold"),
            background="#f4f8fb", foreground="#005B96"
        )
        self.style.configure(
            "H.TLabel", font=("Segoe UI", 14, "bold"),
            background="white", foreground="#17212b"
        )
        self.make_ui()
        self.show("Dashboard")

    def make_ui(self):
        top = tk.Frame(self, bg="white", height=64)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(
            top, text="COMPELEC ONE", font=("Segoe UI", 18, "bold"),
            fg="#005B96", bg="white"
        ).pack(side="left", padx=24)
        tk.Label(
            top, text="Pfarrbüro-KI   ·   V2.0.2 Entwicklungsstand",
            font=("Segoe UI", 11), fg="#50616d", bg="white"
        ).pack(side="left")
        if self.api_url:
            ttk.Button(top, text="Anmelden", command=self.login).pack(side="right", padx=(4, 12))
            if self.auth_client:
                ttk.Button(top, text="Abmelden", command=self.logout).pack(side="right", padx=4)
        tk.Label(
            top, text=self.backend_label, font=("Segoe UI", 9, "bold"),
            fg="#005B96" if self.api_store else "#8a5a00", bg="white"
        ).pack(side="right", padx=12)

        body = tk.Frame(self, bg="#f4f8fb")
        body.pack(fill="both", expand=True)
        nav = tk.Frame(body, bg="#e5f4fc", width=230)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)
        self.content = tk.Frame(body, bg="#f4f8fb")
        self.content.pack(side="left", fill="both", expand=True, padx=24, pady=20)

        modules = [
            "Dashboard", "KI-Assistent", "Vorgänge & Kasualien",
            "Gottesdienste & Termine", "Dokumente & Wissen",
            "Kommunikation", "Administration"
        ]
        for name in modules:
            ttk.Button(
                nav, text=name, style="Nav.TButton",
                command=lambda selected=name: self.show(selected)
            ).pack(fill="x", padx=12, pady=4)

    def login(self):
        if not self.auth_client:
            messagebox.showerror("OIDC nicht konfiguriert", self.backend_error or "OIDC-Konfiguration fehlt.")
            return
        try:
            token = self.auth_client.login()
            self.api_store = ApiCaseStore(self.api_url, token)
            self.api_store.health_check()
            self.backend_error = None
            self.backend_label = "SECURE API · ANGEMELDET"
            self.show("Dashboard")
        except Exception as exc:
            self.api_store = None
            self.backend_error = str(exc)
            self.backend_label = "ANMELDUNG FEHLGESCHLAGEN"
            messagebox.showerror("Anmeldung fehlgeschlagen", str(exc))
            self.show("Dashboard")

    def logout(self):
        if self.auth_client:
            self.auth_client.clear()
        self.api_store = None
        self.backend_error = "Bitte über die Schaltfläche Anmelden erneut anmelden."
        self.backend_label = "ABGEMELDET"
        self.show("Dashboard")

    def clear(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def card(self, parent, title, text):
        frame = tk.Frame(parent, bg="white", bd=1, relief="solid")
        frame.pack(side="left", fill="both", expand=True, padx=7, pady=7)
        ttk.Label(frame, text=title, style="H.TLabel").pack(
            anchor="w", padx=18, pady=(16, 6)
        )
        tk.Label(
            frame, text=text, font=("Segoe UI", 12),
            fg="#50616d", bg="white", justify="left", wraplength=280
        ).pack(anchor="w", padx=18, pady=(0, 18))
        return frame

    def case_rows(self):
        if self.api_store:
            return self.api_store.list_cases()
        if self.conn:
            return self.conn.execute(
                "select typ,name,status from cases order by id desc"
            ).fetchall()
        return []

    def add_case(self):
        case_type = simpledialog.askstring("Neuer Vorgang", "Vorgangsart:", parent=self)
        if not case_type:
            return
        subject = simpledialog.askstring("Neuer Vorgang", "Betreff / Kurzbeschreibung:", parent=self)
        if not subject:
            return
        try:
            if self.api_store:
                self.api_store.create_case(case_type, subject)
            elif self.conn:
                self.conn.execute(
                    "insert into cases(typ,name,status) values(?,?,?)",
                    (case_type.strip(), subject.strip(), "Offen")
                )
                self.conn.commit()
            else:
                raise RuntimeError(self.backend_error or "Kein Datenbank-Backend verfügbar.")
            self.show("Vorgänge & Kasualien")
        except Exception as exc:
            messagebox.showerror("Vorgang konnte nicht gespeichert werden", str(exc))

    def show(self, name):
        self.clear()
        ttk.Label(self.content, text=name, style="Title.TLabel").pack(
            anchor="w", pady=(0, 12)
        )

        if self.backend_error:
            tk.Label(
                self.content,
                text="PostgreSQL wurde ausdrücklich konfiguriert, ist aber nicht verfügbar.\n"
                     "Aus Sicherheitsgründen wird nicht auf Demo-Daten zurückgeschaltet.\n\n"
                     + self.backend_error,
                font=("Segoe UI", 11), fg="#9b1c1c", bg="#f4f8fb",
                justify="left", wraplength=850
            ).pack(anchor="w", pady=16)
            return

        if name == "Dashboard":
            rows = self.case_rows()
            open_count = sum(1 for row in rows if str(row[2]).lower() in ("offen", "open"))
            row = tk.Frame(self.content, bg="#f4f8fb")
            row.pack(fill="x")
            self.card(row, "Vorgänge", f"{len(rows)} Vorgänge im ausgewählten Datenbestand")
            self.card(row, "Offene Vorgänge", str(open_count))
            self.card(
                row, "Datenbank",
                "Zentraler API-Zugriff mit OIDC-Token" if self.api_store
                else "Lokaler Demo-Modus – keine produktiven Daten"
            )
            self.card(
                self.content, "Nächste Ausbaustufen",
                "Gottesdienstplanung · Veranstaltungen · Dokumentenablage\n"
                "Sakramentenverwaltung · Ehrenamt · Seelsorge"
            )

        elif name == "Vorgänge & Kasualien":
            frame = tk.Frame(self.content, bg="white")
            frame.pack(fill="both", expand=True)
            tree = ttk.Treeview(
                frame, columns=("typ", "subject", "status"),
                show="headings", height=18
            )
            for column, title, width in (
                ("typ", "Vorgangsart", 180),
                ("subject", "Betreff / Vorgang", 520),
                ("status", "Status", 180),
            ):
                tree.heading(column, text=title)
                tree.column(column, width=width, anchor="w")
            for item in self.case_rows():
                tree.insert("", "end", values=item)
            tree.pack(fill="both", expand=True, padx=16, pady=16)
            ttk.Button(
                frame, text="+ Vorgang anlegen", command=self.add_case
            ).pack(anchor="e", padx=16, pady=(0, 16))

        elif name == "KI-Assistent":
            self.card(
                self.content, "Pfarrbüro-KI",
                "Derzeit noch kein produktiver KI-Aufruf. Geplant sind Quellenbindung, "
                "RAG-Wissensbasis, Freigabeschritte und Audit-Protokoll."
            )
            q = tk.Text(self.content, height=8, font=("Segoe UI", 11))
            q.pack(fill="x", pady=10)
            ttk.Button(
                self.content, text="Anfrage vorbereiten",
                command=lambda: messagebox.showinfo(
                    "KI-Assistent",
                    "Die produktive KI-/RAG-Anbindung wird in einem späteren, separat geprüften Schritt integriert."
                )
            ).pack(anchor="w")

        elif name == "Gottesdienste & Termine":
            self.card(
                self.content, "Gottesdienstplanung",
                "Nächster Umsetzungsschritt: Kalenderdatenmodell, Ressourcen, "
                "Zelebranten und Konfliktprüfung."
            )
        elif name == "Dokumente & Wissen":
            self.card(
                self.content, "Dokumente & Wissensbasis",
                "Geplant: kontrollierter Dateispeicher, Dokumentversionen, "
                "SHA-256-Prüfung und Freigabeworkflow."
            )
        elif name == "Kommunikation":
            self.card(
                self.content, "Kommunikation",
                "Geplant: Korrespondenzentwürfe, E-Mail-Adapter und menschliche Freigabe."
            )
        else:
            self.card(
                self.content, "Administration",
                "V2.0-Kern: Mandanten, Organisationseinheiten, Benutzer, Rollen, "
                "Berechtigungen und Audit. Die produktive Anmeldung und "
                "Berechtigungsverwaltung folgen als eigener Umsetzungsschritt."
            )


if __name__ == "__main__":
    App().mainloop()
