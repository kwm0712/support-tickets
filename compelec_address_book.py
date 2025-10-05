import os
import datetime
import tkinter as tk
from tkinter import ttk

try:
    import openai
except ImportError:  # openai is optional
    openai = None


class ChatBot:
    """Simple ChatBot wrapper using OpenAI if available."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        if openai and self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except Exception:
                self.client = None

    def ask(self, prompt: str) -> str:
        if self.client:
            try:
                completion = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                )
                return completion.choices[0].message.content.strip()
            except Exception as e:
                return f"Fehler bei der Anfrage: {e}"
        # Fallback response if no API key or client
        return (
            "Dies ist ein Platzhalter-ChatBot. "
            "Bitte setzen Sie einen OPENAI_API_KEY, um echte Antworten zu erhalten."
        )


class AddressBookApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Compelec Address Manager")
        self.geometry("1280x1024")

        # Use a custom style (simple example for "compelec" look)
        style = ttk.Style(self)
        style.configure("TFrame", background="#f0f4ff")
        style.configure("Status.TLabel", background="#001133", foreground="white")

        self.chat_bot = ChatBot()

        self.create_widgets()

    def create_widgets(self):
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Address frame
        addr_frame = ttk.Frame(self)
        addr_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        addr_frame.columnconfigure(0, weight=1)
        addr_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            addr_frame,
            columns=("Name", "Telefon", "E-Mail"),
            show="headings",
        )
        for col in ("Name", "Telefon", "E-Mail"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        self.tree.grid(row=0, column=0, sticky="nsew")

        entry_frame = ttk.Frame(addr_frame)
        entry_frame.grid(row=1, column=0, pady=5, sticky="ew")
        entry_frame.columnconfigure((0, 1, 2), weight=1)

        self.name_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.email_var = tk.StringVar()

        ttk.Entry(entry_frame, textvariable=self.name_var).grid(row=0, column=0, padx=5)
        ttk.Entry(entry_frame, textvariable=self.phone_var).grid(row=0, column=1, padx=5)
        ttk.Entry(entry_frame, textvariable=self.email_var).grid(row=0, column=2, padx=5)
        ttk.Button(entry_frame, text="Hinzufügen", command=self.add_contact).grid(
            row=0, column=3, padx=5
        )

        # Chat frame
        chat_frame = ttk.Frame(self)
        chat_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        self.chat_history = tk.Text(chat_frame, state="disabled", wrap="word")
        self.chat_history.grid(row=0, column=0, sticky="nsew")

        self.chat_entry = ttk.Entry(chat_frame)
        self.chat_entry.grid(row=1, column=0, sticky="ew", pady=5)
        self.chat_entry.bind("<Return>", self.send_message)

        # Status bar
        status = ttk.Frame(self)
        status.grid(row=1, column=0, columnspan=2, sticky="ew")
        status.columnconfigure(0, weight=1)
        status.columnconfigure(1, weight=1)

        self.left_status = ttk.Label(status, text="C. 2025 Compelec GmbH", style="Status.TLabel")
        self.left_status.grid(row=0, column=0, sticky="w", padx=5)
        self.right_status = ttk.Label(status, style="Status.TLabel")
        self.right_status.grid(row=0, column=1, sticky="e", padx=5)

        self.update_clock()

    def update_clock(self):
        now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        self.right_status.config(text=now)
        self.after(1000, self.update_clock)

    def add_contact(self):
        name = self.name_var.get().strip()
        phone = self.phone_var.get().strip()
        email = self.email_var.get().strip()
        if name:
            self.tree.insert("", "end", values=(name, phone, email))
            self.name_var.set("")
            self.phone_var.set("")
            self.email_var.set("")

    def send_message(self, event=None):
        user_msg = self.chat_entry.get().strip()
        if not user_msg:
            return
        self.chat_entry.delete(0, tk.END)
        self.append_chat("Ich", user_msg)
        answer = self.chat_bot.ask(user_msg)
        self.append_chat("Bot", answer)

    def append_chat(self, sender: str, text: str):
        self.chat_history.config(state="normal")
        self.chat_history.insert(tk.END, f"{sender}: {text}\n")
        self.chat_history.config(state="disabled")
        self.chat_history.see(tk.END)


if __name__ == "__main__":
    app = AddressBookApp()
    app.mainloop()
