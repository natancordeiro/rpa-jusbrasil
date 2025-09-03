# Caminho da chave de políticas do Google Update
$regPath = "HKLM:\SOFTWARE\Policies\Google\Update"

# Remove os valores criados
Remove-ItemProperty -Path $regPath -Name AutoUpdateCheckPeriodMinutes -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $regPath -Name DisableAutoUpdateChecksCheckboxValue -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $regPath -Name UpdateDefault -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $regPath -Name "Update{8A69D345-D564-463C-AFF1-A69D9E530F96}" -ErrorAction SilentlyContinue

# Se quiser apagar a chave inteira de Update:
Remove-Item -Path $regPath -Recurse -Force -ErrorAction SilentlyContinue
