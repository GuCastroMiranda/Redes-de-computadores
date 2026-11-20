"""
port_scan.py — [ITEM 5] Descoberta de Portas Abertas.

Para cada host ONLINE, tentamos abrir uma conexão TCP em cada porta do range
[porta_inicial, porta_final] escolhido na tela.

Como funciona (TCP Connect Scan):
  O TCP abre conexão com o "aperto de mão em 3 vias" (3-way handshake):
      nós -> SYN        host -> SYN/ACK        nós -> ACK
  - Se o host responde SYN/ACK, a conexão abre: porta ABERTA (há um serviço ouvindo).
  - Se responde RST (recusado) ou não responde dentro do timeout: porta FECHADA/FILTRADA.

  Em Python, socket.connect_ex() faz exatamente isso e devolve 0 quando conectou.
  Logo depois fechamos a conexão (não enviamos nenhum dado).

Para ser rápido, testamos várias portas ao mesmo tempo (ThreadPoolExecutor).
"""

import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

CONEXOES_EM_PARALELO = 200

# Tempo máximo de espera por porta. Na rede local uma porta aberta responde em poucos ms;
# esperar mais só deixa lentas as portas "filtradas" (que nunca respondem).
# O enunciado pede timeout parametrizável no ping (item 1) e range nas portas (item 5),
# então usamos o timeout da tela, mas limitado a este teto.
TETO_TIMEOUT_PORTA_MS = 400

# Serviços conhecidos (portas "bem conhecidas"), só para exibir um nome amigável
SERVICOS_CONHECIDOS = {
    20: "FTP-dados", 21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    67: "DHCP", 80: "HTTP", 110: "POP3", 135: "MS-RPC", 139: "NetBIOS",
    143: "IMAP", 443: "HTTPS", 445: "SMB", 554: "RTSP", 993: "IMAPS", 995: "POP3S",
    1900: "UPnP", 3306: "MySQL", 3389: "RDP", 5000: "UPnP/HTTP", 5353: "mDNS",
    5432: "PostgreSQL", 7000: "AirPlay", 8000: "HTTP-alt (NetProbe)",
    8008: "HTTP-alt", 8080: "HTTP-proxy", 8443: "HTTPS-alt", 62078: "iPhone-sync",
}


def nome_servico(porta):
    return SERVICOS_CONHECIDOS.get(porta, "desconhecido")


def porta_aberta(ip, porta, timeout_ms):
    """Tenta conectar via TCP. True se a porta está aberta."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_ms / 1000)
            return s.connect_ex((ip, porta)) == 0
    except OSError:
        return False


def varrer_portas(ip, porta_inicial, porta_final, timeout_ms, cancelado=None):
    """
    Testa todas as portas do range em um host.
    Retorna lista ordenada: [{"porta": 80, "servico": "HTTP"}, ...]
    """
    abertas = []
    timeout_ms = min(timeout_ms, TETO_TIMEOUT_PORTA_MS)
    portas = range(porta_inicial, porta_final + 1)
    with ThreadPoolExecutor(max_workers=CONEXOES_EM_PARALELO) as executor:
        tarefas = {executor.submit(porta_aberta, ip, p, timeout_ms): p for p in portas}
        for tarefa in as_completed(tarefas):
            if cancelado is not None and cancelado.is_set():
                for t in tarefas:
                    t.cancel()
                break
            if tarefa.result():
                porta = tarefas[tarefa]
                abertas.append({"porta": porta, "servico": nome_servico(porta)})
    abertas.sort(key=lambda item: item["porta"])
    return abertas
