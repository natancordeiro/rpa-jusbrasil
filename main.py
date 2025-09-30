from queue import Queue
from utils.logger import logger
from utils.config import load_config
from utils.io_helpers import read_jobs, init_results
from automation.worker import Worker


def main():
    cfg = load_config("config.yaml")
    jobs = read_jobs(cfg["arquivo_input"])
    if not jobs:
        logger.error("Nenhum item em dados.txt (formato: 'URL ; NOME').")
        return

    init_results()
    print("Iniciando processamento...")

    q = Queue()
    for idx, job in enumerate(jobs, start=1):
        url, nome = job
        q.put((idx, url, nome))

    n_threads = max(1, int(cfg.get("threads", 2)))
    workers = [Worker(i + 1, q, cfg, name=f"T{i+1}") for i in range(n_threads)]
    logger.info(f"Iniciando {n_threads} navegadores. Total de itens: {len(jobs)}")
    for w in workers:
        w.start()

    q.join()
    for w in workers:
        w.stop()
    for w in workers:
        w.join(timeout=2.0)

    logger.info("Processamento concluído. Veja output/resultados.csv")
    print("Processamento concluído. Veja output/resultados.csv")

if __name__ == "__main__":
    main()
