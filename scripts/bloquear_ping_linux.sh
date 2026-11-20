#!/usr/bin/env bash
# Demonstração do ITEM 2 (ARP Probe) — rodar no notebook Linux de um COLEGA (não no que varre).
#   ./scripts/bloquear_ping_linux.sh on    -> passa a IGNORAR ping (ICMP Echo Request)
#   ./scripts/bloquear_ping_linux.sh off   -> volta a responder ping
# Com o ping bloqueado, o NetProbe não acha esse notebook pelo ICMP, mas acha pelo ARP.
case "$1" in
  on)  sudo sysctl -w net.ipv4.icmp_echo_ignore_all=1 && echo "Ping BLOQUEADO." ;;
  off) sudo sysctl -w net.ipv4.icmp_echo_ignore_all=0 && echo "Ping LIBERADO." ;;
  *)   echo "Uso: $0 on|off"; exit 1 ;;
esac
