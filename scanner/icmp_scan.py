"""
icmp_scan.py — [ITEM 1] Varredura ICMP (Ping Sweep).

O que é: enviamos um "ICMP Echo Request" (o famoso ping) para cada IP da faixa /24.
Quem responde com "ICMP Echo Reply" está ONLINE.

Como fazemos:
  - Usamos o comando 'ping' do próprio sistema operacional, enviando só 1 pacote:
        Windows:  ping -n 1 -w <timeout em ms>      <ip>
        Linux:    ping -c 1 -W <timeout em segundos> <ip>
    O timeout é o tempo máximo de espera pela resposta (parametrizável na tela).
  - Para ser ágil, pingamos vários IPs ao mesmo tempo (ThreadPoolExecutor = várias
    "linhas de execução" em paralelo). Assim 254 IPs levam poucos segundos, e não minutos.

Detalhe importante (pegadinha do Windows):
  O ping do Windows pode retornar "sucesso" quando o roteador responde
  "Host de destino inacessível". Por isso só consideramos ONLINE quando a resposta
  contém "TTL=", que só aparece num Echo Reply verdadeiro (vale para os dois sistemas).
"""

import math
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from .plataforma import AMBIENTE_C, LINUX, MACOS, SEM_JANELA, WINDOWS

# Quantos pings ao mesmo tempo
PINGS_EM_PARALELO = 64

# Captura o tempo de resposta em qualquer formato:
#   Windows: "tempo=12ms", "time<1ms"      Linux: "time=3.45 ms"
_REGEX_LATENCIA = re.compile(r"(?:time|tempo)\s*([=<])\s*([\d.,]+)\s*ms", re.IGNORECASE)

# No Linux, versões antigas do ping não aceitam timeout fracionado (ex: -W 0.3).
# Testamos uma vez e guardamos o resultado.
_linux_aceita_fracao = None


def _linux_timeout_fracionado():
    global _linux_aceita_fracao
    if _linux_aceita_fracao is None:
        try:
            teste = subprocess.run(["ping", "-c", "1", "-W", "0.5", "127.0.0.1"],
                                   capture_output=True, timeout=5, env=AMBIENTE_C)
            _linux_aceita_fracao = teste.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            _linux_aceita_fracao = False
    return _linux_aceita_fracao


def montar_comando(ip, timeout_ms):
    """Monta o comando ping certo para o sistema operacional."""
    if WINDOWS:
        return ["ping", "-n", "1", "-w", str(timeout_ms), ip]
    if MACOS:
        return ["ping", "-c", "1", "-W", str(timeout_ms), ip]  # macOS: -W em ms
    # Linux: -W em segundos
    if _linux_timeout_fracionado():
        segundos = "%.3f" % (timeout_ms / 1000)
    else:
        segundos = str(max(1, math.ceil(timeout_ms / 1000)))
    return ["ping", "-c", "1", "-W", segundos, ip]


def pingar(ip, timeout_ms):
    """
    Envia 1 ping para o IP.
    Retorna a latência em ms (int) se respondeu, ou None se não respondeu.
    """
    try:
        resultado = subprocess.run(
            montar_comando(ip, timeout_ms),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout_ms / 1000 + 3,  # trava de segurança extra
            creationflags=SEM_JANELA,
            env=AMBIENTE_C if LINUX or MACOS else None,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    for linha in resultado.stdout.splitlines():
        if "TTL=" in linha.upper():  # Echo Reply verdadeiro
            achou = _REGEX_LATENCIA.search(linha)
            if not achou or achou.group(1) == "<":
                return 0  # "tempo<1ms": menos de 1 ms (a tela mostra "< 1 ms")
            return max(0, round(float(achou.group(2).replace(",", "."))))
    return None  # não houve Echo Reply


def varrer(ips, timeout_ms, ao_responder=None, cancelado=None):
    """
    Pinga todos os IPs em paralelo.

    ips          -> lista de IPs (texto)
    timeout_ms   -> timeout de cada ping
    ao_responder -> função chamada a cada IP concluído: ao_responder(ip, latencia_ou_None)
                    (é assim que a tela é atualizada em tempo real)
    cancelado    -> threading.Event; se for "setado", paramos de enviar novos pings

    Retorna um dicionário {ip: latencia_ms} só com quem respondeu.
    """
    if LINUX:
        _linux_timeout_fracionado()  # faz o teste uma vez, antes das threads
    respondidos = {}
    with ThreadPoolExecutor(max_workers=PINGS_EM_PARALELO) as executor:
        tarefas = {executor.submit(pingar, ip, timeout_ms): ip for ip in ips}
        for tarefa in as_completed(tarefas):
            if cancelado is not None and cancelado.is_set():
                for t in tarefas:
                    t.cancel()
                break
            ip = tarefas[tarefa]
            latencia = tarefa.result()
            if latencia is not None:
                respondidos[ip] = latencia
            if ao_responder:
                ao_responder(ip, latencia)
    return respondidos
