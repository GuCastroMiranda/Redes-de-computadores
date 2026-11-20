"""
arp_probe.py — [ITEM 2] Mecanismo de Colisão / ARP Probe.

Problema: muitos dispositivos (ex: Windows com firewall ligado, iPhone) BLOQUEIAM o
ping (ICMP). Para o Ping Sweep eles parecem "offline", mas estão ligados na rede.

Solução: para cada IP que NÃO respondeu ao ping, mandamos uma pergunta ARP:
    "Quem tem o IP 192.168.0.X? Me diga seu MAC."
O ARP é da CAMADA 2 (enlace). Um dispositivo precisa responder ARP para conseguir
usar a rede local, então o firewall normalmente NÃO bloqueia isso.

  - Se alguém respondeu ao ARP -> o IP está OCUPADO (online, só bloqueia ICMP).
  - Se ninguém respondeu       -> o IP está realmente VAZIO (offline).

Isso é o mesmo princípio do "ARP Probe" (RFC 5227), usado para detectar
colisão/conflito de IP antes de um dispositivo assumir um endereço.

Como fazemos (sem precisar de administrador/root):
  - Windows: chamamos a função nativa SendARP (biblioteca iphlpapi.dll) via ctypes.
             Ela envia o ARP e devolve o MAC de quem respondeu.
  - Linux:   enviamos um pacote UDP qualquer para cada IP. Para entregar esse pacote,
             o kernel PRECISA descobrir o MAC do destino, então ele mesmo dispara o
             ARP Request ("who-has"). Depois lemos a tabela ARP do kernel
             (/proc/net/arp): quem aparece com MAC respondeu ao ARP.
"""

import ctypes
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .plataforma import WINDOWS, ler_tabela_arp, normalizar_mac

# Windows: quantas perguntas ARP ao mesmo tempo (cada IP vazio demora ~3-4 s)
ARPS_EM_PARALELO = 128

# Linux: quantas rodadas de envio e quanto esperar entre elas (segundos)
RODADAS_LINUX = 3
ESPERA_ENTRE_RODADAS = 1.0
PORTA_UDP_DESCARTE = 9  # porta "discard": o conteúdo do pacote não importa


# ---------------------------------------------------------------------------
# Windows: SendARP
# ---------------------------------------------------------------------------
def consultar_mac_windows(ip):
    """Envia ARP via SendARP. Devolve o MAC (AA:BB:...) ou None se ninguém respondeu."""
    try:
        # O Windows espera o IP como um número de 32 bits na ordem da rede
        ip_destino = int.from_bytes(socket.inet_aton(ip), "little")
        buffer_mac = (ctypes.c_ubyte * 6)()   # espaço para os 6 bytes do MAC
        tamanho = ctypes.c_ulong(6)
        retorno = ctypes.windll.iphlpapi.SendARP(
            ip_destino, 0, ctypes.byref(buffer_mac), ctypes.byref(tamanho))
    except (OSError, AttributeError, ValueError):
        return None
    if retorno != 0 or tamanho.value == 0:  # 0 = NO_ERROR
        return None
    return normalizar_mac(":".join("%02X" % b for b in buffer_mac[:tamanho.value]))


def _sondar_windows(ips, ao_concluir, cancelado):
    ocupados = {}
    with ThreadPoolExecutor(max_workers=ARPS_EM_PARALELO) as executor:
        tarefas = {executor.submit(consultar_mac_windows, ip): ip for ip in ips}
        for tarefa in as_completed(tarefas):
            if cancelado is not None and cancelado.is_set():
                for t in tarefas:
                    t.cancel()
                break
            ip, mac = tarefas[tarefa], tarefa.result()
            if mac:
                ocupados[ip] = mac
            if ao_concluir:
                ao_concluir(ip, mac)
    return ocupados


# ---------------------------------------------------------------------------
# Linux: o kernel envia o ARP; nós lemos a tabela ARP
# ---------------------------------------------------------------------------
def _provocar_arp(ips):
    """Envia 1 pacote UDP para cada IP; o kernel dispara o ARP Request de cada um."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setblocking(False)
        for ip in ips:
            try:
                s.sendto(b"netprobe", (ip, PORTA_UDP_DESCARTE))
            except OSError:
                pass  # "host inacessível" de uma tentativa anterior: tudo bem


def _sondar_linux(ips, ao_concluir, cancelado):
    ocupados = {}
    pendentes = list(ips)
    for _ in range(RODADAS_LINUX):
        if not pendentes or (cancelado is not None and cancelado.is_set()):
            break
        _provocar_arp(pendentes)
        time.sleep(ESPERA_ENTRE_RODADAS)  # tempo para as respostas ARP chegarem
        tabela = ler_tabela_arp()
        ainda_pendentes = []
        for ip in pendentes:
            if ip in tabela:
                ocupados[ip] = tabela[ip]
                if ao_concluir:
                    ao_concluir(ip, tabela[ip])  # achou: avisa a tela na hora
            else:
                ainda_pendentes.append(ip)
        pendentes = ainda_pendentes
    if ao_concluir and not (cancelado is not None and cancelado.is_set()):
        for ip in pendentes:
            ao_concluir(ip, None)  # ninguém respondeu: IP vazio
    return ocupados


# ---------------------------------------------------------------------------
# Função usada pelo orquestrador (escolhe o jeito certo para o sistema)
# ---------------------------------------------------------------------------
def consultar_mac(ip):
    """MAC de um único IP (usado pela tabela IP<->MAC), ou None."""
    if WINDOWS:
        return consultar_mac_windows(ip)
    tabela = ler_tabela_arp()
    if ip not in tabela:
        _provocar_arp([ip])
        time.sleep(0.5)
        tabela = ler_tabela_arp()
    return tabela.get(ip)


def sondar(ips_sem_resposta, ao_concluir=None, cancelado=None):
    """
    Faz o ARP Probe nos IPs que não responderam ao ping.

    ao_concluir -> função chamada a cada IP: ao_concluir(ip, mac_ou_None)
    cancelado   -> threading.Event para interromper

    Retorna {ip: mac} só dos IPs que estavam ocupados (responderam ARP).
    """
    if WINDOWS:
        return _sondar_windows(ips_sem_resposta, ao_concluir, cancelado)
    return _sondar_linux(ips_sem_resposta, ao_concluir, cancelado)
