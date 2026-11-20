"""
icmp_scan.py — [ITEM 1] Varredura ICMP (Ping Sweep).

O que é: enviamos um "ICMP Echo Request" (o famoso ping) para cada IP da faixa /24.
Quem responde com "ICMP Echo Reply" está ONLINE.

Como fazemos:
  - Usamos o comando 'ping' do próprio Windows: ping -n 1 -w <timeout> <ip>
      -n 1  -> envia só 1 pacote
      -w    -> tempo máximo de espera pela resposta, em milissegundos (parametrizável)
  - Para ser ágil, pingamos vários IPs ao mesmo tempo (ThreadPoolExecutor = várias
    "linhas de execução" em paralelo). Assim 254 IPs levam poucos segundos, e não minutos.

Detalhe importante (pegadinha do Windows):
  O ping do Windows pode retornar "sucesso" quando o roteador responde
  "Host de destino inacessível". Por isso só consideramos ONLINE quando a resposta
  contém "TTL=", que só aparece num Echo Reply verdadeiro.
"""

import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Quantos pings ao mesmo tempo
PINGS_EM_PARALELO = 64

# No Windows, evita abrir uma janelinha preta para cada ping
_SEM_JANELA = 0x08000000 if sys.platform == "win32" else 0

# Captura o tempo de resposta: "tempo=12ms", "time=12ms" ou "tempo<1ms"
_REGEX_LATENCIA = re.compile(r"[=<]\s*(\d+)\s*ms", re.IGNORECASE)


def pingar(ip, timeout_ms):
    """
    Envia 1 ping para o IP.
    Retorna a latência em ms (int) se respondeu, ou None se não respondeu.
    """
    if sys.platform == "win32":
        comando = ["ping", "-n", "1", "-w", str(timeout_ms), ip]
    else:  # Linux/macOS (só por compatibilidade; a apresentação é no Windows)
        comando = ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000)), ip]

    try:
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout_ms / 1000 + 3,  # trava de segurança extra
            creationflags=_SEM_JANELA,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    saida = resultado.stdout
    if "TTL=" not in saida.upper():
        return None  # não houve Echo Reply verdadeiro

    for linha in saida.splitlines():
        if "TTL=" in linha.upper():
            achou = _REGEX_LATENCIA.search(linha)
            return int(achou.group(1)) if achou else 0
    return 0


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
