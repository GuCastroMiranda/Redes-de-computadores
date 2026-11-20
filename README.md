# Redes de Computadores — NetProbe Wi-Fi

Trabalho em grupo da disciplina de **Redes de Computadores**: um scanner de rede local
(Wi-Fi) com interface web em tempo real. Funciona em **Linux e Windows**.

> **Status:** 🟡 em desenvolvimento · os 5 itens implementados e testados em Windows e Linux
> **Apresentação:** segunda-feira, 23/11/2026, ao vivo num notebook **Linux** do grupo, no roteador portátil (hotspot 5G) de um celular
> **Última atualização:** 20/11/2026 — suporte a Linux (ARP, MAC e latência) + `iniciar.sh`

---

## O que o NetProbe faz

| # | Item avaliado (2 pts cada) | Arquivo | Como funciona |
|---|---|---|---|
| 1 | **Varredura ICMP (Ping Sweep)** com rede e timeout parametrizáveis | [`scanner/icmp_scan.py`](scanner/icmp_scan.py) | Pinga todos os IPs da faixa `/24` em paralelo (64 ao mesmo tempo) com o timeout escolhido. Só conta como online quem devolve um *Echo Reply* de verdade (`TTL=`). |
| 2 | **Colisão / ARP Probe** nos IPs que não responderam ao ping | [`scanner/arp_probe.py`](scanner/arp_probe.py) | Para cada IP sem resposta ICMP, dispara uma requisição **ARP** (camada 2). Se alguém responde, o IP está ocupado (o dispositivo só bloqueia ping); se não, está realmente vazio. **Linux:** envia um pacote UDP ao IP, o kernel dispara o ARP e lemos `/proc/net/arp`. **Windows:** função nativa `SendARP`. |
| 3 | **Vinculação IP ↔ MAC** | [`scanner/mac_table.py`](scanner/mac_table.py) | Monta a tabela IP (lógico, camada 3) ↔ MAC (físico, camada 2) de todos os hosts online, no formato `AA:BB:CC:DD:EE:FF`, a partir do cache ARP do sistema (e da placa de rede, para a própria máquina). |
| 4 | **Interface em tempo real** (online/offline) | [`web/`](web/) + [`server.py`](server.py) | Painel web em `http://127.0.0.1:8000`. Os dispositivos aparecem na tabela **enquanto** a varredura acontece, via *Server-Sent Events* (SSE). Tem filtros, resumo, barra de progresso e histórico. |
| 5 | **Portas abertas** com range parametrizável | [`scanner/port_scan.py`](scanner/port_scan.py) | *TCP Connect Scan* (3-way handshake) em cada host online, da porta inicial à final, com o nome do serviço conhecido (80/HTTP, 443/HTTPS…). |

Apoio:
- [`scanner/orchestrator.py`](scanner/orchestrator.py): executa as 4 etapas em ordem e envia cada novidade para a tela.
- [`scanner/models.py`](scanner/models.py): estruturas de dados e **validação** de todos os parâmetros (rede, timeout, portas).
- [`scanner/plataforma.py`](scanner/plataforma.py): **tudo que muda entre Linux e Windows** (comando ping, tabela ARP, MAC da própria máquina) concentrado num lugar só.
- [`historico.py`](historico.py): grava cada varredura num banco **SQLite** local (`netprobe.db`).

## Fluxo de uma varredura

```
 Parâmetros (rede /24, timeout, porta inicial-final)
        │  validação (models.py)
        ▼
 1. ICMP Ping Sweep ──► responderam? ──► ONLINE (ICMP)
        │ não responderam
        ▼
 2. ARP Probe ─────────► responderam ARP? ──► ONLINE (ICMP bloqueado)
        │ não
        ▼
     OFFLINE
        ▼
 3. Tabela IP ↔ MAC dos online
 4. Portas abertas dos online
        ▼
 Tela em tempo real (SSE) + histórico (SQLite)
```

## Como rodar

**Requisito:** **Python 3.8 ou mais novo** e o comando `ping` (já vem no Linux e no Windows).
Não precisa instalar nenhuma biblioteca (só a biblioteca padrão do Python) nem ser
administrador/root.

