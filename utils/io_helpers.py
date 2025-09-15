import csv, os
from threading import Lock
from datetime import datetime
from pathlib import Path

_lock = Lock()
RESULTS = Path("output/resultados.csv")
RESULTS.parent.mkdir(parents=True, exist_ok=True)

def read_jobs(path: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(";")]
            if len(parts) >= 2:
                items.append((parts[0], parts[1]))
    return items

def init_results():
    os.makedirs("output", exist_ok=True)
    if not os.path.exists("output/resultados.csv"):
        with open("output/resultados.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["quando", "url", "nome", "status", "mensagem"])

def append_result(url: str, nome: str, status: str, msg: str) -> None:
    write_header = not RESULTS.exists()
    with RESULTS.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        if write_header:
            w.writerow(["data_hora", "url", "nome", "status", "msg"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), url, nome, status, msg])