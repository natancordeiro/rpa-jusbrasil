import yaml

def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    cfg.setdefault("threads", 2)
    cfg.setdefault("arquivo_input", "dados.txt")
    cfg.setdefault("timeout_padrao", 25)
    cfg.setdefault("headless", False)
    cfg.setdefault("janela_maximizada", True)
    cfg.setdefault("salvar_capturas", True)
    cfg.setdefault("usar_proxy", False)
    cfg.setdefault("proxy_extension_path", "")
    cfg.setdefault("porta_inicial", 53000)
    cfg.setdefault("porta_final", 60000)
    cfg.setdefault("mail_user_email", "")
    cfg.setdefault("mail_app_password", "")
    cfg.setdefault("imap_server", "imap.gmail.com")
    auth = cfg.get("auth", {}) if isinstance(cfg.get("auth", {}), dict) else {}
    auth.setdefault("mode", "cadastro")  # valores: 'cadastro' | 'login'
    auth.setdefault("accounts_csv", "")  # caminho do CSV com colunas email,senha
    auth.setdefault("accounts_csv_delimiter", "")  # se vazio, detecta automaticamente
    auth.setdefault("persist_rotation_state", True)  # manter estado entre execuções
    auth.setdefault("rotation_state_path", "output/accounts_state.json")  # onde salvar estado
    cfg["auth"] = auth
    return cfg
