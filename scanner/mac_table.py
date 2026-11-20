"""
mac_table.py — [ITEM 3] Vinculação IP <-> MAC.

IP  = endereço LÓGICO (camada 3, rede). Pode mudar (o DHCP entrega outro amanhã).
MAC = endereço FÍSICO (camada 2, enlace). Vem gravado na placa de rede, 6 bytes,
      ex: 34:5A:60:AF:68:2E. Os 3 primeiros bytes (OUI) identificam o fabricante.

O protocolo ARP é justamente quem faz essa ponte: "qual MAC tem este IP?".

Aqui montamos a tabela final IP <-> MAC de TODOS os hosts online:
  - Quem foi achado pelo ARP Probe (item 2) já veio com o MAC.
  - Quem respondeu ao ping (item 1) ainda não tem MAC: perguntamos via ARP agora.
    (Como acabaram de responder, o MAC normalmente já está no cache ARP do Windows,
    então a resposta é instantânea.)
"""

from concurrent.futures import ThreadPoolExecutor

from .arp_probe import consultar_mac


def normalizar_mac(mac):
    """Padroniza para AA:BB:CC:DD:EE:FF (aceita '-' ou ':' e minúsculas)."""
    if not mac:
        return None
    limpo = mac.replace("-", "").replace(":", "").upper()
    if len(limpo) != 12:
        return None
    return ":".join(limpo[i:i + 2] for i in range(0, 12, 2))


def montar_tabela(hosts_online, macs_ja_conhecidos):
    """
    hosts_online       -> lista de IPs online (por ICMP ou ARP)
    macs_ja_conhecidos -> {ip: mac} vindos do ARP Probe

    Retorna a tabela {ip: mac} (mac = None se não foi possível descobrir,
    o que acontece, por exemplo, com IPs fora da rede local).
    """
    tabela = {}
    faltando = []
    for ip in hosts_online:
        if ip in macs_ja_conhecidos:
            tabela[ip] = normalizar_mac(macs_ja_conhecidos[ip])
        else:
            faltando.append(ip)

    # Busca em paralelo o MAC de quem só respondeu ao ping
    if faltando:
        with ThreadPoolExecutor(max_workers=32) as executor:
            for ip, mac in zip(faltando, executor.map(consultar_mac, faltando)):
                tabela[ip] = normalizar_mac(mac)
    return tabela
