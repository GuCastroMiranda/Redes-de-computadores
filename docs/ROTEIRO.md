# Roteiro da apresentação — NetProbe Wi-Fi

> Segunda-feira, 23/11/2026 · notebook **Linux** · rede = roteador portátil (hotspot) de um celular
> **Regra de ouro:** qualquer travamento ou ajuste de código durante a apresentação = **nota 0**.
> Por isso: **ninguém edita código depois do ensaio de domingo**, e seguimos este roteiro à risca.

---

## 1. Antes de sair de casa (domingo à noite)

- [ ] Notebook com a versão final: `cd Redes-de-computadores && git pull` → depois **não mexer mais**
- [ ] Ensaio completo feito no **mesmo hotspot** que será usado na segunda (veja o item 4)
- [ ] Notebook e celular do hotspot **carregados**; levar carregadores
- [ ] Se possível, cópia da pasta em um pendrive (plano B: rodar em outro notebook Linux ou Windows)

## 2. Na sala, 10 minutos antes (checklist pré-voo)

1. Ligar o **hotspot** no celular "roteador". Desligar o Wi-Fi da faculdade no notebook.
2. Conectar ao hotspot: o **notebook** + **2 a 4 celulares** do grupo (de preferência 1 iPhone).
   **Telas dos celulares LIGADAS e desbloqueadas** durante toda a demonstração (com a tela
   apagada, o Wi-Fi do celular entra em economia de energia e pode não responder — visto no teste
   de 20/11 com um Galaxy A6). Se possível, desativar a economia de bateria nos celulares.
3. Se houver demonstração com notebook de colega bloqueando ping: conectar e rodar
   `./scripts/bloquear_ping_linux.sh on` (Linux) ou `.\scripts\bloquear_ping_windows.ps1 on` (Windows, como Admin).
4. No notebook da apresentação, abrir o terminal na pasta e rodar:
   ```bash
   ./iniciar.sh
   ```
   Digitar a senha do sudo. O navegador abre sozinho em `http://127.0.0.1:8000`.
5. Conferir no topo da tela: **`Linux · ARP montado à mão (raw socket)`**.
   (Se aparecer "ARP via kernel (sem sudo)", fechar e rodar `./iniciar.sh` de novo, com a senha.)
6. Fazer **uma varredura de aquecimento** e conferir que os celulares aparecem.
   Ela fica salva no histórico (é o nosso plano B, veja o item 5).

## 3. Sequência da demonstração (~10 min)

| Tempo | Quem | O que fazer na tela | O que falar |
|---|---|---|---|
| 0:00 | Pessoa 1 | Mostrar a tela inicial e o topo (IP, sistema, método ARP) | Objetivo do NetProbe, arquitetura (1 arquivo por item), fluxo das 4 etapas |
| 1:30 | Pessoa 2 | Conferir a rede (ex: `10.x.x.0/24`) e timeout 1000 ms (padrão); **Iniciar varredura** | Ping Sweep: ICMP Echo Request/Reply, faixa /24 = 254 IPs, timeout, paralelismo |
| 3:00 | Pessoa 4 | Apontar a coluna MAC; no terminal: `ip neigh` e comparar 1 MAC | IP (camada 3) × MAC (camada 2), ARP faz a ponte |
| 4:30 | Pessoa 3 | Filtro **Bloqueando ICMP**: mostrar o aparelho "ONLINE · ICMP bloqueado" | Por que o ping falha, por que o ARP não pode ser bloqueado, pacote ARP montado à mão |
| 6:00 | Pessoa 5 | Mostrar as portas encontradas; mudar o range (ex: 1–100) e varrer de novo | TCP 3-way handshake, connect scan, range parametrizável |
| 7:30 | Pessoa 6 (ou 1) | **Desconectar** um celular do hotspot e varrer de novo → aparece offline | Status em tempo real, histórico SQLite |
| 8:30 | Todos | Perguntas do professor | Usar o `GUIA_ARGUICAO.md` |

**Demonstrações extras (se o professor pedir):**
- **Timeout:** rodar com 50 ms e depois com 1000 ms; mostrar a diferença no tempo total.
- **Validação:** digitar uma rede inválida (`abc`) ou porta inicial maior que a final → mensagem
  em vermelho, nada quebra.
- **Porta conhecida:** em outro terminal do notebook, `python3 -m http.server 8080`; varrer com
  range 8000–8100 → a porta 8080 aparece no IP do próprio notebook. (`Ctrl+C` para parar.)

## 4. Ensaio de domingo (obrigatório)

- [ ] Mesmo celular de hotspot, mesmos aparelhos, mesmo notebook
- [ ] Rodar a sequência inteira do item 3 cronometrando
- [ ] Cada pessoa responde, sem olhar, 3 perguntas do guia sobre o seu item
- [ ] Testar o plano B (item 5)
- [ ] **Code freeze:** depois do ensaio, ninguém altera nada no código

## 5. Se algo der errado (sem tocar no código)

| Situação | O que fazer |
|---|---|
| Um celular não aparece | Ligar a tela dele, mandar um ping no terminal (`ping -c 3 <ip>`) para "acordá-lo" e varrer de novo |
| Nenhum celular aparece (hotspot isola os aparelhos) | Trocar para o hotspot de outro celular (testado no ensaio) |
| Rede da faculdade/hotspot caiu | Clicar numa varredura do **Histórico**: a tabela salva no SQLite reaparece |
| Navegador não abriu | Abrir manualmente `http://127.0.0.1:8000` |
| "Já existe uma varredura em andamento" | Esperar terminar ou clicar em **Cancelar** e iniciar de novo |
| Terminal fechado sem querer | Rodar `./iniciar.sh` de novo |
| Notebook travou | Plano B: pendrive em outro notebook (`./iniciar.sh` no Linux, `INICIAR.bat` no Windows) |
