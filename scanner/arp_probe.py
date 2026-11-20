"""
arp_probe.py — [ITEM 2] Mecanismo de Colisão / ARP Probe.

Problema: muitos dispositivos (ex: Windows com firewall ligado) BLOQUEIAM o ping (ICMP).
Para o Ping Sweep eles parecem "offline", mas estão ligados na rede.

Solução: para cada IP que NÃO respondeu ao ping, mandamos uma pergunta ARP:
    "Quem tem o IP 192.168.0.X? Me diga seu MAC."
O ARP é da CAMADA 2 (enlace). Um dispositivo precisa responder ARP para conseguir
usar a rede local, então o firewall normalmente NÃO bloqueia isso.

  - Se alguém respondeu ao ARP -> o IP está OCUPADO (online, só bloqueia ICMP).
  - Se ninguém respondeu       -> o IP está realmente VAZIO (offline).

Isso é o mesmo princípio do "ARP Probe" (RFC 5227), usado para detectar
colisão/conflito de IP antes de um dispositivo assumir um endereço.

Como fazemos no Windows: chamamos a função nativa SendARP, da biblioteca
iphlpapi.dll do próprio Windows, via ctypes (não precisa instalar nada nem ser admin).
"""

import ctypes
import socket
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Quantas perguntas ARP ao mesmo tempo (cada IP vazio demora ~3-4 s para desistir)
ARPS_EM_PARALELO = 128

# Código de retorno do Windows quando deu certo
_NO_ERROR = 0


def consultar_mac(ip):
    """
    Envia uma requisição ARP para o IP e devolve o MAC no formato AA:BB:CC:DD:EE:FF,
    ou None se ninguém respondeu.
    """
    if sys.platform != "win32":
        return None  # SendARP só existe no Windows

    try:
        # O Windows espera o IP como um número de 32 bits na ordem da rede
        ip_destino = int.from_bytes(socket.inet_aton(ip), "little")
        buffer_mac = (ctypes.c_ubyte * 6)()   # espaço para os 6 bytes do MAC
        tamanho = ctypes.c_ulong(6)
        retorno = ctypes.windll.iphlpapi.SendARP(
            ip_destino, 0, ctypes.byref(buffer_mac), ctypes.byref(tamanho))
    except (OSError, AttributeError, ValueError):
        return None

    if retorno != _NO_ERROR or tamanho.value == 0:
        return None

    mac = ":".join("%02X" % byte for byte in buffer_mac[:tamanho.value])
    if mac == "00:00:00:00:00:00":
        return None
    return mac


def sondar(ips_sem_resposta, ao_concluir=None, cancelado=None):
    """
    Faz o ARP Probe em paralelo nos IPs que não responderam ao ping.

    ao_concluir -> função chamada a cada IP: ao_concluir(ip, mac_ou_None)
    cancelado   -> threading.Event para interromper

    Retorna {ip: mac} só dos IPs que estavam ocupados (responderam ARP).
    """
    ocupados = {}
    with ThreadPoolExecutor(max_workers=ARPS_EM_PARALELO) as executor:
        tarefas = {executor.submit(consultar_mac, ip): ip for ip in ips_sem_resposta}
        for tarefa in as_completed(tarefas):
            if cancelado is not None and cancelado.is_set():
                for t in tarefas:
                    t.cancel()
                break
            ip = tarefas[tarefa]
            mac = tarefa.result()
            if mac:
                ocupados[ip] = mac
            if ao_concluir:
                ao_concluir(ip, mac)
    return ocupados