**1. Baixar o projeto (só na primeira vez):**
```bash
git clone https://github.com/GuCastroMiranda/Redes-de-computadores.git
```
Para pegar a versão mais nova depois: `git pull` dentro da pasta `Redes-de-computadores`.

**2. Iniciar** — uma forma oficial por sistema:

| Sistema | Como iniciar |
|---|---|
| **Linux** | No terminal, dentro da pasta: `./iniciar.sh` |
| **Windows** | Dois cliques em `INICIAR.bat` |

Os dois só encontram o Python (`python3`/`python`/`py`) e executam o `run.py`. O navegador abre
sozinho em `http://127.0.0.1:8000` (se a porta 8000 estiver ocupada, usa 8001, 8002…). O
sistema operacional detectado aparece no topo da tela. Para encerrar: `Ctrl+C` no terminal
(ou feche a janela).

> Linux: se aparecer "permissão negada", rode uma vez `chmod +x iniciar.sh`.

### Validações (o programa nunca começa com parâmetro inválido)
- Rede em formato CIDR, máscara entre `/24` e `/30` (se digitar só o IP, assume `/24`)
- Timeout entre 50 e 5000 ms
- Portas entre 1 e 65535, inicial ≤ final, no máximo 2000 portas por varredura
- Só uma varredura por vez (clique duplo ou segunda aba recebem aviso)

## Testes realizados

**Windows** (PC, rede doméstica /24, timeout 300 ms, portas 1–1024): ~18 s no total.
Encontrou 4 hosts com IP, MAC e latência corretos; roteador com 53/DNS e 80/HTTP, PC com
135/139/445.

**Linux** (Debian, Python 3.12, usuário comum sem root, rede virtual /24 com 3 máquinas):
~4,5 s no total.

| Máquina de teste | Esperado | Resultado |
|---|---|---|
| Servidor web na porta 8080 | Online por ICMP, porta 8080 aberta | ✅ |
| Máquina que **ignora ping** | Offline no ICMP, **online pelo ARP** | ✅ |
| Gateway da rede | Online por ICMP | ✅ |
| Todos os online | MAC preenchido | ✅ |

## Roteiro / progresso

- [x] Escolha do projeto e plano de ação
- [x] Validar ping, ARP e leitura de MAC sem admin e sem bibliotecas
- [x] Itens 1 a 5 implementados + histórico SQLite
- [x] Validação de entradas e trava contra varreduras simultâneas
- [x] Suporte a Linux (o notebook da apresentação é Linux) — testado
- [ ] Teste no notebook Linux da apresentação, no hotspot 5G, com 3+ celulares conectados
- [ ] Testes de casos de borda (cancelar no meio, rede vazia, desconectar host e reescanear)
- [ ] Roteiro de demonstração dos itens 2 (host bloqueando ping) e 5 (porta conhecida aberta)
- [ ] `docs/GUIA_ARGUICAO.md`: conceitos e perguntas prováveis por integrante
- [ ] Ensaio geral e *code freeze* (domingo, 22/11)

## Estrutura

```
Redes-de-computadores/
├── iniciar.sh          # COMO INICIAR no Linux: ./iniciar.sh
├── INICIAR.bat         # COMO INICIAR no Windows: dois cliques
├── run.py              # chamado pelos dois acima (sobe o servidor e abre o navegador)
├── server.py           # servidor web + tempo real (SSE)
├── historico.py        # banco SQLite com o histórico
├── scanner/
│   ├── models.py       # dados + validação
│   ├── plataforma.py   # diferenças Linux x Windows
│   ├── icmp_scan.py    # item 1
│   ├── arp_probe.py    # item 2
│   ├── mac_table.py    # item 3
│   ├── port_scan.py    # item 5
│   └── orchestrator.py # executa as etapas em ordem
└── web/                # item 4 (index.html, style.css, app.js)
```

## Uso responsável

Ferramenta acadêmica para redes **próprias** ou com autorização (o hotspot do grupo na
apresentação). Não use para varrer redes de terceiros.
