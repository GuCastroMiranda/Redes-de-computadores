#!/usr/bin/env bash
# ===================================================================
#  iniciar.sh - forma oficial de abrir o NetProbe Wi-Fi no LINUX.
#  No terminal, dentro da pasta do projeto:   ./iniciar.sh
#  (na primeira vez, se der "permissão negada":  chmod +x iniciar.sh)
#  Ele procura o Python (python3 ou python) e executa o run.py.
# ===================================================================
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
  python3 run.py "$@"
elif command -v python >/dev/null 2>&1; then
  python run.py "$@"
else
  echo "Python não encontrado. Instale com:  sudo apt install python3"
  exit 1
fi
