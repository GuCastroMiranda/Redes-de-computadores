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

Três formas de enviar o ARP, conforme o sistema:
  1. Linux com sudo (MODO DA APRESENTAÇÃO): montamos o pacote ARP byte a byte e
     enviamos direto na placa de rede (socket "raw"). É o método mais fiel: cada
     resposta é real, recebida agora.
  2. Linux sem sudo: enviamos um pacote UDP qualquer ao IP; para entregá-lo, o kernel
     PRECISA do MAC do destino e dispara ele mesmo o ARP. Depois lemos a tabela de
     vizinhos do kernel ("ip -s neigh") e só aceitamos quem confirmou AGORA.
  3. Windows: função nativa SendARP (biblioteca iphlpapi.dll) via ctypes.
"""

import ctypes
import socket
import struct
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .plataforma import (WINDOWS, eh_root, ler_tabela_arp, ler_vizinhos_linux,
                         mac_desta_maquina, normalizar_mac, placa_de_rede_linux)

# Windows: quantas perguntas ARP ao mesmo tempo (cada IP vazio demora ~3-4 s)
ARPS_EM_PARALELO = 128

# Linux com sudo: rodadas de envio e tempo total esperando respostas (segundos)
RODADAS_RAW = 2
ESPERA_RAW = 1.5

# Linux sem sudo: tempo máximo esperando o kernel resolver os ARPs (segundos)
ESPERA_MAXIMA_KERNEL = 9.0
PORTA_UDP_DESCARTE = 9  # porta "discard": o conteúdo do pacote não importa

ETHERTYPE_ARP = 0x0806


def _cancelou(cancelado):
    return cancelado is not None and cancelado.is_set()


# ===========================================================================
# 1. Linux com sudo: pacote ARP montado à mão (socket raw na camada 2)
# ===========================================================================
def montar_pacote_arp(meu_mac, meu_ip, ip_alvo):
    """
    Monta um quadro Ethernet com uma requisição ARP ("who-has ip_alvo?").

    Quadro Ethernet (14 bytes):
        MAC destino  = FF:FF:FF:FF:FF:FF  (broadcast: todos da rede recebem)
        MAC origem   = meu MAC
        Tipo         = 0x0806 (ARP)
    Pacote ARP (28 bytes):
        Tipo de hardware = 1 (Ethernet)    Tipo de protocolo = 0x0800 (IPv4)
        Tamanho MAC = 6                    Tamanho IP = 4
        Operação = 1 (requisição; a resposta vem com operação 2)
        MAC/IP do remetente = os meus
        MAC/IP do alvo      = 00:00:00:00:00:00 (desconhecido) / IP perguntado
    """
    mac = bytes.fromhex(meu_mac.replace(":", ""))
    ethernet = b"\xff" * 6 + mac + struct.pack("!H", ETHERTYPE_ARP)
    arp = struct.pack("!HHBBH", 1, 0x0800, 6, 4, 1)
    arp += mac + socket.inet_aton(meu_ip) + b"\x00" * 6 + socket.inet_aton(ip_alvo)
    return ethernet + arp


def ler_resposta_arp(quadro):
    """Se o quadro for uma RESPOSTA ARP, devolve (ip_de_quem_respondeu, mac). Senão None."""
    if len(quadro) < 42 or struct.unpack("!H", quadro[12:14])[0] != ETHERTYPE_ARP:
        return None
    operacao = struct.unpack("!H", quadro[20:22])[0]
    if operacao != 2:  # 2 = resposta
        return None
    mac = ":".join("%02X" % b for b in quadro[22:28])
    ip = socket.inet_ntoa(quadro[28:32])
    return ip, mac


def _sondar_linux_raw(ips, ao_concluir, cancelado):
    """Envia ARPs feitos à mão e escuta as respostas. Devolve None se não for possível."""
    meu_ip = _meu_ip()
    placa = placa_de_rede_linux(meu_ip) if meu_ip else None
    meu_mac = mac_desta_maquina(meu_ip) if placa else None
    if not (placa and meu_mac):
        return None
    try:
        s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETHERTYPE_ARP))
        s.bind((placa, 0))
    except (OSError, AttributeError):
        return None  # sem permissão: usa o método do kernel

    ocupados, pendentes = {}, set(ips)
    with s:
        s.settimeout(0.1)
        intervalo = ESPERA_RAW / RODADAS_RAW
        for _ in range(RODADAS_RAW):
            if not pendentes or _cancelou(cancelado):
                break
            for ip in sorted(pendentes):          # envia "who-has" para cada IP pendente
                try:
                    s.send(montar_pacote_arp(meu_mac, meu_ip, ip))
                except OSError:
                    pass
            limite = time.monotonic() + intervalo
            while time.monotonic() < limite:       # escuta as respostas
                try:
                    resposta = ler_resposta_arp(s.recv(2048))
                except socket.timeout:
                    continue
                except OSError:
                    break
                if resposta and resposta[0] in pendentes:
                    ip, mac = resposta
                    pendentes.discard(ip)
                    ocupados[ip] = normalizar_mac(mac)
                    if ao_concluir:
                        ao_concluir(ip, ocupados[ip])  # achou: avisa a tela na hora
    if ao_concluir and not _cancelou(cancelado):
        for ip in pendentes:
            ao_concluir(ip, None)  # ninguém respondeu: IP vazio
    return ocupados


# ===========================================================================
# 2. Linux sem sudo: o kernel envia o ARP; lemos a tabela de vizinhos
# ===========================================================================
def _provocar_arp(ips):
    """Envia 1 pacote UDP para cada IP; o kernel dispara o ARP Request de cada um."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setblocking(False)
        for ip in ips:
            try:
                s.sendto(b"netprobe", (ip, PORTA_UDP_DESCARTE))
            except OSError:
                pass  # "host inacessível" de uma tentativa anterior: tudo bem


