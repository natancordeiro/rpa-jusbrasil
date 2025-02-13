"""
Modulo destinado para armazenar os seletores utilizados na Automação. 

XPATH | CSS
"""

XPATH = {
    'page_verify_human': 'xpath=//p[contains(text(), "you are human")]',
    'sucesso': 'xpath=//h1[contains(text(), "solicitada com sucesso")]',
    'reportar': 'xpath=//button[span[text()="Reportar"]]'
}

CSS = {
    'logado': 'css=div.topbar-profile, img[class*="avatar_image"]',
    'login': 'css=.btn-login, span[class*="user-menu-unlogged"] button:last-of-type',
    'input_login': 'css=#FormFieldset-email',
    'submit': 'css=button[type="submit"]',
    'input_senha': 'css=#FormFieldset-password',
    'btn_reportar_pagina': 'css=.RemoveInformationTrigger-btn',
    'close_popup': 'css=i.icon-remove',
    'select_motivo': 'css=#removal_reason',
    'outros': 'css=option[value="OUTRO"]',
    'nome_vitima': 'css=option[value="NOME_VITIMA"]',
    'input_nome': 'css=#name_remove',
    'telefone': 'css=#telephone',
    'anexo': '#documentation',
    'checkbox': '#check_confirm',
    'frame_recaptcha': "css=iframe[src*='recaptcha']",
    'check_captcha': 'css=#recaptcha-anchor',
    'repsonse_captcha': 'css=#g-recaptcha-response',
    'erro': 'css=div.message-error',
    'mais': 'css=div[class*="layout_mainContent"] button[aria-label="Mais"]',
    'opcao': 'css=#reportType_1 ~ label',
    'check': 'css=.selection-control-label',
    'btn_reportar': 'css=div.LoginRequired button'
}