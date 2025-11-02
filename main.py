from queue import Queue
import atexit
import signal, sys

from utils.logger import logger
from utils.config import load_config
from utils.io_helpers import read_jobs, init_results, get_failed_results, append_result
from automation.worker import Worker
from automation.jusbrasil import JusbrasilClient
from automation.login import try_login
from automation.browser import BrowserFactory

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

    # --- ADIÇÃO: handlers para tentar logout em saídas abruptas (Ctrl+C, kill) ---
    def _graceful_exit(signum=None, frame=None):
        try:
            for w in workers:
                try:
                    # Se você implementou Worker.logout(), ele aciona o client.logout()
                    if hasattr(w, "logout"):
                        w.logout()
                except Exception:
                    pass
                try:
                    w.stop()   # seu stop já pode chamar logout também; manter por segurança
                except Exception:
                    pass
            for w in workers:
                try:
                    w.join(timeout=2.0)
                except Exception:
                    pass
        finally:
            # não imprime stack trace extra em Ctrl+C
            if signum in (signal.SIGINT, signal.SIGTERM):
                sys.exit(1)

    # registra handlers e atexit
    signal.signal(signal.SIGINT, _graceful_exit)
    signal.signal(signal.SIGTERM, _graceful_exit)
    atexit.register(_graceful_exit)

    logger.info(f"Iniciando {n_threads} navegadores. Total de itens: {len(jobs)}")

    # --- ADIÇÃO: try/finally para garantir logout/stop/join mesmo com exceções ---
    try:
        for w in workers:
            w.start()

        q.join()  # aguarda processar a fila

    finally:
        # Término normal ou por exceção: tenta logout/stop/join
        for w in workers:
            try:
                if hasattr(w, "logout"):
                    w.logout()
            except Exception:
                pass
            try:
                w.stop()
            except Exception:
                pass
        for w in workers:
            try:
                w.join(timeout=2.0)
            except Exception:
                pass

    logger.info("Processamento concluído. Veja output/resultados.csv")
    print("Processamento concluído. Veja output/resultados.csv")
    
    falhas = get_failed_results("output/resultados.csv")
    if falhas:
        logger.info(f"{len(falhas)} registros falharam e serão reprocessados.")
        page = BrowserFactory.new_browser(cfg)
        try_login(page, cfg["login_email"], cfg["login_senha"])
        client = JusbrasilClient(page=page, cfg=cfg)

        for url, nome in falhas:
            logger.info(f"Reprocessando: {nome}")
            try:
                res = client.submit_removal_form(url, nome)
                append_result(url, nome, res.status, f"Reprocessado: {res.msg}")
            except Exception as e:
                logger.error(f"Erro ao reprocessar {nome}: {e}")
                append_result(url, nome, "ERRO_REPROCESSAMENTO", str(e))

        logger.info("Reprocessamento concluído.")
        page.browser.quit()
    else:
        logger.info("Nenhuma falha encontrada para reprocessar.")


if __name__ == "__main__":
    main()
