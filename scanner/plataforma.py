"""
plataforma.py — Tudo que muda entre Windows e Linux fica concentrado aqui.

O NetProbe roda nos dois sistemas. As diferenças são poucas:

  Assunto              Windows                         Linux
  -------------------  ------------------------------  -------------------------------------
  Comando ping         ping -n 1 -w <ms>               ping -c 1 -W <segundos>
  Pergunta ARP         função nativa SendARP           o próprio kernel envia o ARP quando
                       (iphlpapi.dll)                  mandamos um pacote para o IP
  Tabela ARP (cache)   comando "arp -a"                arquivo /proc/net/arp
  MAC desta máquina    SendARP no próprio IP           /sys/class/net/<placa>/address

Nenhuma das duas formas precisa de administrador/root nem de biblioteca extra.
"""

import os
import re
import subprocess
import sys
import uuid

WINDOWS = sys.platform == "win32"
LINUX = sys.platform.startswith("linux")
MACOS = sys.platform == "darwin"

# No Windows, evita abrir uma janelinha preta para cada comando executado
SEM_JANELA = 0x08000000 if WINDOWS else 0

# Força mensagens em inglês nos comandos do Linux (facilita ler a saída do ping)
AMBIENTE_C = dict(os.environ, LC_ALL="C", LANG="C")

_REGEX_MAC = re.compile(r"([0-9a-fA-F]{1,2}[:-]){5}[0-9a-fA-F]{1,2}")
_REGEX_IP = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")


def nome_sistema():
    if WINDOWS:
        return "Windows"
    if LINUX:
        return "Linux"
    if MACOS:
        return "macOS"
    return sys.platform


def normalizar_mac(mac):
    """Padroniza para AA:BB:CC:DD:EE:FF (aceita '-' ou ':', minúsculas e '0:1a:...')."""
    if not mac:
        return None
    partes = re.split(r"[:-]", mac.strip())
    if len(partes) != 6:
        return None
    try:
        texto = ":".join("%02X" % int(p, 16) for p in partes)
    except ValueError:
        return None
    if texto in ("00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF"):
        return None  # entrada vazia / broadcast: não é um dispositivo
    return texto


def ler_tabela_arp():
    """
    Lê a tabela ARP (cache) do sistema operacional: {ip: mac}.
    Só entra quem tem MAC resolvido de verdade (respondeu ao ARP).
    """
    tabela = {}
    if LINUX and os.path.exists("/proc/net/arp"):
        # Formato: IP  HWtype  Flags  HWaddress  Mask  Device
        # Flags 0x2 = entrada completa (o dispositivo respondeu ao ARP)
        try:
            with open("/proc/net/arp") as arquivo:
                next(arquivo)  # pula o cabeçalho
                for linha in arquivo:
                    colunas = linha.split()
                    if len(colunas) >= 4 and int(colunas[2], 16) & 0x2:
                        mac = normalizar_mac(colunas[3])
                        if mac:
                            tabela[colunas[0]] = mac
        except (OSError, ValueError, StopIteration):
            pass
        return tabela

    # Windows e macOS: comando "arp -a"
    try:
        saida = subprocess.run(["arp", "-a"] if WINDOWS else ["arp", "-an"],
                               capture_output=True, text=True, errors="replace",
                               timeout=10, creationflags=SEM_JANELA).stdout
    except (OSError, subprocess.TimeoutExpired):
        return tabela
    for linha in saida.splitlines():
        ip, mac = _REGEX_IP.search(linha), _REGEX_MAC.search(linha)
        if ip and mac:
            mac_ok = normalizar_mac(mac.group(0))
            if mac_ok:
                tabela[ip.group(1)] = mac_ok
    return tabela


def mac_desta_maquina(ip):
    """
    MAC da placa de rede desta máquina que tem o IP informado.
    (A própria máquina não aparece na tabela ARP, então buscamos de outro jeito.)
    """
    if LINUX:
        try:
            # "ip -o -4 addr" lista: <n>: <placa> inet <ip>/<máscara> ...
            saida = subprocess.run(["ip", "-o", "-4", "addr"], capture_output=True,
                                   text=True, timeout=5, env=AMBIENTE_C).stdout
            for linha in saida.splitlines():
                colunas = linha.split()
                if "inet" in colunas and colunas[colunas.index("inet") + 1].split("/")[0] == ip:
                    with open("/sys/class/net/%s/address" % colunas[1]) as arquivo:
                        return normalizar_mac(arquivo.read())
        except (OSError, subprocess.TimeoutExpired, IndexError):
            pass
    # Último recurso (qualquer sistema): MAC de uma placa desta máquina
    numero = uuid.getnode()
    if (numero >> 40) & 1:  # bit "multicast" ligado = número inventado, não é MAC real
        return None
    return normalizar_mac(":".join("%02X" % ((numero >> s) & 0xFF) for s in range(40, -1, -8)))
