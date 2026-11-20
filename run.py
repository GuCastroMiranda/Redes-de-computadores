"""
run.py — Ponto de entrada do NetProbe Wi-Fi.

Como usar:  python run.py   (ou dar dois cliques em INICIAR.bat)

Sobe o servidor web local e abre o navegador em http://localhost:8000
Se a porta 8000 estiver ocupada, tenta 8001, 8002... automaticamente.
Para encerrar: Ctrl+C nesta janela.
"""

import os
import sys
import webbrowser

# garante que os imports funcionem de qualquer pasta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import criar_servidor  # noqa: E402


def main():
    if sys.version_info < (3, 8):
        print("Este programa precisa de Python 3.8 ou mais novo.")
        sys.exit(1)

    servidor = None
    for porta in range(8000, 8011):
        try:
            servidor = criar_servidor(porta)
            break
        except OSError:
            continue
    if servidor is None:
        print("Nenhuma porta livre entre 8000 e 8010.")
        sys.exit(1)

    endereco = "http://127.0.0.1:%d" % servidor.server_address[1]
    print("=" * 56)
    print("  NetProbe Wi-Fi rodando em %s" % endereco)
    print("  Para encerrar: Ctrl+C")
    print("=" * 56)
    if "--sem-navegador" not in sys.argv:
        webbrowser.open(endereco)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando...")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
