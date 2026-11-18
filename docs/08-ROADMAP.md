# 08 — Roadmap

## Estado

- Sessões coletadas: **4** (13/11 exploratória, 16/11 boa, 17/11 truncada, 18/11 boa)
- Sessões válidas para confirmar: **2** (16/11, 18/11)
- Sessões exigidas pelo protocolo: **20**
- Hipóteses refutadas: **4** (V1, A1, A5a, A8)
- **Hipóteses replicadas: 1 (A9 — frequência do mercado)**
- Hipóteses em avaliação: **2** (A5b, A10)
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

### 2. Corrigir a rotulagem de A7 — **FEITO em 18/11/2026**

`[MEDIDO]` Correção concluída. Quatro erros encontrados e corrigidos: rotulagem
invertida, look-ahead na definição de zona, desfecho tautológico e duplicação de
94 % dos episódios.

`[MEDIDO-n=235]` Resultado pós-correção: o "achado estável" não sobreviveu.
Único efeito que passa Holm e a sensibilidade é **negativo** (`consumo/segurou`
com 35,7 % de alinhamento). Ver `06-BECOS-SEM-SAIDA.md` §11 e
`analise_a7.py`.

### 3. Definir quem ataca e quem defende — **FEITO em 18/11/2026**

`[MEDIDO]` Implementado em `analise_a7.py`: o atacante é escolhido pelo
`lado_inferido` na fita (compra vs. venda no episódio), não pela posição da
borda. O lado do nível (bid ou ask) é registrado com volume inicial e final.

`[INFERIDO]` Continua sendo inferência: `lado_inferido` é derivado de
`last >= ask → compra`, e a taxa de erro dessa regra nunca foi medida
(ver `02-DADOS.md`).

### 4. Ampliar A9 — **PRIORIDADE**

`[MEDIDO]` A9 (frequência) replicou em 2 sessões com configuração fixa
(alvo p60 / stop p30). É o único achado do projeto a sobreviver a dados novos.

**Decisão travada:** usar **alvo p60 / stop p30** — o meio do plato, não o melhor
de nenhuma sessão — e **não alterar nenhum parâmetro** por 5 sessões.

| sessão | total | mediana | acerto |
|---|---:|---:|---:|
| 16/11 | +1.595 | +52,5 | 53 % |
| 18/11 | +914 | +45,0 | 54 % |

**Critério de aprovação:** positiva em ≥ 4 das próximas 5 sessões.

**O que ainda falta:** teste em regime diferente (dia lateral sem tendência,
abertura com gap). As duas sessões testadas tinham tendência definida.

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
