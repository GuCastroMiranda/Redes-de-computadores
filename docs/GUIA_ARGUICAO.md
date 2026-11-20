# Guia de arguição — NetProbe Wi-Fi

> O professor pode perguntar **qualquer trecho** a **qualquer pessoa**. Cada um domina o seu
> item, mas todos devem saber responder a **Parte 0** (visão geral).
> Dica: ao responder, aponte o arquivo e a função na tela (`Ctrl+F` no editor).

---

## Parte 0 — Visão geral (todos)

**O que o programa faz, em uma frase?**
Descobre quais dispositivos estão ligados numa rede local /24 (por ping e por ARP), mostra o
IP e o MAC de cada um e quais portas TCP estão abertas, tudo em tempo real numa página web.

**Qual a ordem das etapas?** (`scanner/orchestrator.py`, função `executar`)
1. ICMP (ping) em todos os IPs → 2. ARP nos que não responderam → 3. tabela IP↔MAC dos
online → 4. portas abertas dos online. Cada novidade vai para a tela na hora.

**Por que Python e sem bibliotecas externas?**
Para não depender de instalação na hora da apresentação: tudo usa a biblioteca padrão
(`subprocess`, `socket`, `ctypes`, `sqlite3`, `http.server`, `concurrent.futures`).

**Por que roda com `sudo`?**
Para o item 2 montar o pacote ARP e enviá-lo direto na placa de rede (socket *raw*, camada 2).
O Linux só permite isso com a permissão `CAP_NET_RAW` (root). Sem sudo o programa ainda
funciona, pedindo para o kernel fazer o ARP, mas é menos preciso (o kernel usa um cache).

**Funciona em Windows também?** Sim. As diferenças ficam em `scanner/plataforma.py`
(comando ping, tabela ARP, MAC da máquina). No Windows o ARP usa a função `SendARP` do sistema.

**Camadas envolvidas (modelo OSI/TCP-IP):**

| Item | Protocolo | Camada |
|---|---|---|
| 1 Ping Sweep | ICMP | 3 – Rede |
| 2 ARP Probe | ARP | 2 – Enlace (faz a ponte com a 3) |
| 3 IP↔MAC | IP (lógico) × MAC (físico) | 3 × 2 |
| 5 Portas | TCP | 4 – Transporte |
| 4 Interface | HTTP + SSE | 7 – Aplicação |

---

## Pessoa 2 — Item 1: Varredura ICMP (`scanner/icmp_scan.py`)

**Conceito.** O ping envia um **ICMP Echo Request (tipo 8)**; quem está ligado e não bloqueia
responde **Echo Reply (tipo 0)**. ICMP é um protocolo de controle que viaja dentro do IP.

**Como o código faz.**
- `montar_comando`: monta o comando do sistema: Linux `ping -c 1 -W <segundos>`,
  Windows `ping -n 1 -w <ms>`. `-c/-n 1` = um pacote só; `-W/-w` = timeout.
- `pingar`: executa o ping e só considera online se a resposta tiver **`TTL=`** (prova de Echo
  Reply verdadeiro; no Windows o ping pode "dar certo" com a mensagem "host inacessível").
  Também lê a latência (`time=3.45 ms`).
- `varrer`: dispara **64 pings em paralelo** (`ThreadPoolExecutor`) e avisa a tela a cada resposta.

**Perguntas prováveis.**
- *Quantos IPs tem uma /24?* 256 endereços; 254 usáveis (tira o endereço de rede `.0` e o de
  broadcast `.255`). `rede.hosts()` já devolve só os 254.
- *Para que serve o timeout?* É quanto esperamos por cada resposta. Menor = mais rápido, mas
  pode perder aparelho lento (ex: celular economizando bateria). Maior = mais confiável e mais lento.
- *Por que em paralelo?* Em sequência, 254 × 300 ms ≈ 76 s. Em paralelo, ~2 s. O trabalho é
  quase só esperar a rede, então várias threads ao mesmo tempo resolvem.
- *Por que um aparelho ligado pode não responder ao ping?* Firewall (Windows bloqueia por
  padrão em rede pública), iPhone, configuração do sistema. Por isso existe o item 2.
- *O que é TTL?* *Time To Live*: contador de saltos do pacote IP; cada roteador diminui 1.
  Evita pacote rodando em loop para sempre.
- *Por que o ping funciona sem root no Linux?* O Linux permite "ICMP datagram sockets" a
  usuários comuns (ou o `ping` tem a permissão `cap_net_raw`).

---

## Pessoa 3 — Item 2: ARP Probe / colisão (`scanner/arp_probe.py`)

**Conceito.** Para enviar qualquer pacote numa rede local, o aparelho precisa do **MAC** do
destino. Ele pergunta via **ARP Request** em broadcast ("quem tem o IP X?"), e o dono responde
com **ARP Reply** (seu MAC). Como sem ARP o aparelho nem consegue usar a rede, **firewalls não
bloqueiam ARP**. Então: não respondeu ping, mas respondeu ARP → está ligado (bloqueia ICMP).
Não respondeu nenhum dos dois → IP vazio.

