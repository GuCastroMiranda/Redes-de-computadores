"""
orchestrator.py — O "maestro" da varredura.

Executa as etapas em ordem e avisa a tela de cada novidade (em tempo real):

  Etapa 1  ICMP  (icmp_scan.py)  -> quem responde ao ping?
  Etapa 2  ARP   (arp_probe.py)  -> dos que NÃO responderam, quem está ocupado?
  Etapa 3  MAC   (mac_table.py)  -> tabela IP <-> MAC de todos os online
  Etapa 4  PORTAS(port_scan.py)  -> portas abertas de cada online

A função 'emitir(tipo, dados)' é recebida de fora (do server.py). Cada vez que algo
acontece, chamamos emitir(...), e o servidor repassa o evento para o navegador.
"""

import time

from . import arp_probe, icmp_scan, mac_table, port_scan
from .models import Host


def executar(config, emitir, cancelado):
    """
    config    -> ScanConfig validado
    emitir    -> função emitir(tipo, dados) que envia eventos para a tela
    cancelado -> threading.Event (botão "Cancelar")

    Retorna a lista final de hosts (dicionários).
    """
    inicio = time.time()
    ips = config.lista_ips()
    hosts = {ip: Host(ip) for ip in ips}

    def atualizar(host):
        emitir("host", host.para_dicionario())

    # ---------------- Etapa 1: Ping Sweep (ICMP) ----------------
    emitir("etapa", {"etapa": "icmp", "texto": "1/4 Varredura ICMP (ping) em %d IPs" % len(ips)})
    feitos = [0]

    def ao_responder_ping(ip, latencia):
        feitos[0] += 1
        if latencia is not None:
            h = hosts[ip]
            h.status, h.metodo, h.latencia_ms = "online", "ICMP", latencia
            atualizar(h)
        emitir("progresso", {"etapa": "icmp", "feitos": feitos[0], "total": len(ips)})

    respondidos = icmp_scan.varrer(ips, config.timeout_ms, ao_responder_ping, cancelado)
    if cancelado.is_set():
        return _finalizar(hosts, inicio, emitir, cancelado=True)

    # ---------------- Etapa 2: ARP Probe ----------------
    sem_resposta = [ip for ip in ips if ip not in respondidos]
    emitir("etapa", {"etapa": "arp",
                     "texto": "2/4 ARP Probe nos %d IPs que não responderam ao ping" % len(sem_resposta)})
    feitos[0] = 0

    def ao_concluir_arp(ip, mac):
        feitos[0] += 1
        h = hosts[ip]
        if mac:
            h.status, h.metodo, h.mac = "online", "ARP", mac
        atualizar(h)  # envia também os offline, para a tela mostrar o status
        emitir("progresso", {"etapa": "arp", "feitos": feitos[0], "total": len(sem_resposta)})

    ocupados = arp_probe.sondar(sem_resposta, ao_concluir_arp, cancelado)
    if cancelado.is_set():
        return _finalizar(hosts, inicio, emitir, cancelado=True)

    # ---------------- Etapa 3: Tabela IP <-> MAC ----------------
    online = [ip for ip in ips if hosts[ip].status == "online"]
    emitir("etapa", {"etapa": "mac", "texto": "3/4 Vinculando IP <-> MAC de %d hosts online" % len(online)})
    tabela = mac_table.montar_tabela(online, ocupados)
    for ip, mac in tabela.items():
        hosts[ip].mac = mac
        atualizar(hosts[ip])

    # ---------------- Etapa 4: Portas abertas ----------------
    emitir("etapa", {"etapa": "portas",
                     "texto": "4/4 Portas %d-%d em %d hosts online"
                              % (config.porta_inicial, config.porta_final, len(online))})
    for n, ip in enumerate(online, start=1):
        if cancelado.is_set():
            return _finalizar(hosts, inicio, emitir, cancelado=True)
        hosts[ip].portas = port_scan.varrer_portas(
            ip, config.porta_inicial, config.porta_final, config.timeout_ms, cancelado)
        atualizar(hosts[ip])
        emitir("progresso", {"etapa": "portas", "feitos": n, "total": len(online)})

    return _finalizar(hosts, inicio, emitir, cancelado=cancelado.is_set())


def _finalizar(hosts, inicio, emitir, cancelado):
    """Monta o resumo final e avisa a tela."""
    lista = [h.para_dicionario() for h in hosts.values()]
    resumo = {
        "total": len(lista),
        "online": sum(1 for h in lista if h["status"] == "online"),
        "via_icmp": sum(1 for h in lista if h["metodo"] == "ICMP"),
        "via_arp": sum(1 for h in lista if h["metodo"] == "ARP"),
        "duracao_s": round(time.time() - inicio, 1),
        "cancelado": cancelado,
    }
    resumo["offline"] = resumo["total"] - resumo["online"]
    emitir("fim", resumo)
    return lista, resumo
