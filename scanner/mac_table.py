"""
mac_table.py — [ITEM 3] Vinculação IP <-> MAC.

IP  = endereço LÓGICO (camada 3, rede). Pode mudar (o DHCP entrega outro amanhã).
MAC = endereço FÍSICO (camada 2, enlace). Vem gravado na placa de rede, 6 bytes,
      ex: 34:5A:60:AF:68:2E. Os 3 primeiros bytes (OUI) identificam o fabricante.

O protocolo ARP é justamente quem faz essa ponte: "qual MAC tem este IP?".

Aqui montamos a tabela final IP <-> MAC de TODOS os hosts online:
  - Quem foi achado pelo ARP Probe (item 2) já veio com o MAC.
  - Quem respondeu ao ping (item 1): como acabou de trocar pacotes conosco, o MAC já
    está no cache ARP do sistema. Lemos esse cache (Linux: /proc/net/arp,
    Windows: SendARP) e, se faltar alguém, perguntamos via ARP.
  - A própria máquina não aparece no cache ARP (ninguém pergunta o próprio MAC),
    então lemos o MAC direto da placa de rede.
"""

import socket
from concurrent.futures import ThreadPoolExecutor

from .arp_probe import consultar_mac
from .plataforma import WINDOWS, ler_tabela_arp, mac_desta_maquina, normalizar_mac


def ip_desta_maquina():
    """IP desta máquina na rede (não envia nenhum pacote de fato)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return None


def montar_tabela(hosts_online, macs_ja_conhecidos):
    """
    hosts_online       -> lista de IPs online (por ICMP ou ARP)
    macs_ja_conhecidos -> {ip: mac} vindos do ARP Probe

    Retorna a tabela {ip: mac} (mac = None se não foi possível descobrir).
    """
    meu_ip = ip_desta_maquina()
    cache_arp = ler_tabela_arp()  # o que o sistema já sabe
    tabela, faltando = {}, []

    for ip in hosts_online:
        if ip in macs_ja_conhecidos:
            tabela[ip] = normalizar_mac(macs_ja_conhecidos[ip])
        elif ip == meu_ip:
            # Windows: SendARP responde até para o próprio IP; Linux: lê da placa
            tabela[ip] = consultar_mac(ip) if WINDOWS else mac_desta_maquina(ip)
        elif ip in cache_arp:
            tabela[ip] = cache_arp[ip]
        else:
            faltando.append(ip)

    # Pergunta via ARP o MAC de quem ainda falta (em paralelo)
    if faltando:
        with ThreadPoolExecutor(max_workers=32) as executor:
            for ip, mac in zip(faltando, executor.map(consultar_mac, faltando)):
                tabela[ip] = normalizar_mac(mac)
    return tabela
