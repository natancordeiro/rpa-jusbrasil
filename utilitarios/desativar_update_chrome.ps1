# Cria a chave de políticas do Google Update
New-Item -Path "HKLM:\SOFTWARE\Policies\Google\Update" -Force | Out-Null

# 0 = nunca verificar atualizações automaticamente
Set-ItemProperty "HKLM:\SOFTWARE\Policies\Google\Update" AutoUpdateCheckPeriodMinutes 0 -Type DWord

# Desabilita a UI de auto-update
Set-ItemProperty "HKLM:\SOFTWARE\Policies\Google\Update" DisableAutoUpdateChecksCheckboxValue 1 -Type DWord

# 0 = desativado para todos os apps do Google Update
Set-ItemProperty "HKLM:\SOFTWARE\Policies\Google\Update" UpdateDefault 0 -Type DWord

# Desativa atualizações do Chrome (GUID do Chrome estável)
Set-ItemProperty "HKLM:\SOFTWARE\Policies\Google\Update" "Update{8A69D345-D564-463C-AFF1-A69D9E530F96}" 0 -Type DWord
