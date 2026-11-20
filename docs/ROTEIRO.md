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
| 3 a 4 celulares | Aparecem como online via ICMP (telas **ligadas**). Um deles será **desconectado** ao vivo |
| 1 notebook de colega (Linux ou Windows) | Demo do item 2: **bloqueia ping** → aparece "ONLINE · ICMP bloqueado" |
| 1 tablet / celulares extras / 2º notebook | **Reserva** (não conectar: menos aparelhos = menos imprevisto). Plano B se algo falhar |

Total conectado ao hotspot: ~6 aparelhos (o limite do hotspot Samsung costuma ser 10).

## 1. Antes de sair de casa (domingo à noite)

- [ ] Notebook Windows com a versão final: na pasta, `git pull` → depois **não mexer mais**
- [ ] Ensaio completo feito no **mesmo hotspot** que será usado na segunda (veja o item 4)
- [ ] Notebook, celular do hotspot e notebook do colega **carregados**; levar carregadores
- [ ] Cópia da pasta num pendrive (plano B: rodar no notebook Linux com `./iniciar.sh`)
- [ ] Notebook do colega: testar o script de bloquear ping (item 2 do checklist abaixo)

## 2. Na sala, 10 minutos antes (checklist pré-voo)

1. Ligar o **hotspot** no celular "roteador". No notebook Windows, **esquecer/desligar o Wi-Fi da
   faculdade** e conectar só no hotspot.
2. Conectar ao hotspot os **3–4 celulares** e o notebook do colega.
   **Telas dos celulares LIGADAS e desbloqueadas** durante toda a demonstração (com a tela
   apagada, o Wi-Fi do celular entra em economia de energia e pode não responder — visto no teste
   de 20/11 com um Galaxy A6). Se possível, desativar a economia de bateria nos celulares.
3. Notebook do colega bloqueando ping:
   - Linux: `./scripts/bloquear_ping_linux.sh on`
   - Windows: PowerShell **como Administrador**: `.\scripts\bloquear_ping_windows.ps1 on`
4. No notebook Windows: **dois cliques em `INICIAR.bat`**. O navegador abre sozinho em
   `http://127.0.0.1:8000` (não feche a janela preta).
5. Conferir no topo da tela: **`Windows · SendARP (Windows)`** e o IP do hotspot.
6. Fazer **uma varredura de aquecimento** e conferir que todos aparecem.
   Ela fica salva no histórico (é o nosso plano B, veja o item 5).

## 3. Sequência da demonstração (~10 min)

| Tempo | Quem | O que fazer na tela | O que falar |
|---|---|---|---|
| 0:00 | Pessoa 1 | Mostrar a tela inicial e o topo (IP, sistema, método ARP) | Objetivo do NetProbe, arquitetura (1 arquivo por item), fluxo das 4 etapas |
| 1:30 | Pessoa 2 | Conferir a rede (ex: `10.x.x.0/24`) e timeout 1000 ms (padrão); **Iniciar varredura** | Ping Sweep: ICMP Echo Request/Reply, faixa /24 = 254 IPs, timeout, paralelismo |
| 3:00 | Pessoa 4 | Apontar a coluna MAC; num terminal (`cmd`): `arp -a` e comparar 1 MAC | IP (camada 3) × MAC (camada 2), ARP faz a ponte |
| 4:30 | Pessoa 3 | Filtro **Bloqueando ICMP**: mostrar o notebook do colega "ONLINE · ICMP bloqueado"; no `cmd`: `ping <ip dele>` falha | Por que o ping falha, por que o ARP não pode ser bloqueado |
| 6:00 | Pessoa 5 | Mostrar as portas encontradas; mudar o range (ex: 1–100) e varrer de novo | TCP 3-way handshake, connect scan, range parametrizável |
| 7:30 | Pessoa 6 (ou 1) | **Desconectar** um celular do hotspot. **Falar ~1 minuto** sobre o histórico (clicar numa varredura antiga) e só então varrer de novo → o celular aparece offline | Status em tempo real, histórico SQLite |
| 9:00 | Todos | Perguntas do professor | Usar o `GUIA_ARGUICAO.md` |

> **Por que esperar ~1 minuto antes de varrer de novo?** O Windows guarda por alguns segundos
> (até ~45 s) que o celular estava "alcançável". Passado esse tempo ele volta a perguntar via ARP
> de verdade e o celular desconectado sai corretamente como offline (testado em 20/11).

**Demonstrações extras (se o professor pedir):**
- **Timeout:** rodar com 50 ms e depois com 1000 ms; mostrar a diferença no tempo total.
- **Validação:** digitar uma rede inválida (`abc`) ou porta inicial maior que a final → mensagem
  em vermelho, nada quebra.
- **Porta conhecida:** num segundo `cmd`, na pasta do projeto: `python -m http.server 8080`;
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
