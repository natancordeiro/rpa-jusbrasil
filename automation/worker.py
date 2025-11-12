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
        self.browser = None

    def _start_browser(self):
        self.browser = BrowserFactory.new_browser(self.cfg)
        self.page = self.browser.latest_tab
        logger.info(f"[{self.name}] Chromium iniciado.")

    def _restart_browser(self):
        logger.warning(f"[{self.name}] Reiniciando navegador para trocar IP/porta…")
        self.browser = BrowserFactory.recreate(prev_page=self.page,cfg=self.cfg)
        self.page = self.browser.latest_tab
        logger.info(f"[{self.name}] Chromium recriado.")

    def run(self):
        self._start_browser()
        try:
            ok = try_login(self.browser, rotate=True, cfg=self.cfg)
            logger.info(f"Login: {'OK' if ok else 'não efetuado'}")
        except Exception as e:
            logger.warning(f"Falha ao tentar login: {e}")

        while True:
            try:
                job = self.jobs.get(timeout=1)
                if isinstance(job, (list, tuple)):
                    if len(job) == 3:
                        idx, url, nome = job
                    else:
                        url, nome = job
                        idx = 0
                else:
                    # se for dict, aceita também (retrocompatível)
                    idx = int(job.get("idx", 0))
                    url = job["url"]
                    nome = job["nome"]

                print(f"link {idx} {url}", flush=True)
            except Exception:
                break

            attempts = 0
            max_attempts = int(self.cfg.get('max_attempts_por_job', 3))

            while attempts < max_attempts:
                attempts += 1
                logger.info(f"[{self.name}] Processando: {url} ; {nome} (tentativa {attempts}/{max_attempts})")

                try:
                    client = JusbrasilClient(
                        browser=self.browser,
                        cfg=self.cfg
                    )
                    res = client.submit_removal_form(url, nome)

                    if res.status == "BLOQUEADO":
                        self._restart_browser()
                        time.sleep(2)
                        try:
                            ok = try_login(self.browser, cfg=self.cfg) or try_login(self.browser, rotate=True, cfg=self.cfg)
                            logger.info(f"[{self.name}] Reautenticação pós-bloqueio: {'OK' if ok else 'falhou'}")
                        except Exception as e:
                            logger.warning(f"[{self.name}] Erro ao reautenticar pós-bloqueio: {e}")
                        continue

                    append_result(url, nome, res.status, res.msg, idx=idx)
                    break

                except BlockedError:
                    self._restart_browser()
                    time.sleep(2)
                    try:
                        ok = try_login(self.browser, cfg=self.cfg) or try_login(self.browser, rotate=True, cfg=self.cfg)
                        logger.info(f"[{self.name}] Reautenticação pós-bloqueio: {'OK' if ok else 'falhou'}")
                    except Exception as e:
                        logger.warning(f"[{self.name}] Erro ao reautenticar pós-bloqueio: {e}")
                    continue

                except Exception as e:
                    logger.error(f"[{self.name}] Erro inesperado: {e}")
                    append_result(url, nome, "ERRO", str(e), idx=idx)
                    break

            else:
                append_result(url, nome, "ERRO", "Esgotadas as tentativas de processamento para este item.", idx=idx)

            self.jobs.task_done()

        try:
            self.logout()
            self.page.browser.quit()
        except Exception:
            pass
        logger.info(f"[{self.name}] Finalizado.")

    def logout(self):
        try:
            self.page.get("https://www.jusbrasil.com.br/logout")
            logger.info("[logout] Sessão encerrada.")
            time.sleep(0.5)
        except Exception:
            pass
