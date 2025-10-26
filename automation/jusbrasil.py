# automation/jusbrasil.py
import time, os
from dataclasses import dataclass
from bs4 import BeautifulSoup

from DrissionPage import ChromiumPage
from utils.logger import logger
from utils.cf_bypass import CloudflareBypasser
from automation.login import try_login

class BlockedError(Exception):
    """Levanta quando o site bloqueia o IP (precisa reiniciar o navegador)."""


@dataclass
class SubmitResult:
    ok: bool
    status: str
    msg: str = ""


class JusbrasilClient:
    def __init__(self, page: ChromiumPage, cfg: dict):
        self.cfg = cfg
        self.page = page
        self.salvar_capturas = self.cfg.get('salvar_capturas', False)
        self.evid_dir = self.cfg.get('evid_dir', 'output/screenshots')
        self.login_refresh_interval = self.cfg.get("login_refresh_interval", 10)
        self.remocoes_contador = 0

    # ---------- helpers ----------

    def _screenshot(self, name: str) -> None:
        if not self.salvar_capturas:
            return
        try:
            file = f"{self.evid_dir}/{name}.png"
            self.page.get_screenshot(file)
            logger.info(f"Screenshot salvo: {file}")
        except Exception as e:
            logger.warning(f"Falha ao salvar screenshot: {e}")

    def _check_blockers_and_recover(self) -> None:
        """Replica as verificações do projeto base:
           - bloqueio ('you have been blocked') => BlockedError
           - 'Página não disponível' => refresh nas abas
        """
        html = (self.page.html or "").lower()

        # 1) Bloqueio de IP
        if 'you have been blocked' in html or 'access denied' in html:
            self._screenshot("bloqueado")
            logger.error('Bloqueado pelo site. Tentando novamente com outro IP.')
            raise BlockedError('IP bloqueado / Access denied')

        if 'Página não disponível' in html or 'página não disponível' in html.lower():
            logger.warning('Página indisponível. Efetuando refresh.')
            try:
                self.page.refresh()
                time.sleep(3)

                # 🔍 Após refresh, o site às vezes faz logout.
                logado = self.page.ele(
                    'css=div.topbar-profile, img[class*="avatar_image"], span[class*="avatar_fallback"]',
                    timeout=10
                )
                if not logado:
                    logger.warning("Sessão desconectada após erro de página. Reautenticando...")
                    ok = try_login(self.page, self.cfg["login_email"], self.cfg["login_senha"])
                    if not ok:
                        logger.error("Falha ao relogar na conta.")
                    else:
                        logger.info("Login restaurado com sucesso após desconexão.")

            except Exception as e:
                logger.warning(f"Falha ao dar refresh na aba: {e}")

    def _wait_cloudflare_and_bypass(self) -> bool:
        """Verifica se alguma aba está no 'Just a moment...' e tenta resolver via self.bypass()."""
        time.sleep(5)  # igual ao base antes de varrer as abas
        resolved_any = False

        try:
            title = (self.page.title or "").lower()
        except Exception:
            title = ""
        if 'moment' in title or 'just a moment' in title:
            logger.info(f"Detectado Cloudflare (Just a moment...). Tentando bypass...")
            resolveu = CloudflareBypasser(self.page, max_retries=3).bypass()
            if not resolveu:
                logger.info(f"CAPTCHA/CF não resolvido")
                return False
            logger.info(f"CAPTCHA/CF resolvido")
            resolved_any = True

        return True if resolved_any else True
    
    @staticmethod
    def go_report_via_form_submit(page):
        """Cria e submete um <form> igual ao do site, para navegar ao 'Reportar' mantendo o Referer."""
        js = r"""
        (function () {
        var f = document.createElement('form');
        f.method = 'GET';
        f.action = 'https://www.jusbrasil.com.br/contato/remocao';
        var i = document.createElement('input');
        i.type = 'hidden';
        i.name = 'ref';
        i.value = 'RemoveInformationTrigger';
        f.appendChild(i);
        document.body.appendChild(f);
        f.submit();
        })();
        """
        page.run_js(js)

    def _go_report_via_form_submit(self) -> None:
        """
        Replica a navegação do projeto antigo:
        cria e submete um <form> GET para /contato/remocao mantendo o 'ref' (Referer lógico).
        """
        js = r"""
        (function () {
            try {
                var f = document.createElement('form');
                f.method = 'GET';
                f.action = 'https://www.jusbrasil.com.br/contato/remocao';
                var i = document.createElement('input');
                i.type = 'hidden';
                i.name = 'ref';
                i.value = 'RemoveInformationTrigger';
                f.appendChild(i);
                document.body.appendChild(f);
                f.submit();
            } catch (e) {}
        })();
        """
        try:
            self.page.run_js(js)
        except Exception:
            # fallback: tenta ir direto (sem preservar ref) se o JS falhar
            try:
                self.page.get('https://www.jusbrasil.com.br/contato/remocao')
            except Exception:
                pass

    def _random_phone(self) -> str:
        # gera um telefone válido "1199XXXXXXX" ou "(11) 9XXXX-XXXX"
        import random
        ddd = random.randint(11, 99)
        p1 = random.randint(90000, 99999)
        p2 = random.randint(0000, 9999)
        return f"({ddd}) {str(p1)[0]}{str(p1)[1:]}-{p2:04d}"

    # ---------- implementação pedida: preencher/enviar formulário ----------

    def submit_removal_form(self, diario_url: str, nome: str) -> SubmitResult:
        """
        Abre a página do item, navega até 'Remoção de informações' e preenche o formulário.
        Reproduz comportamentos do projeto antigo:
          - tenta clicar 'Reportar' / 'Mais'
          - mantém o 'ref' ao ir para /contato/remocao (via form submit em JS)
          - verifica bloqueios ('you have been blocked' / 'access denied')
          - trata 'Página não disponível'
          - tenta contornar 'Just a moment...' (Cloudflare)
          - seleciona motivo 'NOME_VITIMA', preenche nome, telefone, anexa PDF, marca checkbox e envia
        """
        BASE_URL = "https://www.jusbrasil.com.br"

        try:
            # 1) Abre a página original (onde aparece o nome)
            self.page.get(diario_url)
            time.sleep(1.5)
            self._check_blockers_and_recover()

            # 1.5) Verifica se está logado, e refaz o login
            logado = self.page.ele('css=div.topbar-profile, img[class*="avatar_image"], span[class*="avatar_fallback"]', timeout=15)
            if not logado:
                ok = try_login(self.page, self.cfg["login_email"], self.cfg["login_senha"])

            # 2) Vá para o formulário
            self._go_report_via_form_submit()

            time.sleep(1)

            # 3) Checagens de bloqueio/página indisponível e Cloudflare novamente
            self._check_blockers_and_recover()
            self._wait_cloudflare_and_bypass()

            telefone = self._random_phone()
            full_name = self.page.ele('#full_name', timeout=20).attrs['value']
            pdf_file = (os.path.join(os.getcwd(), 'utilitarios', 'arquivo.pdf'), b"%PDF-1.4\n%EOF", "application/pdf")

            default_headers = {
                "User-Agent": self.page.user_agent,
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Connection": "keep-alive",
            }

            confirm_url = f"{BASE_URL}/contato/remocao/confirmacao"
            data_confirm = {
                "referrer": diario_url,
                "removal_reason": "NOME_VITIMA",
                "name_remove": nome,
                "full_name": full_name,
                "telephone": telefone,
                "email": self.cfg["login_email"],
                "submit-contact": ""
            }

            files = {
                "documentation": pdf_file
            }

            # Primeira requisição: confirmação
            self.page.reconnect(10)
            self.page.wait(2)
            resp = self.page.post(confirm_url, headers=default_headers, data=data_confirm, files=files, retry=3)

            if resp.status_code != 200:
                logger.error(f"Falha na etapa de confirmação: status {resp.status_code}")
                return SubmitResult(ok=False, status=str(resp.status_code), msg="Falha na confirmação")

            # Extrai file_path da resposta
            soup = BeautifulSoup(resp.text, "html.parser")
            file_path_input = soup.find("input", {"id": "file_path"})
            if not file_path_input:
                logger.error("Campo file_path não encontrado na resposta de confirmação")
                return SubmitResult(ok=False, status="error", msg="file_path não encontrado")

            file_path = file_path_input.attrs.get("value", "")

            # Segunda requisição: envio final
            remocao_url = f"{BASE_URL}/contato/remocao/enviar"
            data_envio = {
                "csrf_token": "None",
                "referrer": diario_url,
                "removal_reason": "NOME_VITIMA",
                "full_name": full_name,
                "name_remove": nome,
                "telephone": telefone,
                "email": self.cfg["login_email"],
                "file_path": file_path,
                "file_name": "arquivo.pdf",
                "check_confirm": "y",
                "g-recaptcha-response": ""
            }

            resp_envio = self.page.post(remocao_url, headers=default_headers, data=data_envio, retry=3)

            if resp_envio.status_code == 200:
                logger.info("Remoção bem-sucedida.")

                # 🔁 Controle de logout/login periódico
                self.remocoes_contador += 1
                if self.remocoes_contador >= self.login_refresh_interval:
                    logger.info(f"{self.remocoes_contador} remoções realizadas. Renovando login...")
                    self.remocoes_contador = 0

                    try:
                        # Logout manual — geralmente via URL ou botão
                        self.page.get(f"{BASE_URL}/logout")
                        time.sleep(2)

                        ok = try_login(self.page, self.cfg["login_email"], self.cfg["login_senha"])
                        if ok:
                            logger.info("Login renovado com sucesso.")
                        else:
                            logger.error("Falha ao renovar login automaticamente.")
                    except Exception as e:
                        logger.error(f"Erro ao renovar login: {e}")

                return SubmitResult(ok=True, status="SUCESSO", msg="Remoção concluída com sucesso")
            
            elif resp_envio.status_code == 409:
                soup = BeautifulSoup(resp_envio.text, "html.parser")
                msg_erro = soup.find("div", {"class": "message-error"})
                erro_texto = msg_erro.text.strip() if msg_erro else "Erro desconhecido"
                logger.warning(f"Remoção não concluída (já solicitada?): {erro_texto}")

                # 🔁 Controle de logout/login periódico
                self.remocoes_contador += 1
                if self.remocoes_contador >= self.login_refresh_interval:
                    logger.info(f"{self.remocoes_contador} remoções realizadas. Renovando login...")
                    self.remocoes_contador = 0

                    try:
                        # Logout manual — geralmente via URL ou botão
                        self.page.get(f"{BASE_URL}/logout")
                        time.sleep(2)

                        ok = try_login(self.page, self.cfg["login_email"], self.cfg["login_senha"])
                        if ok:
                            logger.info("Login renovado com sucesso.")
                        else:
                            logger.error("Falha ao renovar login automaticamente.")
                    except Exception as e:
                        logger.error(f"Erro ao renovar login: {e}")

                return SubmitResult(ok=False, status="ERRO_VALIDACAO", msg=erro_texto)
            
            else:
                logger.error(f"Erro inesperado na remoção. Status {resp_envio.status_code}")
                return SubmitResult(ok=False, status=str(resp_envio.status_code), msg="Erro inesperado")

        except BlockedError as be:
            return SubmitResult(False, "BLOQUEADO", str(be))
        except Exception as e:
            logger.error(f"[submit_removal_form] Erro inesperado: {e}")
            return SubmitResult(False, "ERRO_FORM", f"Falha preenchendo/enviando formulário: {e}")
