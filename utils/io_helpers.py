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

def append_result(url: str, nome: str, status: str, msg: str, idx: int | None = None) -> None:
    write_header = not RESULTS.exists()
    with RESULTS.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        if write_header:
            w.writerow(["data_hora", "url", "nome", "status", "msg"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), url, nome, status, msg])

    # --- apenas console (não afeta app.log) ---
    if idx is None or idx == 0:
        idx_txt = "?"
    else:
        idx_txt = str(idx)

    ok = (status or "").strip().upper() in {"OK", "SUCESSO", "REMOVIDO", "SUCESSO_FORM", "SUCESSO_REMOCAO"}
    if ok:
        print(f"Removido com sucesso link {idx_txt} {url}", flush=True)
    else:
        print(f"Falha na remoção link {idx_txt} {url} ({status})", flush=True)

def get_failed_results(output_file="output/resultados.txt"):
    """Retorna lista de (url, nome) que falharam (exclui SUCESSO e ERRO_VALIDACAO)."""
    erros = []
    with open(output_file, "r", encoding="utf-8") as f:
        for line in f:
            partes = line.strip().split(";")
            if len(partes) < 4:
                continue
            url, nome, status, msg = partes[:4]
            if status not in ("SUCESSO", "ERRO_VALIDACAO"):
                erros.append((url, nome))
    return erros