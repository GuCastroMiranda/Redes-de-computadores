"""
historico.py — Base de dados local (SQLite) com o histórico das varreduras.

SQLite é um banco de dados que fica num único arquivo (netprobe.db) e já vem
embutido no Python: não precisa instalar nem ligar nenhum servidor de banco.

Tabela 'varreduras': uma linha por varredura (data, parâmetros, resumo e hosts em JSON).
"""

import json
import os
import sqlite3
import threading
from datetime import datetime

ARQUIVO_BANCO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "netprobe.db")
_trava = threading.Lock()  # evita duas gravações ao mesmo tempo


def _conectar():
    conexao = sqlite3.connect(ARQUIVO_BANCO, timeout=5)
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS varreduras (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora   TEXT NOT NULL,
            rede        TEXT NOT NULL,
            timeout_ms  INTEGER NOT NULL,
            portas      TEXT NOT NULL,
            resumo_json TEXT NOT NULL,
            hosts_json  TEXT NOT NULL
        )
    """)
    return conexao


def salvar(config, resumo, hosts):
    """Grava uma varredura concluída. Retorna o id gerado."""
    with _trava:
        conexao = _conectar()
        try:
            cursor = conexao.execute(
                "INSERT INTO varreduras (data_hora, rede, timeout_ms, portas, resumo_json, hosts_json)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                 str(config.rede),
                 config.timeout_ms,
                 "%d-%d" % (config.porta_inicial, config.porta_final),
                 json.dumps(resumo),
                 json.dumps(hosts)))
            conexao.commit()
            return cursor.lastrowid
        finally:
            conexao.close()


def listar(limite=15):
    """Últimas varreduras (sem a lista de hosts, só o resumo)."""
    with _trava:
        conexao = _conectar()
        try:
            linhas = conexao.execute(
                "SELECT id, data_hora, rede, timeout_ms, portas, resumo_json"
                " FROM varreduras ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
        finally:
            conexao.close()
    return [{"id": l[0], "data_hora": l[1], "rede": l[2], "timeout_ms": l[3],
             "portas": l[4], "resumo": json.loads(l[5])} for l in linhas]


def obter(id_varredura):
    """Uma varredura completa (com hosts), ou None se não existir."""
    with _trava:
        conexao = _conectar()
        try:
            l = conexao.execute(
                "SELECT id, data_hora, rede, timeout_ms, portas, resumo_json, hosts_json"
                " FROM varreduras WHERE id = ?", (id_varredura,)).fetchone()
        finally:
            conexao.close()
    if not l:
        return None
    return {"id": l[0], "data_hora": l[1], "rede": l[2], "timeout_ms": l[3],
            "portas": l[4], "resumo": json.loads(l[5]), "hosts": json.loads(l[6])}
