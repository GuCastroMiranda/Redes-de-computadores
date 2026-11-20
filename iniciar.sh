#!/usr/bin/env bash
# ===================================================================
#  iniciar.sh - forma oficial de abrir o NetProbe Wi-Fi no LINUX.
#  No terminal, dentro da pasta do projeto:   ./iniciar.sh
#  (na primeira vez, se der "permissão negada":  chmod +x iniciar.sh)
#
#  Ele pede a senha do sudo: com sudo, o ARP Probe (item 2) monta e envia
#  o pacote ARP direto na placa de rede, que é o modo mais preciso.
#  Plano B, sem sudo:   ./iniciar.sh --sem-sudo
# ===================================================================
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python não encontrado. Instale com:  sudo apt install python3"
  exit 1
fi

if [ "$1" = "--sem-sudo" ] || [ "$(id -u)" = "0" ] || ! command -v sudo >/dev/null 2>&1; then
  [ "$1" = "--sem-sudo" ] && shift
  exec "$PY" run.py "$@"
fi

echo "Pedindo a senha do sudo para enviar ARP direto na placa de rede (modo completo)."

# Abre o navegador (como usuário normal) assim que o servidor responder (até 2 min)
(
  for _ in $(seq 1 120); do
    for porta in 8000 8001 8002; do
      if (exec 3<>"/dev/tcp/127.0.0.1/$porta") 2>/dev/null; then
        xdg-open "http://127.0.0.1:$porta" >/dev/null 2>&1
        exit 0
      fi
    done
    sleep 1
  done
) &

exec sudo "$(command -v "$PY")" run.py "$@"
