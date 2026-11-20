"""
server.py — Servidor web do NetProbe (parte do [ITEM 4] Interface em tempo real).

Usa só o que já vem no Python (http.server), sem instalar nada.

Rotas:
  GET  /                    -> a página (web/index.html, style.css, app.js)
  GET  /api/info            -> IP desta máquina e rede sugerida
  POST /api/varrer          -> inicia uma varredura (parâmetros em JSON)
  POST /api/cancelar        -> cancela a varredura em andamento
  GET  /api/eventos         -> TEMPO REAL: Server-Sent Events (SSE)
  GET  /api/historico       -> últimas varreduras salvas no SQLite
  GET  /api/historico/<id>  -> uma varredura salva, completa

Tempo real com SSE: o navegador abre UMA conexão em /api/eventos e o servidor
vai "empurrando" eventos (host encontrado, progresso, fim) conforme acontecem.
"""

import json
import os
import socket
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import historico
from scanner import orchestrator
from scanner.arp_probe import metodo_arp
from scanner.models import ErroValidacao, ScanConfig
from scanner.plataforma import nome_sistema

PASTA_WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
TIPOS = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".js": "application/javascript; charset=utf-8"}


# ---------------------------------------------------------------------------
# Estado da varredura atual (compartilhado entre as threads do servidor)
# ---------------------------------------------------------------------------
class EstadoVarredura:
    def __init__(self):
        self.condicao = threading.Condition()
        self.numero = 0          # muda a cada nova varredura
        self.eventos = []        # todos os eventos da varredura atual
        self.rodando = False
        self.cancelado = threading.Event()

    def emitir(self, tipo, dados):
        """Guarda o evento e acorda todas as conexões SSE esperando novidade."""
        with self.condicao:
            if tipo == "fim":
                # libera um novo "Iniciar" no mesmo instante em que a tela recebe o fim
                self.rodando = False
            self.eventos.append({"tipo": tipo, "dados": dados})
            self.condicao.notify_all()

    def iniciar(self, config):
        """Começa uma varredura numa thread separada. Retorna False se já houver uma rodando."""
        with self.condicao:
            if self.rodando:
                return False  # trava contra clique duplo / scans simultâneos
            self.rodando = True
            self.numero += 1
            self.eventos = []
            self.cancelado = threading.Event()
            self.condicao.notify_all()
        threading.Thread(target=self._rodar, args=(config,), daemon=True).start()
        return True

    def _rodar(self, config):
        meu_numero = self.numero
        self.emitir("inicio", {"rede": str(config.rede), "timeout_ms": config.timeout_ms,
                               "porta_inicial": config.porta_inicial,
                               "porta_final": config.porta_final})
        try:
            hosts, resumo = orchestrator.executar(config, self.emitir, self.cancelado)
            if not resumo["cancelado"]:
                historico.salvar(config, resumo, hosts)
                self.emitir("salvo", {})
        except Exception as erro:  # nunca deixa a aplicação cair
            traceback.print_exc()
            self.emitir("erro", {"mensagem": "Falha inesperada: %s" % erro})
        finally:
            with self.condicao:
                if self.numero == meu_numero:  # não mexe numa varredura mais nova
                    self.rodando = False
                self.condicao.notify_all()


ESTADO = EstadoVarredura()


def ip_local():
    """Descobre o IP desta máquina na rede (sem enviar nenhum pacote de fato)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


# ---------------------------------------------------------------------------
# Tratamento das requisições HTTP
# ---------------------------------------------------------------------------
class Manipulador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, formato, *args):
        pass  # silencia o log padrão para não poluir o terminal na apresentação

    # ---------- utilitários ----------
    def _responder_json(self, status, dados):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _ler_json(self):
        tamanho = int(self.headers.get("Content-Length") or 0)
        if tamanho <= 0 or tamanho > 10000:
            return {}
        try:
            return json.loads(self.rfile.read(tamanho).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    # ---------- GET ----------
    def do_GET(self):
        caminho = self.path.split("?")[0]
        try:
            if caminho == "/api/info":
                ip = ip_local()
                self._responder_json(200, {"ip": ip, "rede_sugerida": ip.rsplit(".", 1)[0] + ".0/24",
                                           "sistema": nome_sistema(), "arp": metodo_arp(),
                                           "rodando": ESTADO.rodando})
            elif caminho == "/api/eventos":
                self._transmitir_eventos()
            elif caminho == "/api/historico":
                self._responder_json(200, historico.listar())
            elif caminho.startswith("/api/historico/"):
                try:
                    item = historico.obter(int(caminho.rsplit("/", 1)[1]))
                except ValueError:
                    item = None
                if item:
                    self._responder_json(200, item)
                else:
                    self._responder_json(404, {"erro": "Varredura não encontrada."})
            else:
                self._arquivo_estatico(caminho)
        except (ConnectionError, BrokenPipeError):
            pass  # o navegador fechou a conexão; tudo bem

    def _arquivo_estatico(self, caminho):
        nome = "index.html" if caminho in ("/", "") else caminho.lstrip("/")
        arquivo = os.path.normpath(os.path.join(PASTA_WEB, nome))
        # segurança: não deixa sair da pasta web/
        if not arquivo.startswith(PASTA_WEB) or not os.path.isfile(arquivo):
            self._responder_json(404, {"erro": "Não encontrado."})
            return
        with open(arquivo, "rb") as f:
            corpo = f.read()
        self.send_response(200)
        self.send_header("Content-Type", TIPOS.get(os.path.splitext(arquivo)[1], "application/octet-stream"))
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _transmitir_eventos(self):
        """SSE: mantém a conexão aberta e envia cada evento novo assim que ele acontece."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        numero_visto, enviados = None, 0
        while True:
            with ESTADO.condicao:
                # espera até ter novidade (ou 15 s, para mandar um "sinal de vida")
                ESTADO.condicao.wait_for(
                    lambda: ESTADO.numero != numero_visto or len(ESTADO.eventos) > enviados,
                    timeout=15)
                if ESTADO.numero != numero_visto:  # começou outra varredura
                    numero_visto, enviados = ESTADO.numero, 0
                novos = ESTADO.eventos[enviados:]
                enviados += len(novos)
            if novos:
                pacote = "".join("data: %s\n\n" % json.dumps(e, ensure_ascii=False) for e in novos)
            else:
                pacote = ": ping\n\n"  # comentário SSE só para manter a conexão viva
            self.wfile.write(pacote.encode("utf-8"))
            self.wfile.flush()

    # ---------- POST ----------
    def do_POST(self):
        caminho = self.path.split("?")[0]
        try:
            if caminho == "/api/varrer":
                try:
                    config = ScanConfig.de_dicionario(self._ler_json())
                except ErroValidacao as erro:
                    self._responder_json(400, {"erro": str(erro)})
                    return
                if ESTADO.iniciar(config):
                    self._responder_json(200, {"ok": True})
                else:
                    self._responder_json(409, {"erro": "Já existe uma varredura em andamento."})
            elif caminho == "/api/cancelar":
                ESTADO.cancelado.set()
                self._responder_json(200, {"ok": True})
            else:
                self._responder_json(404, {"erro": "Rota não encontrada."})
        except (ConnectionError, BrokenPipeError):
            pass


def criar_servidor(porta):
    servidor = ThreadingHTTPServer(("127.0.0.1", porta), Manipulador)
    servidor.daemon_threads = True
    return servidor
