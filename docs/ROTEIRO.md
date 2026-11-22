# Roteiro da apresentação — NetProbe Wi-Fi

> Segunda-feira, 23/11/2026 · notebook **Windows** do Gustavo · rede = roteador portátil (hotspot) de um celular
> **Regra de ouro:** qualquer travamento ou ajuste de código durante a apresentação = **nota 0**.
> Por isso: **ninguém edita código depois do ensaio de domingo**, e seguimos este roteiro à risca.

---

## 0. Equipamentos (o que temos e quem faz o quê)

| Equipamento | Papel na demonstração |
|---|---|
| Notebook **Windows** do Gustavo | Roda o NetProbe (`INICIAR.bat`) — é o que aparece no projetor |
| 1 celular | **Roteador** (hotspot). Tela ligada, carregando |
| 1 notebook extra + tablet | Alvos **estáveis** (notebook não "dorme" na rede como celular) |
| 2 a 3 celulares **aprovados no teste de estabilidade** | Aparecem como online via ICMP (telas **ligadas**). Um deles será **desconectado** ao vivo |
| 1 notebook de colega (Linux ou Windows) | Demo do item 2: **bloqueia ping** → aparece "ONLINE · ICMP bloqueado" |
| 1 tablet / celulares extras / 2º notebook | **Reserva** (não conectar: menos aparelhos = menos imprevisto). Plano B se algo falhar |

Total conectado ao hotspot: ~6 aparelhos (o limite do hotspot Samsung costuma ser 10).

## 1. Antes de sair de casa (domingo à noite)

- [ ] Notebook Windows com a versão final: na pasta, `git pull` → depois **não mexer mais**
- [ ] Ensaio completo feito no **mesmo hotspot** que será usado na segunda (veja o item 4)
- [ ] Notebook, celular do hotspot e notebook do colega **carregados**; levar carregadores
- [ ] Cópia da pasta num pendrive (plano B: rodar no notebook Linux com `./iniciar.sh`)
- [ ] Notebook do colega: testar o script de bloquear ping (item 2 do checklist abaixo)
- [ ] **Teste de estabilidade** (no ensaio): todos conectados no hotspot, rodar
      `python3 scripts/monitorar.py` (Windows: `python scripts\monitorar.py`) por **5 minutos**.
      Aparelho que tiver qualquer linha **SUMIU** fica de **reserva** (não entra na demo).
      Visto em 20/11: um Galaxy A12 ficava "conectado" no hotspot, mas mudo na rede (nem ARP
      respondia) por minutos — não é falha do NetProbe, o próprio `ping` do sistema falhava.

## 2. Na sala, 10 minutos antes (checklist pré-voo)

1. Ligar o **hotspot** no celular "roteador". No notebook Windows, **esquecer/desligar o Wi-Fi da
   faculdade** e conectar só no hotspot.
2. Conectar ao hotspot os **3–4 celulares** e o notebook do colega.
   **Telas dos celulares LIGADAS e desbloqueadas** durante toda a demonstração (com a tela
   apagada, o Wi-Fi do celular entra em economia de energia e pode não responder — visto no teste
   de 20/11 com um Galaxy A6). Se possível, desativar a economia de bateria nos celulares.
3. Notebook do colega bloqueando ping (**nunca** no notebook que roda o NetProbe: a própria
   máquina aparece só como "ONLINE · esta máquina", não como "ICMP bloqueado"):
   - Linux: `./scripts/bloquear_ping_linux.sh on`
   - Windows: PowerShell **como Administrador**: `.\scripts\bloquear_ping_windows.ps1 on`
4. No notebook Windows: **dois cliques em `INICIAR.bat`**. O navegador abre sozinho em
   `http://127.0.0.1:8000` (não feche a janela preta).
5. Conferir no topo da tela: **`Windows · SendARP (Windows)`** e o IP do hotspot.
6. Fazer **uma varredura de aquecimento** e conferir que todos aparecem.
   Ela fica salva no histórico (é o nosso plano B, veja o item 5).

## 3. Sequência da demonstração (~12 min) — dividida por integrante

> Ordem = ordem dos itens do enunciado. Cada pessoa **mostra na tela**, **explica o conceito** e
> **sabe abrir o seu arquivo** se o professor pedir. As perguntas prováveis de cada um estão no
> `docs/GUIA_ARGUICAO.md` (seção com o mesmo número de pessoa). **Grupo de 5:** a Pessoa 1 faz
> também a parte da Pessoa 6.

