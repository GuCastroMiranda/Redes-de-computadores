"""
models.py — Estruturas de dados e validação dos parâmetros da varredura.

Aqui ficam:
  - Host: um dispositivo da rede (IP, MAC, status, como foi descoberto, portas).
  - ScanConfig: os parâmetros escolhidos na tela (rede, timeout, portas).
  - ScanConfig.de_dicionario(): valida TUDO que vem da tela antes de começar.
    Se algo estiver errado, levanta ErroValidacao com uma mensagem em português,
    e a varredura nem começa (assim a aplicação nunca quebra por input ruim).
"""

import ipaddress


class ErroValidacao(Exception):
    """Erro de parâmetro inválido digitado pelo usuário."""


# Limites de segurança (evitam varreduras que demorariam demais na apresentação)
TIMEOUT_MIN_MS = 50
TIMEOUT_MAX_MS = 5000
MAX_PORTAS_POR_VARREDURA = 2000


class Host:
    """Um dispositivo (ou endereço) da rede analisada."""

    def __init__(self, ip):
        self.ip = ip                # Endereço lógico (camada 3), ex: 192.168.0.10
        self.mac = None             # Endereço físico (camada 2), ex: AA:BB:CC:DD:EE:FF
        self.status = "offline"     # "online" ou "offline"
        self.metodo = None          # "ICMP" (respondeu ping) ou "ARP" (só respondeu ARP)
        self.latencia_ms = None     # Tempo de resposta do ping
        self.portas = []            # Lista de portas abertas: [{"porta": 80, "servico": "HTTP"}]

    def para_dicionario(self):
        """Converte para dicionário (para enviar à tela em JSON)."""
        return {
            "ip": self.ip,
            "mac": self.mac,
            "status": self.status,
            "metodo": self.metodo,
            "latencia_ms": self.latencia_ms,
            "portas": self.portas,
        }


class ScanConfig:
    """Parâmetros de uma varredura, já validados."""

    def __init__(self, rede, timeout_ms, porta_inicial, porta_final):
        self.rede = rede                    # objeto ipaddress.IPv4Network
        self.timeout_ms = timeout_ms        # timeout de cada ping/conexão, em milissegundos
        self.porta_inicial = porta_inicial  # início do range de portas
        self.porta_final = porta_final      # fim do range de portas

    def lista_ips(self):
        """Todos os IPs 'usáveis' da rede (sem o endereço de rede e o de broadcast)."""
        return [str(ip) for ip in self.rede.hosts()]

    @staticmethod
    def de_dicionario(dados):
        """Lê e valida os parâmetros vindos da tela. Levanta ErroValidacao se algo estiver errado."""
        if not isinstance(dados, dict):
            raise ErroValidacao("Parâmetros ausentes.")

        # --- Rede (CIDR) ---
        texto_rede = str(dados.get("rede", "")).strip()
        if not texto_rede:
            raise ErroValidacao("Informe a rede, por exemplo 192.168.0.0/24.")
        if "/" not in texto_rede:
            texto_rede += "/24"  # se digitarem só o IP, assumimos /24
        try:
            # strict=False aceita "192.168.0.15/24" e transforma em "192.168.0.0/24"
            rede = ipaddress.IPv4Network(texto_rede, strict=False)
        except ValueError:
            raise ErroValidacao("Rede inválida: use o formato 192.168.0.0/24.")
        if rede.prefixlen < 24:
            raise ErroValidacao("Rede grande demais: use máscara /24 ou menor (até 254 hosts).")
        if rede.prefixlen > 30:
            raise ErroValidacao("Rede pequena demais: use máscara entre /24 e /30.")

        # --- Timeout ---
        timeout_ms = _inteiro(dados.get("timeout_ms"), "Timeout")
        if not (TIMEOUT_MIN_MS <= timeout_ms <= TIMEOUT_MAX_MS):
            raise ErroValidacao(
                "Timeout deve ficar entre %d e %d ms." % (TIMEOUT_MIN_MS, TIMEOUT_MAX_MS))

        # --- Portas ---
        porta_inicial = _inteiro(dados.get("porta_inicial"), "Porta inicial")
        porta_final = _inteiro(dados.get("porta_final"), "Porta final")
        for nome, porta in (("Porta inicial", porta_inicial), ("Porta final", porta_final)):
            if not (1 <= porta <= 65535):
                raise ErroValidacao("%s deve ficar entre 1 e 65535." % nome)
        if porta_inicial > porta_final:
            raise ErroValidacao("A porta inicial não pode ser maior que a porta final.")
        if porta_final - porta_inicial + 1 > MAX_PORTAS_POR_VARREDURA:
            raise ErroValidacao(
                "Range de portas grande demais: no máximo %d portas por varredura."
                % MAX_PORTAS_POR_VARREDURA)

        return ScanConfig(rede, timeout_ms, porta_inicial, porta_final)


def _inteiro(valor, nome):
    """Converte para inteiro ou levanta ErroValidacao com mensagem amigável."""
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        raise ErroValidacao("%s deve ser um número inteiro." % nome)
