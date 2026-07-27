"""Windows desktop interface for OBD-Insight."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from analysis import analyze_scan_text
from history import save_scan_to_history
from main import format_vehicle


class ObdInsightApp:
    """Paste or open FORScan log text and display its first-pass analysis."""

    def __init__(self, root):
        self.root = root
        self.root.title("OBD-Insight")
        self.root.geometry("1050x760")
        self.root.minsize(800, 600)

        self.vehicle_var = tk.StringVar(value="Vehicle: Not analyzed")
        self.summary_var = tk.StringVar(value="Paste or open a FORScan Log to begin.")
        self.status_var = tk.StringVar(value="Ready")

        self._build_layout()

    def _build_layout(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)
        self.root.rowconfigure(4, weight=1)

        header = ttk.Frame(self.root, padding=(16, 14, 16, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="OBD-Insight",
            font=("Segoe UI", 20, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Copy the FORScan Log tab, paste it here, and analyze the scan.",
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        actions = ttk.Frame(self.root, padding=(16, 4, 16, 8))
        actions.grid(row=1, column=0, sticky="ew")
        ttk.Button(
            actions,
            text="Paste from Clipboard",
            command=self.paste_from_clipboard,
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Open Log File",
            command=self.open_log_file,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Clear", command=self.clear_all).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(
            actions,
            text="Analyze Scan",
            command=self.analyze_scan,
        ).pack(side="right")

        input_frame = ttk.LabelFrame(
            self.root,
            text="FORScan Log Text",
            padding=8,
        )
        input_frame.grid(row=2, column=0, sticky="nsew", padx=16)
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=1)

        self.scan_text = ScrolledText(
            input_frame,
            wrap="word",
            font=("Consolas", 9),
            undo=True,
        )
        self.scan_text.grid(row=0, column=0, sticky="nsew")

        summary = ttk.Frame(self.root, padding=(16, 10, 16, 6))
        summary.grid(row=3, column=0, sticky="ew")
        summary.columnconfigure(0, weight=1)
        ttk.Label(
            summary,
            textvariable=self.vehicle_var,
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(summary, textvariable=self.summary_var).grid(
            row=1, column=0, sticky="w", pady=(3, 0)
        )

        results_frame = ttk.LabelFrame(self.root, text="Results", padding=8)
        results_frame.grid(row=4, column=0, sticky="nsew", padx=16)
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        columns = ("severity", "module", "module_name", "code")
        self.results = ttk.Treeview(
            results_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.results.heading("severity", text="Severity")
        self.results.heading("module", text="Module")
        self.results.heading("module_name", text="Module Name")
        self.results.heading("code", text="DTC Code")
        self.results.column("severity", width=110, minwidth=90, stretch=False)
        self.results.column("module", width=100, minwidth=80, stretch=False)
        self.results.column("module_name", width=460, minwidth=220)
        self.results.column("code", width=140, minwidth=120, stretch=False)
        self.results.tag_configure("Critical", foreground="#b00020")
        self.results.tag_configure("Warning", foreground="#9a5b00")
        self.results.tag_configure("Informational", foreground="#4b5563")
        self.results.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            results_frame,
            orient="vertical",
            command=self.results.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.results.configure(yscrollcommand=scrollbar.set)

        ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief="sunken",
            anchor="w",
            padding=(8, 4),
        ).grid(row=5, column=0, sticky="ew", pady=(10, 0))

    def paste_from_clipboard(self):
        try:
            clipboard_text = self.root.clipboard_get()
        except tk.TclError:
            messagebox.showwarning(
                "Nothing to paste",
                "The clipboard does not contain text. Copy the FORScan Log tab first.",
            )
            return

        if not clipboard_text.strip():
            messagebox.showwarning(
                "Nothing to paste",
                "The clipboard text is empty. Copy the FORScan Log tab first.",
            )
            return

        self._set_scan_text(clipboard_text)
        self.status_var.set("FORScan text pasted. Click Analyze Scan.")

    def open_log_file(self):
        selected_path = filedialog.askopenfilename(
            title="Open FORScan Log",
            filetypes=(
                ("Text files", "*.txt"),
                ("Log files", "*.log"),
                ("All files", "*.*"),
            ),
        )
        if not selected_path:
            return

        try:
            scan_text = read_log_file(selected_path)
        except (OSError, UnicodeError) as error:
            messagebox.showerror(
                "Unable to open log",
                f"OBD-Insight could not read this file.\n\n{error}",
            )
            return

        self._set_scan_text(scan_text)
        self.status_var.set(f"Opened {Path(selected_path).name}. Click Analyze Scan.")

    def analyze_scan(self):
        scan_text = self.scan_text.get("1.0", "end-1c")
        if not scan_text.strip():
            messagebox.showwarning(
                "No scan text",
                "Paste FORScan Log text or open a log file before analyzing.",
            )
            return

        analysis = analyze_scan_text(scan_text)
        if not any((analysis["vehicle"], analysis["modules"], analysis["dtcs"])):
            self._clear_results()
            self.vehicle_var.set("Vehicle: Not found")
            self.summary_var.set("No recognizable FORScan scan data was found.")
            self.status_var.set("Analysis stopped: unrecognized scan text.")
            messagebox.showwarning(
                "FORScan data not found",
                "The text did not contain a Vehicle, Found module, or DTCs in line.",
            )
            return

        self._show_analysis(analysis)
        self._save_history(scan_text)

    def clear_all(self):
        self.scan_text.delete("1.0", "end")
        self._clear_results()
        self.vehicle_var.set("Vehicle: Not analyzed")
        self.summary_var.set("Paste or open a FORScan Log to begin.")
        self.status_var.set("Ready")

    def _set_scan_text(self, scan_text):
        self.scan_text.delete("1.0", "end")
        self.scan_text.insert("1.0", scan_text)

    def _show_analysis(self, analysis):
        self._clear_results()

        vehicle = format_vehicle(analysis["vehicle"])
        vin = analysis["vehicle"].get("vin")
        vehicle_text = f"Vehicle: {vehicle}"
        if vin:
            vehicle_text += f"  |  VIN: {vin}"
        self.vehicle_var.set(vehicle_text)

        counts = analysis["counts"]
        self.summary_var.set(
            f"{len(analysis['modules'])} modules  |  "
            f"{len(analysis['results'])} DTCs  |  "
            f"{counts['Critical']} Critical  |  "
            f"{counts['Warning']} Warning  |  "
            f"{counts['Informational']} Informational"
        )

        for result in analysis["results"]:
            severity = result["severity"]
            self.results.insert(
                "",
                "end",
                values=(
                    severity,
                    result["module"],
                    result.get("module_name") or "Unknown module",
                    result["code"],
                ),
                tags=(severity,),
            )

        if analysis["results"]:
            self.status_var.set("Scan analyzed successfully.")
        else:
            self.status_var.set("Scan analyzed successfully. No DTCs were found.")

    def _clear_results(self):
        for item in self.results.get_children():
            self.results.delete(item)

    def _save_history(self, scan_text):
        try:
            save_result = save_scan_to_history(scan_text)
        except (OSError, ValueError) as error:
            self.status_var.set("Scan analyzed, but history could not be saved.")
            messagebox.showwarning(
                "History not saved",
                f"The scan results are available, but the history file could not be saved.\n\n{error}",
            )
            return

        if save_result.created:
            self.status_var.set(
                f"Scan analyzed and saved to {save_result.vehicle_folder.name}."
            )
        else:
            self.status_var.set("Scan analyzed. This scan is already in history.")


def read_log_file(path):
    """Read common FORScan text encodings without requiring user conversion."""
    raw_data = Path(path).read_bytes()
    if raw_data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw_data.decode("utf-16")

    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw_data.decode(encoding)
        except UnicodeError:
            continue
    raise UnicodeError("Unsupported text encoding")


def main():
    root = tk.Tk()
    ObdInsightApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
