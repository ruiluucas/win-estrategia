# 01 — O problema

## O que se quer prever

Dado o estado do livro de ofertas e a fita de negócios num instante `t`, prever
a **direção do mid** num horizonte entre **30 segundos e 5 minutos**, e se esse
movimento é **grande o bastante para pagar o custo de execução**.

São duas perguntas distintas e o projeto as trata separadamente:

1. **Direção** — o preço vai subir ou descer?
2. **Tradabilidade** — o movimento é maior que o custo? [HIPOTESE: essa segunda
   pergunta precisa de modelo próprio; não medido ainda]

## Por que 30 s a 5 min

`[MEDIDO-n≈68k]` Correlação do OFI de 1 s com o retorno futuro do mid, sessão de
16/11:

| horizonte | correlação |
|---|---:|
| 30 s | −0,022 |
| 1 min | −0,019 |
| 2 min | −0,013 |
| 3 min | +0,002 |
| 5 min | +0,014 |

`[INFERIDO]` Abaixo de 30 s o fenômeno que se quer capturar não é acessível:
o sistema coleta a ~8,5 snapshots/s (mediana de 100 ms entre leituras), o que
impõe latência mínima de execução incompatível com HFT. Não há colocation nem
acesso direto à API da corretora.

`[INFERIDO]` Acima de 5 min o custo de carregar posição e o risco de notícia
dominam o sinal de microestrutura.

## O custo é a régua

`[MEDIDO]` Spread mediano do WINZ26: **5 pontos**, estável nas três sessões.

`[LITERATURA-EXTERNA, NÃO VERIFICADO NO PROJETO]` Custo de round trip adotado:
**7,5 pontos** (5 de spread + 2,5 de corretagem). Este número veio de nota de
corretagem de outro instrumento e **não foi medido**. A sensibilidade do
resultado a 5, 7,5 e 10 pontos deve ser reportada junto com qualquer conclusão.

**Consequência:** uma hipótese que só funcione em mid-to-mid (sem pagar spread)
não é operacional. Toda medição usa P&L executável.

## O que o autor humano descreve

`[RELATO HUMANO — origem das hipóteses]` O pesquisador tem anos de experiência
em mesa e descreve os seguintes padrões observados visualmente:

- "Quando o preço bate numa região com muita ordem e não passa, e o volume
  agressivo continua entrando, em algum momento ele volta."
- "Quando o preço sobe sem volume, não sustenta."
- "Quando o preço rompe uma região e fica ali em cima sem volume, e depois volta
  pra dentro, geralmente cai."
- "Bloco grande de venda aparece e o preço não cai — aí é porque tem comprador."

`[INFERIDO]` Esses relatos são o **material de origem**. O trabalho técnico é
convertê-los em definições numéricas testáveis. Três tentativas de conversão
falharam e estão registradas em `06-BECOS-SEM-SAIDA.md` — o padrão de falha foi
sempre o mesmo: a definição numérica media algo correlato, mas diferente, do
fenômeno descrito.

## Por que isso pode não funcionar

`[LITERATURA]` Mesfin (2026, arXiv:2605.17724): 944 dias de MNQ, alvo direcional,
walk-forward. Gradient boosting 50,0–50,9 %, LSTM 50,6 %, base rate 51,8 %.
Nenhum passou p<0,05. **Ressalva:** o estudo usou apenas OHLCV de 5 min, sem
book — o espaço de features é outro.

`[LITERATURA]` Briola, Bartolucci & Aste (2025, DOI
10.1080/14697688.2025.2522911): acurácias de 85–90 % em previsão de LOB
coexistem com MCC de 0,05–0,13 porque o classificador é dominado pela classe
"estacionário". **Acurácia alta não é sinal operável.**

`[DESCONHECIDO]` Não foi localizada nenhuma publicação que use book profundo
tick a tick em índice futuro brasileiro com custo modelado. Se existir, este
projeto deveria ser comparado a ela.