**Como o código faz (modo da apresentação, com sudo).**
- `montar_pacote_arp`: monta o quadro **byte a byte**:
  - Ethernet (14 bytes): MAC destino `FF:FF:FF:FF:FF:FF` (broadcast), MAC origem (nosso),
    tipo `0x0806` (ARP).
  - ARP (28 bytes): hardware 1 (Ethernet), protocolo `0x0800` (IPv4), tamanhos 6 e 4,
    **operação 1 (request)**, nosso MAC/IP, MAC alvo zerado (desconhecido), IP perguntado.
- `_sondar_linux_raw`: abre um socket `AF_PACKET`/`SOCK_RAW` na placa Wi-Fi, envia um
  request para cada IP sem resposta, escuta por 1,5 s e lê cada resposta em
  `ler_resposta_arp` (**operação 2 = reply**; pega o MAC e o IP de quem respondeu).
  Faz 2 rodadas para não perder resposta.
- Sem sudo: `_sondar_linux_kernel` manda um UDP qualquer ao IP, o kernel faz o ARP, e lemos
  `ip -s neigh` aceitando só quem confirmou agora. Windows: `SendARP`.

**Perguntas prováveis.**
- *ARP é de que camada?* Enlace (2). Ele liga a camada 3 (IP) à 2 (MAC). Não passa de roteador:
  só funciona dentro da mesma rede local (mesmo domínio de broadcast).
- *Por que o request vai em broadcast e o reply não?* Quem pergunta não sabe o MAC do dono,
  então pergunta a todos; o dono responde só para quem perguntou.
- *O que é "colisão" aqui / ARP Probe da RFC 5227?* Antes de usar um IP, um aparelho pergunta via
  ARP se alguém já o usa; se alguém responde, há **conflito (colisão) de IP**. Usamos o mesmo
  princípio: resposta ARP = IP ocupado. (O probe "oficial" usa IP de origem `0.0.0.0`; nós usamos
  o nosso IP, que é um ARP request normal, e todos os aparelhos respondem.)
- *Por que só nos IPs que não responderam ao ping?* Quem respondeu ao ping já está provado
  online; economiza tempo e é o que o enunciado pede.
- *Por que precisa de sudo?* Socket raw na camada 2 exige `CAP_NET_RAW`.
- *Por que não usar só a tabela ARP do sistema?* Ela é um **cache**: guarda aparelhos que já
  saíram da rede por um tempo. Com o pacote próprio, cada resposta é real e recente.

---

## Pessoa 4 — Item 3: Vinculação IP ↔ MAC (`scanner/mac_table.py`)

**Conceito.** **IP** = endereço lógico (camada 3), pode mudar (DHCP). **MAC** = endereço físico
da placa (camada 2), 48 bits, ex: `30:F6:EF:33:86:FF`. Os 3 primeiros bytes (**OUI**)
identificam o fabricante.

**Como o código faz.** `montar_tabela`:
- Quem veio do item 2 já tem MAC.
- Quem respondeu ao ping: o MAC já está no cache ARP do sistema (`ler_tabela_arp`:
  `/proc/net/arp` no Linux, `arp -a` no Windows); se faltar, pergunta via ARP.
- A própria máquina não está no cache: lê da placa (`/sys/class/net/<placa>/address`).
- `normalizar_mac` padroniza tudo para `AA:BB:CC:DD:EE:FF`.

**Como conferir ao vivo.** No terminal: `ip neigh` (Linux) ou `arp -a` (Windows) e comparar
com a tabela. Para a própria máquina: `ip link`.

**Perguntas prováveis.**
- *Por que precisamos do MAC se já temos o IP?* Na rede local o quadro Ethernet/Wi-Fi é
  entregue pelo MAC. O IP diz "para quem" (fim a fim); o MAC diz "para qual placa" (salto local).
- *O MAC do celular parece "estranho" / muda entre redes. Por quê?* Celulares usam **MAC
  aleatório por rede** (privacidade). Dá para ver: o 2º dígito hexa é 2, 6, A ou E (bit
  "administrado localmente" ligado), ex: `32:0D:...`.
- *No celular-roteador, o IP e o MAC mostrados em "Sobre o telefone" são diferentes dos da
  tabela. Está errado?* Não. O celular-roteador está em **duas redes**: a da operadora (5G, ex:
  `10.139.x.x`, lado da internet) e a do hotspot (ex: `10.251.150.210`, a que varremos). E no
  hotspot o Samsung usa **MAC aleatório** (ex: `32:0D:...`) em vez do MAC de fábrica da placa
  (`80:54:2D:...`). Cada interface de rede tem seu próprio IP; o MAC pode ser o físico ou um gerado.