def _sondar_linux_kernel(ips, ao_concluir, cancelado):
    """
    Regras para não ser enganado pelo cache do kernel:
      - ONLINE  se o vizinho tem MAC e foi confirmado DEPOIS que começamos
                (ou está REACHABLE = confirmado há poucos segundos);
      - continua esperando enquanto o kernel ainda está perguntando
        (estados INCOMPLETE, DELAY, PROBE), até ESPERA_MAXIMA_KERNEL;
      - o resto é OFFLINE.
    """
    inicio = time.monotonic()
    _provocar_arp(ips)
    ocupados, pendentes = {}, set(ips)
    while pendentes and not _cancelou(cancelado):
        time.sleep(0.5)
        vizinhos = ler_vizinhos_linux()
        if vizinhos is None:  # sem o comando "ip": lê /proc/net/arp
            vizinhos = {ip: {"mac": mac, "estado": "REACHABLE", "confirmado_ha": 0}
                        for ip, mac in ler_tabela_arp().items()}
        decorrido = time.monotonic() - inicio
        ainda_resolvendo = False
        for ip in sorted(pendentes):
            v = vizinhos.get(ip)
            if not v:
                continue
            recente = v["confirmado_ha"] is not None and v["confirmado_ha"] <= decorrido + 1
            if v["mac"] and (v["estado"] == "REACHABLE" or recente) and v["estado"] != "FAILED":
                pendentes.discard(ip)
                ocupados[ip] = v["mac"]
                if ao_concluir:
                    ao_concluir(ip, v["mac"])
            elif v["estado"] in ("INCOMPLETE", "DELAY", "PROBE"):
                ainda_resolvendo = True
        if decorrido >= ESPERA_MAXIMA_KERNEL or (not ainda_resolvendo and decorrido >= 1.5):
            break
    if ao_concluir and not _cancelou(cancelado):
        for ip in pendentes:
            ao_concluir(ip, None)
    return ocupados


# ===========================================================================
# 3. Windows: SendARP
# ===========================================================================
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
            if _cancelou(cancelado):
                for t in tarefas:
                    t.cancel()
                break
            ip, mac = tarefas[tarefa], tarefa.result()
            if mac:
                ocupados[ip] = mac
            if ao_concluir:
                ao_concluir(ip, mac)
    return ocupados


# ===========================================================================
# Funções usadas pelo resto do programa
# ===========================================================================
def _meu_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return None


def metodo_arp():
    """Texto curto dizendo qual método de ARP está em uso (aparece na tela)."""
    if WINDOWS:
        return "SendARP (Windows)"
    if eh_root():
        return "ARP montado à mão (raw socket)"
    return "ARP via kernel (sem sudo)"


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
    if eh_root():
        resultado = _sondar_linux_raw(ips_sem_resposta, ao_concluir, cancelado)
        if resultado is not None:
            return resultado
    return _sondar_linux_kernel(ips_sem_resposta, ao_concluir, cancelado)
