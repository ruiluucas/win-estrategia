# 08 — Roadmap

## Estado

- Sessões coletadas: **3** (13/11 exploratória, 16/11 boa, 17/11 truncada)
- Sessões válidas para confirmar: **1** (16/11)
- Sessões exigidas pelo protocolo: **20**
- Hipóteses refutadas: **4** (V1, A1, A5a, A8)
- Hipóteses em avaliação: **2** (A5b, A7)
- Hipóteses bloqueadas por dado: **2** (A2, A3)

## Bloqueio principal

**Coleta confiável.** É o único item que impede todo o resto. A sessão de 17/11
parou às 12:37 sem aviso; 16/11 perdeu 6 h de tarde.

Antes do próximo passo analítico, é preciso que a captura da manhã (09:00–12:15)
seja confiável por 20 dias úteis.

`[MEDIDO]` Falhas de 17/11: MT5 fechou às 11:42 por motivo não identificado; o
coletor não religou sozinho; buraco de 16 min.

## Ordem de trabalho proposta

### 1. Coleta (bloqueante)

- watchdog que verifica a cada 2 min se há gravação nos últimos 60 s
- religar MT5 → ponte → coletor em caso de queda
- avisar quando religar
- critério de sucesso: 20 sessões de manhã sem buraco > 60 s

### 2. Corrigir a rotulagem de A7

`[MEDIDO]` O defeito está identificado: na classe "exaustão", `def_queda` mediu
−227 % — o volume cresceu. O rótulo está invertido.

Trabalho:
- classificar pelo **sinal** de `def_queda`, não por suposição
- separar "volume no nível cai" (consumo) de "volume no nível sobe" (reforço)
- medir os quatro quadrantes: consumo/alívio × passou/segurou

### 3. Definir quem ataca e quem defende

`[INFERIDO]` Esta é a raiz dos três últimos erros. O código supõe qual lado ataca
a partir da posição da borda, mas:

- borda superior de uma região pode ser **parede de compra** (bid) que absorve
  venda
- o mesmo preço pode ter bid e ask simultaneamente

Antes de testar de novo: para cada episódio, registrar **o que de fato está
naquele nível** (bid ou ask, com volume) e **qual lado agride**, medido por
`lado_inferido`. Sem isso, qualquer resultado positivo pode ser artefato de
rotulagem.

### 4. Ampliar A5b

`[MEDIDO-n=148]` É o único resultado de nível B. Replicar em ≥ 3 sessões antes de
qualquer conclusão.

### 5. Só então: modelo

Não antes de existir uma feature com efeito replicado. O histórico mostra que
partir para modelagem antes disso produziu 63 configurações de stop/alvo com
mediana negativa e 185 trades num dia.

## O que NÃO fazer

- Não otimizar parâmetros em amostra de 2 sessões.
- Não reportar média sem mediana.
- Não medir nada sem controle da mesma sessão e horário.
- Não testar hipótese nova sem antes verificar se a anterior falhou por definição
  ou por fenômeno (ver `06-BECOS-SEM-SAIDA.md`).

## Questões abertas para revisores

1. A definição de "região" (densidade de tempo > 1,5×) é arbitrária. Existe
   justificativa melhor para o limiar?
2. Como separar cancelamento de execução sem Level-3? Alguma técnica de
   reconciliação contábil funciona com book agregado a 8,5 leituras/s?
3. A janela de 60 s é a mais adequada para o episódio, ou o fenômeno se resolve
   em menos tempo?
4. Com 2 sessões, existe alguma forma honesta de estimar poder estatístico, ou o
   número de eventos por sessão (~15–30) já condena a amostra de 20?