- *Dá para ver o MAC de um aparelho em outra rede (internet)?* Não. O MAC só existe dentro da
  rede local; ao passar por um roteador, o quadro é refeito com outros MACs.

---

## Pessoa 5 — Item 5: Portas abertas (`scanner/port_scan.py`)

**Conceito.** Uma porta aberta = um programa (serviço) esperando conexões. O TCP abre conexão
com o **3-way handshake**: `SYN` → `SYN/ACK` → `ACK`.
- Respondeu `SYN/ACK` → porta **aberta**.
- Respondeu `RST` → **fechada** (ninguém escutando).
- Não respondeu dentro do timeout → **filtrada** (firewall descartou).

**Como o código faz.**
- `porta_aberta`: `socket.connect_ex((ip, porta))` tenta o handshake completo; devolve 0 se
  conectou. Fecha logo em seguida, sem enviar dados (*TCP connect scan*).
- `varrer_portas`: testa da porta inicial à final, **200 conexões em paralelo**, com o mesmo
  timeout da tela.
- `nome_servico`: mostra o serviço conhecido (80 = HTTP, 443 = HTTPS, 53 = DNS...).

**Perguntas prováveis.**
- *Por que só portas TCP?* UDP não tem handshake: porta UDP aberta normalmente não responde
  nada, então não dá para distinguir aberta de filtrada de forma confiável.
- *Diferença para o SYN scan do nmap?* O nmap `-sS` manda só o `SYN` e não completa o
  handshake (meia-abertura, exige root). O nosso completa a conexão (mais simples, não exige root).
- *Faixas de portas?* 0–1023 bem conhecidas (HTTP, SSH...), 1024–49151 registradas,
  49152–65535 dinâmicas.
- *Por que limitar a 2000 portas por varredura?* Tempo de apresentação: 2000 portas × vários
  hosts com timeout pode levar minutos. O limite e a validação ficam em `scanner/models.py`.
- *Por que o celular-roteador tem a 53 aberta?* Ele é o servidor **DNS** da rede do hotspot.

---

## Pessoa 1 (e 6) — Item 4: Interface em tempo real + orquestração e banco

**Arquivos:** `web/index.html`, `web/app.js`, `web/style.css`, `server.py`,
`scanner/orchestrator.py`, `historico.py`, `scanner/models.py`.

**Conceito do tempo real: SSE (*Server-Sent Events*).** O navegador abre **uma** conexão HTTP em
`/api/eventos` que fica aberta; o servidor "empurra" cada novidade como uma linha `data: {...}`.
Na página, `new EventSource("/api/eventos")` recebe cada evento (`host`, `progresso`, `etapa`,
`fim`) e redesenha a tabela.

**Como o código faz.**
- `server.py`: servidor HTTP da biblioteca padrão. `EstadoVarredura.emitir` guarda cada evento
  e acorda as conexões SSE (`threading.Condition`). A varredura roda numa thread separada.
- `iniciar` tem uma **trava**: se já existe varredura rodando, responde **409** (clique duplo não
  quebra nada).
- `scanner/models.py` valida tudo antes de começar (rede /24 a /30, timeout 50–5000 ms,
  portas 1–65535, inicial ≤ final). Erro → mensagem em vermelho, código **400**.
- `historico.py`: grava cada varredura no **SQLite** (arquivo `netprobe.db`, tabela
  `varreduras`). Clicando no histórico, a tabela salva reaparece.

**Perguntas prováveis.**
- *Por que SSE e não atualizar a página a cada X segundos (polling)?* Polling faz requisições
  à toa e atrasa; com SSE a informação chega no instante em que acontece, numa só conexão.
- *E WebSocket?* WebSocket é bidirecional; aqui só o servidor precisa falar, então SSE é mais
  simples (é HTTP comum e o navegador reconecta sozinho).
- *Por que o servidor só escuta em 127.0.0.1?* Só o próprio notebook acessa o painel: ninguém
  da rede consegue disparar varreduras por ele.
- *Onde fica a "base de dados"?* `netprobe.db` (SQLite), na pasta do projeto. Não precisa de
  servidor de banco.
- *O que acontece se clicar em Cancelar?* Um `threading.Event` é ligado; cada etapa confere e
  para de enviar pacotes; a tela recebe "Varredura cancelada".

---

## Perguntas "pegadinha" (todos)

- *Isso é legal?* Só em rede própria ou com autorização (o hotspot é nosso). Varrer rede de
  terceiros sem permissão é invasivo.
- *Por que o próprio notebook aparece com latência "< 1 ms"?* O ping para si mesmo não sai
  pela placa: é respondido internamente.
- *Por que o aparelho X não apareceu?* Pode estar em economia de energia, fora da faixa /24,
  ou o hotspot isola os clientes. Mostrar a tabela com `ip neigh` como prova.
