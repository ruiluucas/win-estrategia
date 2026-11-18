# WIN Microestrutura — Estratégia de Absorção e Exaustão

> **Para agentes de IA revisando este repositório:** comece por
> [`docs/00-LEIA-PRIMEIRO.md`](docs/00-LEIA-PRIMEIRO.md). Ele explica o estado
> epistêmico de cada afirmação. Nem tudo aqui está provado — o que não está
> provado vem marcado como tal.

Pesquisa de microestrutura sobre o mini-índice B3 (WIN) usando book de ofertas
profundo e fita de negócios tick a tick. Objetivo: encontrar gatilhos de
**absorção** e **exaustão** operáveis em horizonte de **30 s a 5 min**, com
P&L líquido de custo de corretagem e spread.

**Escopo atual: sessão da manhã (09:00–12:15 BRT), contrato WINZ26.**

## Estado em uma linha

Nenhuma das definições testadas até agora produziu resultado estatisticamente
conclusivo, **exceto A9 (frequência do mercado)**: alvo no p60 das pernadas, stop
no p30 — positivo em duas sessões independentes, acerto 53-54 %, mediana positiva.
É nível B (falta 3+ sessões para nível A).
Outro achado anterior ("exaustão invertida") foi rastreado até um erro de
rotulagem e **rebaixado a hipótese** — ver `docs/06-BECOS-SEM-SAIDA.md` §11.
Amostra: **2 sessões válidas** (16/11 e 18/11) contra as **20** exigidas.

## Ler em ordem

| documento | conteúdo |
|---|---|
| [`00-LEIA-PRIMEIRO.md`](docs/00-LEIA-PRIMEIRO.md) | como interpretar evidência aqui |
| [`01-PROBLEMA.md`](docs/01-PROBLEMA.md) | o que se quer prever e por quê |
| [`02-DADOS.md`](docs/02-DADOS.md) | schema, coleta, limitações duras |
| [`03-METODO.md`](docs/03-METODO.md) | protocolo, controles, réguas de decisão |
| [`04-HIPOTESES.md`](docs/04-HIPOTESES.md) | todas as hipóteses e seu status |
| [`05-RESULTADOS.md`](docs/05-RESULTADOS.md) | o que foi medido, com números |
| [`06-BECOS-SEM-SAIDA.md`](docs/06-BECOS-SEM-SAIDA.md) | o que já falhou e não repetir |
| [`07-ARQUITETURA.md`](docs/07-ARQUITETURA.md) | separação dados/método/código |
| [`08-ROADMAP.md`](docs/08-ROADMAP.md) | próximo passo objetivo |

## Regra deste repositório

Dados brutos **não entram aqui** (~800 MB por sessão). O repositório carrega
método, código de análise e evidência resumida. Os dados vivem no banco
TimescaleDB local; ver [`02-DADOS.md`](docs/02-DADOS.md).
