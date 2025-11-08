# utils/mails_dp.py
from __future__ import annotations
from typing import Callable, Dict, Any, Optional
from DrissionPage import Chromium
import json

TARGETS = [
    '/api/email/generate',
    '/api/email/inbox',
    '/api/email/inbox/read',
    '/api/captcha/verify',
    '/api/nonce'
]

def _to_json(body) -> Dict[str, Any]:
    if body is None:
        return {}
    if isinstance(body, (bytes, bytearray)):
        try:
            return json.loads(body.decode('utf-8', 'ignore'))
        except Exception:
            return {}
    if isinstance(body, str):
        try:
            return json.loads(body)
        except Exception:
            return {}
    # alguns builds expõem body já como dict
    if isinstance(body, dict):
        return body
    return {}

def _pick_email_from_inbox(data: Dict[str, Any], want: Callable[[Dict[str, Any]], bool] | None = None):
    """Normaliza o shape do mails.org (emails: dict[id]->obj) e aplica um predicate opcional."""
    if not isinstance(data, dict) or not isinstance(data.get('emails'), dict):
        return None
    items = []
    for mid, m in data['emails'].items():
        if not isinstance(m, dict):
            continue
        subj = m.get('subject') or ''
        sndr = m.get('sender') or ''
        date = m.get('received_at') or m.get('date') or ''
        raw_body = m.get('body') or ''
        masked = (subj == 'Subject hidden until verification')
        item = {
            'id': str(mid),
            'subject': subj,
            'from': sndr,
            'date': date,
            'body': raw_body or '',
            'masked': bool(masked),
            'captcha': m.get('captcha'),
            '_raw': m,
        }
        items.append(item)
    # aplica filtro se houver
    if want:
        for it in items:
            if want(it):
                return it
        return None
    # se não houver filtro, devolve o mais recente que não esteja mascarado (se existir)
    for it in items:
        if not it['masked']:
            return it
    return items[0] if items else None

class MailClient:
    """
    Controla a aba do mails.org e ouve as respostas via listener oficial do DrissionPage.
    - wait_email_generated(): espera o /api/email/generate e devolve email + payload inteiro
    - wait_verification_message(): espera inbox até achar a mensagem desejada; se vier mascarada,
      continua ouvindo até chegar o /api/email/inbox/read correspondente.
    """
    def __init__(self, browser: Chromium):
        self.browser = browser
        self.tab = self.browser.new_tab()
        self.tab.listen.start('/api/email/generate')
        self.tab.get('https://mails.org/')
        # self.tab.listen.start(TARGETS)

        self.generated_email: Optional[str] = None
        self._mailbox_token: Optional[str] = None

    # -------- geração do alias --------
    def wait_email_generated(self, timeout: float = 30.0) -> str:
        """
        Espera pela resposta do /api/email/generate e devolve o e-mail gerado.
        """
        # já estamos em mails.org; a própria página costuma disparar nonce->generate no carregamento
        # vamos iterar pacotes até achar o generate
        packet = self.tab.listen.wait(timeout=timeout)
        data = _to_json(packet.response.body)
        email = data.get('email') or data.get('address')
        self.tab.listen.stop()
        if email:
            self.generated_email = email
            self._mailbox_token = data.get('token') or self._mailbox_token
            return self.generated_email or ""

        raise TimeoutError("Não capturei a resposta de /api/email/generate dentro do timeout.")

    # -------- ouvir inbox até achar a verificação --------
    def wait_verification_message(
        self,
        sender_contains: str,
        subject_prefix: str,
        timeout: float = 120.0,
    ):
        """
        Ouve /api/email/inbox até o 'emails' vir com conteúdo e
        encontrar a mensagem cujo remetente contém `sender_contains`
        e o assunto começa com `subject_prefix`.
        Retorna um dict simples com os campos mais úteis.
        """
        import time
        deadline = time.time() + (timeout if timeout else 10**9)

        # inicie a escuta antes (boas práticas do DrissionPage)
        self.tab.listen.start('/api/email/inbox')

        try:
            while time.time() < deadline:
                remaining = max(0.5, deadline - time.time())
                # steps(): itera “em tempo real”; timeout interrompe o iterador
                for packet in self.tab.listen.steps(timeout=remaining):
                    # podem vir pacotes não-JSON; ignore com segurança
                    try:
                        data = _to_json(packet.response.body)
                    except Exception:
                        continue

                    emails = data.get('emails')
                    # polling costuma trazer [] ou {} – apenas continue
                    if not emails:
                        continue

                    # normaliza iteração (tanto dict quanto list)
                    if isinstance(emails, dict):
                        items = [(k, v) for k, v in emails.items()]
                    else:  # assume lista de dicts
                        items = [(str(e.get('id', '')), e) for e in emails if isinstance(e, dict)]

                    for msg_id, msg in items:
                        sender = (msg.get('sender') or msg.get('from') or '').lower()
                        subject = msg.get('subject') or ''
                        if sender_contains.lower() in sender and subject.startswith(subject_prefix):
                            body = msg.get('body') or ''
                            received_at = msg.get('received_at')
                            return {
                                'id': msg_id,
                                'sender': msg.get('sender') or msg.get('from'),
                                'subject': subject,
                                'body': body,
                                'received_at': received_at,
                                'raw': msg,  # mantém bruto para quem precisar
                            }
                # se o iterador terminou por timeout mas ainda há tempo, loop continua
        finally:
            # pare a escuta ao sair (evita perder pacotes no meio)
            self.tab.listen.stop()

        raise TimeoutError('Não encontrei a mensagem de verificação dentro do timeout.')
