from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, Button, Frame, Label, StringVar, Tk
from tkinter.scrolledtext import ScrolledText


PROJECT_ROOT = Path(__file__).resolve().parent
PANEL_PS1 = PROJECT_ROOT / "panel.ps1"
LOGS_DIR = PROJECT_ROOT / "logs"
STDOUT_LOG = LOGS_DIR / "server.stdout.log"
STDERR_LOG = LOGS_DIR / "server.stderr.log"
PANEL_URL = "http://127.0.0.1:5000"


class PanelLauncher:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Canvas Panel Control")
        self.root.geometry("760x520")
        self.root.minsize(700, 460)
        self.status_var = StringVar(value="Verificando status...")
        self.output = None
        self._build_ui()
        self.refresh_status(log_output=False)
        self.root.after(5000, self.auto_refresh_status)

    def _build_ui(self) -> None:
        self.root.configure(bg="#0d131b")

        top = Frame(self.root, bg="#0d131b")
        top.pack(fill="x", padx=16, pady=(16, 10))

        Label(
            top,
            text="Canvas Panel Control",
            fg="#f3f7fb",
            bg="#0d131b",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        Label(
            top,
            textvariable=self.status_var,
            fg="#8ea3bd",
            bg="#0d131b",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 0))

        button_row = Frame(self.root, bg="#0d131b")
        button_row.pack(fill="x", padx=16, pady=(0, 10))

        for label, action in [
            ("Iniciar", "start"),
            ("Parar", "stop"),
            ("Reiniciar", "restart"),
            ("Status", "status"),
            ("Abrir painel", "open"),
        ]:
            Button(
                button_row,
                text=label,
                command=lambda current=action: self.run_action_async(current),
                padx=12,
                pady=6,
            ).pack(side=LEFT, padx=(0, 8))

        Button(
            button_row,
            text="Abrir log stdout",
            command=lambda: self.open_path(STDOUT_LOG),
            padx=12,
            pady=6,
        ).pack(side=RIGHT, padx=(8, 0))
        Button(
            button_row,
            text="Abrir log stderr",
            command=lambda: self.open_path(STDERR_LOG),
            padx=12,
            pady=6,
        ).pack(side=RIGHT, padx=(8, 0))

        body = Frame(self.root, bg="#0d131b")
        body.pack(fill=BOTH, expand=True, padx=16, pady=(0, 16))

        self.output = ScrolledText(
            body,
            wrap="word",
            bg="#111a24",
            fg="#dfeaf5",
            insertbackground="#dfeaf5",
            relief="flat",
            borderwidth=1,
            font=("Consolas", 10),
        )
        self.output.pack(fill=BOTH, expand=True)
        self.output.insert(END, "Mini controle carregado. Use os botoes acima para operar o painel.\n")
        self.output.configure(state="disabled")

    def append_output(self, text: str) -> None:
        if not self.output:
            return
        self.output.configure(state="normal")
        self.output.insert(END, f"{text.rstrip()}\n")
        self.output.see(END)
        self.output.configure(state="disabled")

    def run_action_async(self, action: str) -> None:
        thread = threading.Thread(target=self._run_action_worker, args=(action,), daemon=True)
        thread.start()

    def _run_action_worker(self, action: str) -> None:
        result = self.run_action(action)
        self.root.after(0, lambda: self.append_output(result))
        if action in {"start", "stop", "restart", "status"}:
            self.root.after(200, lambda: self.refresh_status(log_output=False))

    def run_action(self, action: str) -> str:
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PANEL_PS1),
            action,
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        except Exception as exc:  # noqa: BLE001
            return f"[{action}] erro ao executar: {exc}"

        output = (completed.stdout or "").strip()
        errors = (completed.stderr or "").strip()
        if errors:
            output = f"{output}\n{errors}".strip()
        prefix = f"[{action}] "
        return prefix + (output or "comando concluido sem saida")

    def refresh_status(self, *, log_output: bool = True) -> None:
        text = self.run_action("status")
        if log_output:
            self.append_output(text)
        normalized = text.lower()
        if "painel em execucao" in normalized:
            self.status_var.set(f"Rodando em {PANEL_URL}")
        elif "painel parado" in normalized:
            self.status_var.set("Painel parado")
        else:
            self.status_var.set("Status indisponivel")

    def auto_refresh_status(self) -> None:
        self.refresh_status(log_output=False)
        self.root.after(5000, self.auto_refresh_status)

    @staticmethod
    def open_path(path: Path) -> None:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        subprocess.Popen(["explorer", str(path)], shell=False)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    PanelLauncher().run()
