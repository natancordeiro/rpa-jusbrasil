import imaplib
import email
from email.header import decode_header
import time
import random
import string

class MailClient:
    def __init__(self, user_email, app_password, imap_server='imap.gmail.com'):
        self.user_email = user_email
        self.app_password = app_password
        self.imap_server = imap_server
        self.mail = None

    def connect(self):
        self.mail = imaplib.IMAP4_SSL(self.imap_server)
        self.mail.login(self.user_email, self.app_password)

    def gerar_alias_gmail(self, base_email=None, tamanho_tag=10):
        """
        Gera um alias para Gmail no formato usuario+tag@gmail.com.
        Por padrão usa o user_email da instância, mas pode receber outro.
        """
        email_to_use = base_email or self.user_email

        if '@' not in email_to_use:
            raise ValueError('Endereço de email inválido')

        local, domain = email_to_use.split('@', 1)
        domain = domain.lower()

        if domain != 'gmail.com':
            raise ValueError('Somente domínios gmail.com são suportados')

        tag = ''.join(random.choices(string.ascii_lowercase + string.digits, k=tamanho_tag))
        return f"{local}+{tag}@{domain}"

    def decodificar_subject(self, subject):
        """
        Decodifica um header de assunto potencialmente quebrado em múltiplas partes codificadas.
        """
        decoded_fragments = decode_header(subject)
        parts = []

        for fragment, encoding in decoded_fragments:
            if isinstance(fragment, bytes):
                if encoding:
                    parts.append(fragment.decode(encoding, errors='replace'))
                else:
                    parts.append(fragment.decode(errors='replace'))
            else:
                parts.append(fragment)

        return ''.join(parts)

    def wait_for_new_message(
        self,
        sender_filter,
        subject_prefix="",
        check_interval=10,
        on_match='delete'        # 'delete' | 'read' | 'none'
    ):
        """
        Espera por novas mensagens não lidas de um remetente específico.
        Filtra pelo assunto começando com subject_prefix (se fornecido).
        Ao encontrar, executa a ação (apagar, marcar como lida ou nada) e retorna
        SEMPRE um dicionário com subject, from, date e body.
        - on_match: 'delete' move p/ lixeira e expunge o original; 'read' marca como lida; 'none' não altera flags.
        """
        import re

        while True:
            self.mail.select("INBOX")
            search_criteria = f'(UNSEEN FROM "{sender_filter}")'
            result, data = self.mail.search(None, search_criteria)
            if result != 'OK':
                time.sleep(check_interval)
                continue

            email_ids = data[0].split()
            if email_ids:
                # do mais recente para o mais antigo
                for eid in reversed(email_ids):
                    result, msg_data = self.mail.fetch(eid, "(RFC822)")
                    if result != 'OK' or not msg_data or not msg_data[0]:
                        continue

                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # Assunto decodificado
                    subject = msg.get("Subject", "")
                    subject_text = self.decodificar_subject(subject) if subject else ""

                    if subject_text.startswith(subject_prefix or "") or subject_prefix == "":
                        # Extrai corpo em texto simples (fallback HTML -> texto)
                        body_text = ""
                        if msg.is_multipart():
                            # busca text/plain sem attachment
                            for part in msg.walk():
                                ctype = part.get_content_type()
                                disp = (part.get("Content-Disposition") or "").lower()
                                if ctype == "text/plain" and "attachment" not in disp:
                                    payload = part.get_payload(decode=True) or b""
                                    charset = part.get_content_charset() or "utf-8"
                                    try:
                                        body_text = payload.decode(charset, errors="replace")
                                    except LookupError:
                                        body_text = payload.decode(errors="replace")
                                    break
                            # fallback: tenta text/html
                            if not body_text:
                                for part in msg.walk():
                                    if part.get_content_type() == "text/html":
                                        payload = part.get_payload(decode=True) or b""
                                        charset = part.get_content_charset() or "utf-8"
                                        try:
                                            html = payload.decode(charset, errors="replace")
                                        except LookupError:
                                            html = payload.decode(errors="replace")
                                        # remove tags básicas
                                        body_text = re.sub(r"<[^>]+>", " ", html)
                                        break
                        else:
                            payload = msg.get_payload(decode=True) or b""
                            charset = msg.get_content_charset() or "utf-8"
                            try:
                                body_text = payload.decode(errors="replace") if not charset else payload.decode(charset, errors="replace")
                            except LookupError:
                                body_text = payload.decode(errors="replace")

                        # Ação na mensagem encontrada
                        try:
                            if on_match == 'read':
                                self.mail.store(eid, '+FLAGS', '\\Seen')
                            elif on_match == 'delete':
                                # Remove o original da INBOX
                                self.mail.store(eid, '+FLAGS', '\\Deleted')
                                self.mail.expunge()
                        except Exception:
                            pass

                        return {
                            "subject": subject_text,
                            "from": msg.get("From"),
                            "date": msg.get("Date"),
                            "body": body_text
                        }

            time.sleep(check_interval)
