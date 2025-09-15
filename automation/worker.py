# automation/worker.py
import threading
import time
from queue import Queue
from typing import Dict, Any

from automation.browser import BrowserFactory
from automation.jusbrasil import JusbrasilClient, BlockedError
from automation.login import try_login
from utils.logger import logger
from utils.io_helpers import append_result


class Worker(threading.Thread):
    def __init__(self, idx: int, jobs: Queue, config: Dict[str, Any], name: str | None = None):
        super().__init__(daemon=True, name=name or f"T{idx}")
        self.idx = idx
        self.jobs = jobs
        self.cfg = config
        self.page = None

    def _start_browser(self):
        self.page = BrowserFactory.new_browser(self.cfg)
        logger.info(f"[{self.name}] Chromium iniciado.")

    def _restart_browser(self):
        logger.warning(f"[{self.name}] Reiniciando navegador para trocar IP/porta…")
        self.page = BrowserFactory.recreate(
            prev_page=self.page,
            use_proxy=self.cfg.get('usar_proxy', False),
            proxy_extension_path=self.cfg.get('proxy_extension_path'),
        )
        logger.info(f"[{self.name}] Chromium recriado.")

    def run(self):
        self._start_browser()
        try:
            ok = try_login(self.page, self.cfg["login_email"], self.cfg["login_senha"])
            logger.info(f"Login: {'OK' if ok else 'não efetuado'}")
        except Exception as e:
            logger.warning(f"Falha ao tentar login: {e}")

        while True:
            try:
                job = self.jobs.get(timeout=1)
            except Exception:
                break

            url = job[0]
            nome = job[1]
            attempts = 0
            max_attempts = int(self.cfg.get('max_attempts_por_job', 3))

            while attempts < max_attempts:
                attempts += 1
                logger.info(f"[{self.name}] Processando: {url} ; {nome} (tentativa {attempts}/{max_attempts})")

                try:
                    client = JusbrasilClient(
                        page=self.page,
                        salvar_capturas=self.cfg.get('salvar_capturas', False),
                        evid_dir=self.cfg.get('evid_dir', 'output/screenshots'),
                    )
                    res = client.submit_removal_form(url, nome)

                    if res.status == "BLOQUEADO":
                        self._restart_browser()
                        time.sleep(2)
                        continue

                    append_result(url, nome, res.status, res.msg)
                    break

                except BlockedError:
                    self._restart_browser()
                    time.sleep(2)
                    continue

                except Exception as e:
                    logger.error(f"[{self.name}] Erro inesperado: {e}")
                    append_result(url, nome, "ERRO", str(e))
                    break

            else:
                append_result(url, nome, "ERRO", "Esgotadas as tentativas de processamento para este item.")

            self.jobs.task_done()

        try:
            self.page.browser.quit()
        except Exception:
            pass
        logger.info(f"[{self.name}] Finalizado.")
