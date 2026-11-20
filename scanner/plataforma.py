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
        placa = placa_de_rede_linux(ip)
        if placa:
            try:
                with open("/sys/class/net/%s/address" % placa) as arquivo:
                    return normalizar_mac(arquivo.read())
            except OSError:
                pass
    # Último recurso (qualquer sistema): MAC de uma placa desta máquina
    numero = uuid.getnode()
    if (numero >> 40) & 1:  # bit "multicast" ligado = número inventado, não é MAC real
        return None
    return normalizar_mac(":".join("%02X" % ((numero >> s) & 0xFF) for s in range(40, -1, -8)))


def eh_root():
    """True se o programa está rodando como root (Linux, via sudo)."""
    return hasattr(os, "geteuid") and os.geteuid() == 0


def placa_de_rede_linux(ip):
    """Nome da placa de rede (ex: wlan0, wlp2s0) que tem o IP informado, ou None."""
    try:
        saida = subprocess.run(["ip", "-o", "-4", "addr"], capture_output=True,
                               text=True, timeout=5, env=AMBIENTE_C).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    for linha in saida.splitlines():
        colunas = linha.split()
        if "inet" in colunas and colunas[colunas.index("inet") + 1].split("/")[0] == ip:
            return colunas[1]
    return None


def rede_desta_maquina(ip):
    """
    Rede (com a máscara REAL) da placa que tem o IP informado, ex: "172.20.10.0/28".
    Por que importa: o hotspot do iPhone usa /28 (só 14 endereços), não /24.
    Se não der para descobrir, ou se a máscara for maior que /24 (rede grande demais
    para varrer), sugerimos a /24 do IP.
    """
    prefixo = None
    try:
        if WINDOWS:
            # "netsh" lista: Endereço IP: x.x.x.x  /  Prefixo de Sub-rede: rede/NN
            saida = subprocess.run(["netsh", "interface", "ipv4", "show", "addresses"],
                                   capture_output=True, text=True, errors="replace",
                                   timeout=5, creationflags=SEM_JANELA).stdout
            achei_ip = False
            for linha in saida.splitlines():
                if ip in _REGEX_IP.findall(linha) and "/" not in linha:
                    achei_ip = True
                elif achei_ip and re.search(r"\d+\.\d+\.\d+\.\d+/(\d+)", linha):
                    prefixo = int(re.search(r"\d+\.\d+\.\d+\.\d+/(\d+)", linha).group(1))
                    break
        elif LINUX:
            saida = subprocess.run(["ip", "-o", "-4", "addr"], capture_output=True,
                                   text=True, timeout=5, env=AMBIENTE_C).stdout
            achado = re.search(r"inet %s/(\d+)" % re.escape(ip), saida)
            if achado:
                prefixo = int(achado.group(1))
    except (OSError, subprocess.TimeoutExpired, ValueError):
        prefixo = None
    if prefixo is None or prefixo < 24 or prefixo > 30:
        prefixo = 24
    import ipaddress
    return str(ipaddress.ip_network("%s/%d" % (ip, prefixo), strict=False))


def ler_vizinhos_linux():
    """
    Tabela de vizinhos do kernel com DETALHES, via "ip -s neigh":
        {ip: {"mac": ..., "estado": "REACHABLE"/"STALE"/"FAILED"/..., "confirmado_ha": segundos}}
    "confirmado_ha" = há quantos segundos o vizinho respondeu pela última vez.
    Devolve None se o comando "ip" não existir.
    """
    try:
        saida = subprocess.run(["ip", "-s", "-4", "neigh", "show"], capture_output=True,
                               text=True, timeout=5, env=AMBIENTE_C).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    vizinhos = {}
    for linha in saida.splitlines():
        colunas = linha.split()
        if not colunas:
            continue
        info = {"mac": None, "estado": colunas[-1].upper(), "confirmado_ha": None}
        if "lladdr" in colunas:
            info["mac"] = normalizar_mac(colunas[colunas.index("lladdr") + 1])
        if "used" in colunas:
            tempos = colunas[colunas.index("used") + 1].split("/")  # usado/confirmado/atualizado
            if len(tempos) >= 2 and tempos[1].isdigit():
                info["confirmado_ha"] = int(tempos[1])
        vizinhos[colunas[0]] = info
    return vizinhos
