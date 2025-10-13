# automation/jusbrasil.py
import time, os
from dataclasses import dataclass
from typing import Optional

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

            # 4) Preenche os campos do formulário (mapeados como no projeto antigo)
            try:
                close_popup = self.page.ele('css=i.icon-remove', timeout=30)
                if close_popup:
                    close_popup.wait.clickable(timeout=15)
                    if close_popup.states.has_rect:
                        close_popup.click()
                        self.page.wait(0.5)
            except Exception as e:
                logger.error(f"[submit_removal_form] Erro ao fechar popup: {type(e).__name__}: {e}")

            try:
                select_motivo = self.page.ele('css=#removal_reason', timeout=15)
                if select_motivo:
                    opt_vitima = self.page.ele('css=option[value="NOME_VITIMA"]', timeout=3)
                    if opt_vitima:
                        select_motivo.select(opt_vitima.text)
                        self.page.wait(0.5)
                    else:
                        # fallback: escolhe o 2º item
                        try:
                            if hasattr(select_motivo, 'select'):
                                select_motivo.select(1)
                        except Exception:
                            pass
            except Exception as e:
                logger.error(f"[submit_removal_form] Erro ao selecionar motivo: {type(e).__name__}: {e}")

            #    Nome
            try:
                nome_input = self.page.ele('css=#name_remove', timeout=6)
                if nome_input:
                    try:
                        nome_input.input(nome, clear=True)
                        self.page.wait(1)
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"[submit_removal_form] Erro ao preencher nome: {type(e).__name__}: {e}")

            #    Telefone
            try:
                tel_input = self.page.ele('css=#telephone', timeout=4)
                if tel_input:
                    try:
                        tel_input.input(self._random_phone(), clear=True)
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"[submit_removal_form] Erro ao preencher telefone: {type(e).__name__}: {e}")

            #    Anexo (PDF)
            try:
                doc_input = self.page.ele('css=#documentation', timeout=3)
                if doc_input:
                    # usa o mesmo arquivo do projeto novo
                    pdf_file = os.path.join(os.getcwd(), 'utilitarios', 'arquivo.pdf')
                    doc_input.input(pdf_file)
            except Exception as e:
                logger.error(f"[submit_removal_form] Erro ao preencher anexo: {type(e).__name__}: {e}")

            #    Enviar solicitação
            try:
                submit_btn = self.page.ele('css=button[type="submit"]', timeout=3)
                if submit_btn:
                    submit_btn.click()
                    self.page.wait(5)
            except Exception as e:
                logger.error(f"[submit_removal_form] Erro ao enviar solicitação: {type(e).__name__}: {e}")

            # 4.1) Checagens de bloqueio/página indisponível e Cloudflare novamente
            self._check_blockers_and_recover()
            self._wait_cloudflare_and_bypass()

            try:
                close_popup = self.page.ele('css=i.icon-remove', timeout=30)
                if close_popup:
                    close_popup.wait.clickable(timeout=15)
                    if close_popup.states.has_rect:
                        close_popup.click()
                        self.page.wait(0.5)
            except Exception as e:
                logger.error(f"[submit_removal_form] Erro ao fechar popup: {type(e).__name__}: {e}")

            #    Checkbox de confirmação
            try:
                cb = self.page.ele('css=#check_confirm', timeout=5)
                if cb:
                    try:
                        # DrissionPage: states.is_checked + .check()
                        while not self.page.ele('css=#check_confirm', timeout=5).states.is_checked:
                            self.page.ele('css=#check_confirm', timeout=5).check()
                            self.page.wait(1)
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"[submit_removal_form] Erro ao preencher checkbox: {type(e).__name__}: {e}")
            time.sleep(2)

            # 5) Enviar
            submit_btn = self.page.ele('css=button[type="submit"]', timeout=3)
            if submit_btn:
                submit_btn.click()
            else:
                logger.error(f"[submit_removal_form] Não localizei botão de envio no formulário: {type(e).__name__}: {e}")
                self._screenshot("sem_submit")
                return SubmitResult(False, "FORM_SEM_SUBMIT", "Não localizei botão de envio no formulário.")

            # 6) Pós-envio: checagens e detecção de sucesso
            time.sleep(2)
            self._check_blockers_and_recover()
            self._wait_cloudflare_and_bypass()
            seletores = ['css=i.icon-remove', 
                         'text:Apenas remover', 
                         'text:solicitada com sucesso', 
                         'css=div.message-error'
                        ]
            self.page.wait.eles_loaded(seletores, timeout=25, any_one=True)
            seletor, elemento = self.page.find(seletores[1:], timeout=25, any_one=True)

            # Página de sucesso
            if seletor == 'text:solicitada com sucesso':
                logger.info("[submit_removal_form] Remoção solicitada com sucesso.")
                return SubmitResult(True, "SUCESSO", "Remoção solicitada com sucesso.")

            # Página de erro
            if seletor == 'css=div.message-error':
                logger.error(f"[submit_removal_form] Erro de validação no formulário: {elemento.text}")
                return SubmitResult(False, "ERRO_VALIDACAO", f"Erro de validação no formulário: {elemento.text}")
            
            # Página sem confirmação
            if seletor == 'text:Apenas remover':
                logger.error("[submit_removal_form] Botão 'apenas remover' apareceu no resultado final.")
                return SubmitResult(False, "ERRO_VALIDACAO", f"Botão 'apenas remover' apareceu no resultado final.")

        except BlockedError as be:
            return SubmitResult(False, "BLOQUEADO", str(be))
        except Exception as e:
            self._screenshot("erro_form")
            logger.error(f"[submit_removal_form] Erro inesperado: {e}")
            return SubmitResult(False, "ERRO_FORM", f"Falha preenchendo/enviando formulário: {e}")