| # | Quem | Tempo | Item do enunciado | Arquivo que defende |
|---|---|---|---|---|
| 1 | Pessoa 1 — ______ | 0:00–1:30 | Abertura e arquitetura | `run.py`, `server.py`, `scanner/orchestrator.py` |
| 2 | Pessoa 2 — ______ | 1:30–3:30 | **Item 1 · Varredura ICMP (Ping Sweep)** | `scanner/icmp_scan.py` |
| 3 | Pessoa 3 — ______ | 3:30–5:30 | **Item 2 · Colisão / ARP Probe** | `scanner/arp_probe.py` |
| 4 | Pessoa 4 — ______ | 5:30–7:00 | **Item 3 · Vinculação IP/MAC** | `scanner/mac_table.py` |
| 5 | Pessoa 5 — ______ | 7:00–9:00 | **Item 5 · Portas abertas** | `scanner/port_scan.py` |
| 6 | Pessoa 6 — ______ | 9:00–11:00 | **Item 4 · Interface em tempo real** + histórico | `web/`, `server.py` (SSE), `scanner/models.py` |
| — | Todos | 11:00– | Perguntas do professor | `docs/GUIA_ARGUICAO.md` |

### Pessoa 1 — Abertura e arquitetura (1 min 30)
- **Tela:** NetProbe já aberto (varredura de aquecimento feita). Apontar o topo: IP do notebook,
  `Windows · SendARP (Windows)`, rede sugerida.
- **Fala:** "O NetProbe é um inventário de rede doméstica: descobre quem está conectado, mesmo
  aparelhos que bloqueiam ping, mostra o MAC de cada um e as portas abertas. Usamos só a biblioteca
  padrão do Python: não precisa instalar nada. Cada item do enunciado é um arquivo separado dentro de
  `scanner/`. O `orchestrator.py` executa as 4 etapas em ordem: ping → ARP nos que não responderam →
  tabela IP/MAC → portas dos que estão online. O `server.py` é um servidor web local (127.0.0.1) que
  envia o progresso para o navegador em tempo real."
- **Passa para a Pessoa 2.**

### Pessoa 2 — Item 1: Varredura ICMP (2 min)
- **Tela:** mostrar o campo **Rede** (`x.x.x.0/24` = 254 IPs) e o campo **Timeout (ms)** = 1000.
  Clicar **Iniciar varredura**. Enquanto roda, apontar a barra de progresso e os aparelhos
  aparecendo com o selo **ICMP** e a latência.
- **Fala:** "Mandamos um ICMP Echo Request para cada IP da faixa e esperamos o Echo Reply até o
  timeout. Os dois são parametrizáveis na tela, como pede o enunciado. Para ser ágil, pingamos
  vários IPs ao mesmo tempo (várias threads); por isso o /24 inteiro termina em segundos, e não em 254
  × 1 s. Quem não respondeu não é dado como offline ainda: vai para a etapa seguinte."
- **Extra, se pedirem:** varrer com timeout 50 ms e comparar o tempo total e os aparelhos achados.

### Pessoa 3 — Item 2: Colisão / ARP Probe (2 min)
- **Tela:** filtro **Bloqueando ICMP** → notebook do colega com o selo **ONLINE · ICMP bloqueado**.
  Abrir o `cmd`: `ping <ip do colega>` → falha (esgotado o tempo limite).
- **Fala:** "Esse notebook está com o firewall bloqueando ping, então o item 1 não o achou. Para
  todo IP que não respondeu, mandamos uma pergunta ARP: 'quem tem este IP?'. O ARP é obrigatório
  para a rede local funcionar; sem ele o aparelho não recebe nada. Por isso o firewall não pode
  bloqueá-lo. Se chega resposta, o IP está ocupado e só bloqueou o ICMP; se ninguém responde, o IP
  está vazio de verdade. No Windows usamos a função `SendARP` do próprio sistema."
- **Lembrete:** o bloqueio de ping é ativado no notebook DO COLEGA, nunca no que roda o NetProbe.

### Pessoa 4 — Item 3: Vinculação IP/MAC (1 min 30)
- **Tela:** apontar a coluna **MAC** da tabela. No `cmd`: `arp -a` e comparar o MAC de 1 aparelho
  com o da tela (iguais).
- **Fala:** "O IP é o endereço da camada 3 (rede) e pode mudar; o MAC é o endereço da placa, camada
  2. Na rede local os quadros são entregues por MAC, e o ARP é quem traduz IP → MAC. Nossa tabela
  junta o IP de cada aparelho online com o MAC que o ARP devolveu; o MAC do próprio notebook vem
  da placa de rede. Celulares modernos usam MAC aleatório por rede (privacidade), por isso o MAC
  do hotspot pode ser diferente do MAC 'de fábrica' que aparece nas configurações."

