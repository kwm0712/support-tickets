import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3, os
from pathlib import Path

APP="COMPELEC ONE Pfarrbüro-KI"; VERSION="1.3.0-demo"
DATA=Path(os.getenv("LOCALAPPDATA",str(Path.home())))/"COMPELEC ONE"/"Pfarrbuero-KI"
DATA.mkdir(parents=True,exist_ok=True); DB=DATA/"pfarrbuero_demo.db"

def db():
    c=sqlite3.connect(DB)
    c.execute("create table if not exists cases(id integer primary key, typ text, name text, status text)")
    if c.execute("select count(*) from cases").fetchone()[0]==0:
        c.executemany("insert into cases(typ,name,status) values(?,?,?)",[("Taufe","Familie Beispiel","Offen"),("Trauung","Demo-Vorgang","In Bearbeitung"),("Beerdigung","Mustermann","Freigabe")])
    c.commit(); return c

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title(f"{APP} – V{VERSION}"); self.geometry("1280x820"); self.minsize(1000,700)
        self.configure(bg="#f4f8fb"); self.conn=db(); self.style=ttk.Style(self); self.style.theme_use("clam")
        self.style.configure("Nav.TButton",font=("Segoe UI",11),padding=12,anchor="w")
        self.style.configure("Title.TLabel",font=("Segoe UI",22,"bold"),background="#f4f8fb",foreground="#005B96")
        self.style.configure("H.TLabel",font=("Segoe UI",14,"bold"),background="white",foreground="#17212b")
        self.make_ui(); self.show("Dashboard")
    def make_ui(self):
        top=tk.Frame(self,bg="white",height=64); top.pack(fill="x"); top.pack_propagate(False)
        tk.Label(top,text="COMPELEC ONE",font=("Segoe UI",18,"bold"),fg="#005B96",bg="white").pack(side="left",padx=24)
        tk.Label(top,text="Pfarrbüro-KI   ·   V1.3 Demo/Pilot",font=("Segoe UI",11),fg="#50616d",bg="white").pack(side="left")
        body=tk.Frame(self,bg="#f4f8fb"); body.pack(fill="both",expand=True)
        nav=tk.Frame(body,bg="#e5f4fc",width=230); nav.pack(side="left",fill="y"); nav.pack_propagate(False)
        self.content=tk.Frame(body,bg="#f4f8fb"); self.content.pack(side="left",fill="both",expand=True,padx=24,pady=20)
        for n in ["Dashboard","KI-Assistent","Vorgänge & Kasualien","Gottesdienste & Termine","Dokumente & Wissen","Kommunikation","Administration"]:
            ttk.Button(nav,text=n,style="Nav.TButton",command=lambda x=n:self.show(x)).pack(fill="x",padx=12,pady=4)
    def clear(self):
        for w in self.content.winfo_children(): w.destroy()
    def card(self,parent,title,text):
        f=tk.Frame(parent,bg="white",bd=1,relief="solid"); f.pack(side="left",fill="both",expand=True,padx=7,pady=7)
        ttk.Label(f,text=title,style="H.TLabel").pack(anchor="w",padx=18,pady=(16,6))
        tk.Label(f,text=text,font=("Segoe UI",12),fg="#50616d",bg="white",justify="left").pack(anchor="w",padx=18,pady=(0,18)); return f
    def show(self,name):
        self.clear(); ttk.Label(self.content,text=name,style="Title.TLabel").pack(anchor="w",pady=(0,12))
        if name=="Dashboard":
            r=tk.Frame(self.content,bg="#f4f8fb"); r.pack(fill="x")
            self.card(r,"Offene Vorgänge","3 Demo-Vorgänge"); self.card(r,"Gottesdienste","8 in den nächsten 7 Tagen"); self.card(r,"Dokumente","146 Demo-Einträge")
            self.card(self.content,"Heute im Pfarrbüro","09:00 Taufanfrage prüfen\n11:30 Gottesdienstordnung abstimmen\n14:00 Unterlagen vorbereiten")
        elif name=="Vorgänge & Kasualien":
            f=tk.Frame(self.content,bg="white"); f.pack(fill="both",expand=True)
            tree=ttk.Treeview(f,columns=("typ","name","status"),show="headings"); [tree.heading(c,text=t) for c,t in zip(("typ","name","status"),("Art","Vorgang","Status"))]
            for row in self.conn.execute("select typ,name,status from cases"): tree.insert("", "end", values=row)
            tree.pack(fill="both",expand=True,padx=16,pady=16)
            def add():
                self.conn.execute("insert into cases(typ,name,status) values('Taufe','Neuer Demo-Vorgang','Offen')"); self.conn.commit(); self.show(name)
            ttk.Button(f,text="+ Demo-Vorgang anlegen",command=add).pack(anchor="e",padx=16,pady=(0,16))
        elif name=="KI-Assistent":
            self.card(self.content,"Pfarrbüro-KI","Demo-Assistent: Antworten werden in dieser Fassung nicht an externe KI-Dienste gesendet.\nHuman-in-the-Loop · Quellenprüfung · Freigabe · Audit vorbereitet.")
            q=tk.Text(self.content,height=8,font=("Segoe UI",11)); q.pack(fill="x",pady=10)
            ttk.Button(self.content,text="Demo-Antwort vorbereiten",command=lambda:messagebox.showinfo("KI-Demo","Anfrage erkannt. Produktive RAG-/KI-Anbindung folgt nach Pilotfreigabe.")).pack(anchor="w")
        elif name=="Gottesdienste & Termine": self.card(self.content,"Wochenplanung","Sonntag 10:30 Eucharistiefeier\nDienstag 18:30 Abendmesse\nFreitag 17:00 Andacht")
        elif name=="Dokumente & Wissen": self.card(self.content,"Wissensbasis","Formulare 38   ·   Vorlagen 29   ·   Arbeitshilfen 44\nProduktive Dokumentenablage folgt im nächsten Release.")
        elif name=="Kommunikation": self.card(self.content,"Kommunikation","E-Mail · Pfarrbrief · Website · interne Nachricht\nEntwürfe mit Freigabeprozess vorbereitet.")
        else: self.card(self.content,"Administration","Mandant: Demo-Pfarrei\nBenutzer: 6 · Rollen: 4\nAI Control & Governance: Human-in-the-Loop, Least Privilege, Audit-Trail")
if __name__=="__main__": App().mainloop()
