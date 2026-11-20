"""
monitorar.py — FERRAMENTA DE DIAGNÓSTICO (não faz parte da apresentação).

Fica varrendo a rede sem parar e anota, com horário, quando cada aparelho
APARECE ou SOME. Serve para responder perguntas como:
  - "Quanto tempo depois de conectar no hotspot o celular começa a responder?"
  - "Ele some sozinho? Por quantos segundos?"
  - "Quando some, ainda responde ARP (só dormiu) ou fica mudo de vez?"

Como usar (na pasta do projeto):
    Linux:   python3 scripts/monitorar.py                 (rede detectada sozinha)
             python3 scripts/monitorar.py 10.251.150.0/24
    Windows: python scripts\\monitorar.py
Para parar: Ctrl+C. Tudo que aparece na tela também vai para a pasta logs/.

Cada linha do log:
    17:33:02  10.251.150.13    APARECEU   ping 7 ms   (ficou 41 s fora)
    17:35:10  10.251.150.13    SUMIU      ARP: FAILED (mudo: nem ARP responde)
"""

import argparse
import datetime
import ipaddress
import os
import sys
import time

# permite importar o pacote "scanner" rodando a partir de qualquer pasta
PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PASTA_PROJETO)

from scanner import icmp_scan                                  # noqa: E402
from scanner.arp_probe import _meu_ip                          # noqa: E402
from scanner.plataforma import (LINUX, ler_tabela_arp, ler_vizinhos_linux,  # noqa: E402
                                rede_desta_maquina)

EXPLICACAO_ARP = {
    "REACHABLE": "respondeu ARP agora (ligado, mas sem ping: dormindo/bloqueando)",
    "STALE": "ARP antigo, sem confirmação recente",
    "DELAY": "kernel conferindo ARP",
    "PROBE": "kernel perguntando ARP",
    "INCOMPLETE": "kernel perguntando ARP, sem resposta ainda",
    "FAILED": "mudo: nem ARP responde",
}


def agora():
    return datetime.datetime.now().strftime("%H:%M:%S")


def estado_arp(ip):
    """Texto curto com o que a tabela ARP do sistema diz sobre o IP."""
    if LINUX:
        vizinhos = ler_vizinhos_linux() or {}
        v = vizinhos.get(ip)
        if not v:
            return "ARP: sem entrada"
        return "ARP: %s (%s)" % (v["estado"], EXPLICACAO_ARP.get(v["estado"], ""))
    mac = ler_tabela_arp().get(ip)
    return "ARP: " + (mac or "sem entrada")


def main():
    parser = argparse.ArgumentParser(description="Monitor contínuo de aparelhos (diagnóstico)")
    parser.add_argument("rede", nargs="?", help="ex: 10.251.150.0/24 (padrão: rede desta máquina)")
    parser.add_argument("--timeout", type=int, default=1000, help="timeout do ping em ms (padrão 1000)")
    parser.add_argument("--intervalo", type=float, default=2.0, help="pausa entre varreduras, em s")
    args = parser.parse_args()

    if args.rede:
        rede = ipaddress.ip_network(args.rede, strict=False)
    else:
        meu_ip = _meu_ip()
        if not meu_ip:
            sys.exit("Sem rede. Conecte no hotspot ou informe a rede, ex: 10.251.150.0/24")
        rede = ipaddress.ip_network(rede_desta_maquina(meu_ip))  # máscara real (iPhone = /28)
    ips = [str(ip) for ip in rede.hosts()]

    os.makedirs(os.path.join(PASTA_PROJETO, "logs"), exist_ok=True)
    nome = datetime.datetime.now().strftime("monitor-%Y%m%d-%H%M%S.log")
    caminho = os.path.join(PASTA_PROJETO, "logs", nome)
    arquivo = open(caminho, "a", encoding="utf-8")

    def registrar(texto):
        linha = "%s  %s" % (agora(), texto)
        print(linha, flush=True)
        arquivo.write(linha + "\n")
        arquivo.flush()

    registrar("Monitorando %s (timeout %d ms). Log em %s. Ctrl+C para parar."
              % (rede, args.timeout, caminho))

    online = {}        # ip -> horário (monotônico) em que apareceu
    sumiu_em = {}      # ip -> horário em que sumiu
    rodada = 0
    try:
        while True:
            rodada += 1
            respondidos = icmp_scan.varrer(ips, args.timeout)
            t = time.monotonic()
            for ip in sorted(respondidos, key=ipaddress.ip_address):
                if ip not in online:
                    fora = sumiu_em.pop(ip, None)
                    extra = "  (ficou %d s fora)" % (t - fora) if fora else ""
                    registrar("%-15s  APARECEU   ping %s ms%s"
                              % (ip, round(respondidos[ip]), extra))
                    online[ip] = t
            for ip in sorted(set(online) - set(respondidos), key=ipaddress.ip_address):
                registrar("%-15s  SUMIU      ficou %d s online | %s"
                          % (ip, t - online.pop(ip), estado_arp(ip)))
                sumiu_em[ip] = t
            if rodada % 10 == 0:
                registrar("--- rodada %d: %d online: %s" % (rodada, len(online),
                          ", ".join(sorted(online, key=ipaddress.ip_address))))
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        registrar("Encerrado. Online no fim: %s" % ", ".join(sorted(online, key=ipaddress.ip_address)))
    finally:
        arquivo.close()


if __name__ == "__main__":
    main()