### Pessoa 5 — Item 5: Portas abertas (2 min)
- **Tela:** apontar as portas encontradas (ex.: 53/DNS no celular-roteador). Mudar **Porta inicial /
  Porta final** (ex.: 1–100) e varrer de novo → a etapa de portas respeita o novo range.
- **Fala:** "Só testamos portas dos IPs que responderam. Para cada porta tentamos abrir uma conexão
  TCP (o 3-way handshake: SYN, SYN-ACK, ACK). Se a conexão se completa, a porta está aberta; se der
  recusa ou timeout, está fechada ou filtrada. O range inicial–final é parametrizável na tela, e
  limitamos o timeout de cada porta a 400 ms para não deixar a varredura lenta."
- **Extra, se pedirem:** `python -m http.server 8080` num segundo `cmd` e varrer 8000–8100 → a 8080
  aparece no IP do próprio notebook.

### Pessoa 6 — Item 4: Interface em tempo real + histórico (2 min)
- **Tela:** mostrar os filtros **Online / Bloqueando ICMP / Offline / Todos** e os contadores.
  **Desconectar um celular do hotspot.** Enquanto espera ~1 minuto, clicar numa varredura antiga do
  **Histórico** (a tabela salva reaparece). Depois, varrer de novo → o celular aparece **OFFLINE**.
- **Fala:** "A tela não precisa ser recarregada: o servidor manda cada resultado na hora em que
  acontece, por Server-Sent Events, e o navegador vai atualizando a tabela. Todo resultado também é
  salvo num banco SQLite, então dá para comparar varreduras e ver quem entrou e quem saiu. Esperamos
  um minuto porque o Windows guarda por alguns segundos que o aparelho estava alcançável; depois
  ele volta a perguntar por ARP e o celular desconectado sai como offline."
- **Encerramento:** "Esse é o NetProbe. Ficamos à disposição para perguntas."

> **Por que esperar ~1 minuto antes de varrer de novo?** O Windows guarda por alguns segundos
> (até ~45 s) que o celular estava "alcançável". Passado esse tempo ele volta a perguntar via ARP
> de verdade e o celular desconectado sai corretamente como offline (testado em 20/11).

**Demonstrações extras (se o professor pedir)** — quem responde é o dono do item:
- **Timeout** (Pessoa 2): rodar com 50 ms e depois com 1000 ms; mostrar a diferença no tempo total.
- **Validação** (Pessoa 6): digitar uma rede inválida (`abc`) ou porta inicial maior que a final →
  mensagem em vermelho, nada quebra.
- **Porta conhecida** (Pessoa 5): num segundo `cmd`, na pasta do projeto: `python -m http.server 8080`;
  varrer com range 8000–8100 → a porta 8080 aparece no IP do próprio notebook. (`Ctrl+C` para parar.)
  Se o Windows mostrar aviso do firewall, clicar em **Permitir**. (Testar no ensaio antes.)

## 4. Ensaio de domingo (obrigatório)

- [ ] Mesmo celular de hotspot, mesmos aparelhos, mesmo notebook Windows
- [ ] Rodar a sequência inteira do item 3 cronometrando
- [ ] Cada pessoa responde, sem olhar, 3 perguntas do guia sobre o seu item
- [ ] Testar o plano B (item 5), inclusive o pendrive no notebook Linux
- [ ] **Code freeze:** depois do ensaio, ninguém altera nada no código

## 5. Se algo der errado (sem tocar no código)

| Situação | O que fazer |
|---|---|
| Um celular não aparece | Ligar a tela dele, no `cmd`: `ping -n 3 <ip>` para "acordá-lo" e varrer de novo |
| Celular desconectado ainda aparece online | Esperar ~1 minuto e varrer de novo (veja a nota do item 3) |
| Notebook do colega não aparece como "ICMP bloqueado" (aparece via ICMP) | O script não foi ativado: rodar de novo o `on` (Windows: como Administrador) |
| Nenhum celular aparece (hotspot isola os aparelhos) | Trocar para o hotspot de outro celular (testado no ensaio) |
| Rede da faculdade/hotspot caiu | Clicar numa varredura do **Histórico**: a tabela salva no SQLite reaparece |
| Navegador não abriu | Abrir manualmente `http://127.0.0.1:8000` |
| "Já existe uma varredura em andamento" | Esperar terminar ou clicar em **Cancelar** e iniciar de novo |
| Janela preta fechada sem querer | Dois cliques em `INICIAR.bat` de novo |
| Notebook travou | Plano B: pendrive no notebook Linux (`./iniciar.sh`, senha do sudo) |
