# Redes de Computadores — NetProbe Wi-Fi

Trabalho em grupo da disciplina de **Redes de Computadores**: um scanner de rede local
(Wi-Fi) com interface web em tempo real.

> **Status:** 🟡 em desenvolvimento · MVP funcional (os 5 itens implementados e testados num PC Windows)
> **Apresentação:** segunda-feira, 23/11/2026, ao vivo no notebook Windows do grupo
> **Última atualização:** 20/11/2026

---

## O que o NetProbe faz

| # | Item avaliado (2 pts cada) | Arquivo | Como funciona |
|---|---|---|---|
| 1 | **Varredura ICMP (Ping Sweep)** com rede e timeout parametrizáveis | [`scanner/icmp_scan.py`](scanner/icmp_scan.py) | Pinga todos os IPs da faixa `/24` em paralelo (64 ao mesmo tempo) com o timeout escolhido. Só conta como online quem devolve um *Echo Reply* de verdade (`TTL=`). |
| 2 | **Colisão / ARP Probe** nos IPs que não responderam ao ping | [`scanner/arp_probe.py`](scanner/arp_probe.py) | Para cada IP sem resposta ICMP, envia uma requisição **ARP** (camada 2) usando a função nativa `SendARP` do Windows. Se alguém responde, o IP está ocupado (o dispositivo só bloqueia ping); se não, está realmente vazio. |
| 3 | **Vinculação IP ↔ MAC** | [`scanner/mac_table.py`](scanner/mac_table.py) | Monta a tabela IP (lógico, camada 3) ↔ MAC (físico, camada 2) de todos os hosts online, no formato `AA:BB:CC:DD:EE:FF`. |
| 4 | **Interface em tempo real** (online/offline) | [`web/`](web/) + [`server.py`](server.py) | Painel web em `http://127.0.0.1:8000`. Os dispositivos aparecem na tabela **enquanto** a varredura acontece, via *Server-Sent Events* (SSE). Tem filtros, resumo, barra de progresso e histórico. |
| 5 | **Portas abertas** com range parametrizável | [`scanner/port_scan.py`](scanner/port_scan.py) | *TCP Connect Scan* (3-way handshake) em cada host online, da porta inicial à final, com o nome do serviço conhecido (80/HTTP, 443/HTTPS…). |

Apoio:
- [`scanner/orchestrator.py`](scanner/orchestrator.py): executa as 4 etapas em ordem e envia cada novidade para a tela.
- [`scanner/models.py`](scanner/models.py): estruturas de dados e **validação** de todos os parâmetros (rede, timeout, portas).
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

**Requisito:** Windows com **Python 3.8 ou mais novo**. Não precisa instalar nenhuma biblioteca
(tudo usa só a biblioteca padrão do Python) nem ser administrador.

```bat
git clone https://github.com/GuCastroMiranda/Redes-de-computadores.git
cd Redes-de-computadores
python run.py
```

Ou dê dois cliques em **`INICIAR.bat`**. O navegador abre sozinho em `http://127.0.0.1:8000`
(se a porta 8000 estiver ocupada, usa 8001, 8002…).

Na tela: confira a rede sugerida (ex.: `192.168.0.0/24`), ajuste timeout e portas e clique em
**Iniciar varredura**.

### Validações (o programa nunca começa com parâmetro inválido)
- Rede em formato CIDR, máscara entre `/24` e `/30` (se digitar só o IP, assume `/24`)
- Timeout entre 50 e 5000 ms
- Portas entre 1 e 65535, inicial ≤ final, no máximo 2000 portas por varredura
- Só uma varredura por vez (clique duplo ou segunda aba recebem aviso)

## Resultado do primeiro teste (PC Windows, rede doméstica /24)

| Etapa | Tempo |
|---|---|
| ICMP em 254 IPs (timeout 300 ms) | ~2 s |
| ARP Probe em 250 IPs | ~8 s |
| Portas 1–1024 em 4 hosts | ~8 s |
| **Total** | **~18 s** |

Encontrou o roteador (53/DNS, 80/HTTP) e o próprio PC (135, 139, 445) com IP e MAC corretos
(conferidos com `arp -a`).

## Roteiro / progresso

- [x] Escolha do projeto e plano de ação
- [x] Validar ping, ARP (`SendARP`) e leitura de MAC no Windows sem admin e sem bibliotecas
- [x] Itens 1 a 5 implementados + histórico SQLite
- [x] Validação de entradas e trava contra varreduras simultâneas
- [ ] Testes de casos de borda (cancelar no meio, rede vazia, desconectar host e reescanear)
- [ ] Script `scripts/firewall_demo.ps1` (liga/desliga bloqueio de ping para demonstrar o ARP Probe)
- [ ] `docs/GUIA_ARGUICAO.md`: conceitos e perguntas prováveis por integrante
- [ ] Teste no notebook da apresentação, no roteador portátil (hotspot) do celular
- [ ] Ensaio geral e *code freeze* (domingo, 22/11)

## Estrutura

```
Redes-de-computadores/
├── run.py              # ponto de entrada (sobe o servidor e abre o navegador)
├── INICIAR.bat         # atalho de 2 cliques para o run.py
├── server.py           # servidor web + tempo real (SSE)
├── historico.py        # banco SQLite com o histórico
├── scanner/
│   ├── models.py       # dados + validação
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
