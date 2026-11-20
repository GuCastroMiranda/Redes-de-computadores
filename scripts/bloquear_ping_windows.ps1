# Demonstração do ITEM 2 (ARP Probe) - rodar no notebook WINDOWS de um COLEGA, como Administrador.
#   .\scripts\bloquear_ping_windows.ps1 on    -> bloqueia ping de entrada
#   .\scripts\bloquear_ping_windows.ps1 off   -> remove o bloqueio
# Obs: em rede "Pública" o Windows normalmente JÁ bloqueia ping por padrão.
param([string]$acao)
$nome = "NetProbe-Demo-BloqueiaPing"
if ($acao -eq "on") {
  New-NetFirewallRule -DisplayName $nome -Protocol ICMPv4 -IcmpType 8 -Direction Inbound -Action Block | Out-Null
  Write-Host "Ping BLOQUEADO."
} elseif ($acao -eq "off") {
  Remove-NetFirewallRule -DisplayName $nome -ErrorAction SilentlyContinue
  Write-Host "Ping LIBERADO."
} else { Write-Host "Uso: .\scripts\bloquear_ping_windows.ps1 on|off" }
