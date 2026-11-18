# 03 — Método

Este documento define **como qualquer resultado deste projeto deve ser medido**.
Ele existe porque a maior parte do tempo gasto até agora foi em corrigir erros de
método, não em testar hipóteses.

## Regras não negociáveis

### R1 — Controle obrigatório

Nenhum resultado vale sem comparação contra janelas aleatórias da **mesma sessão**
e do **mesmo horário**. Em dia de tendência, qualquer janela de 3 min mostra o
viés do dia; sem controle o efeito é inventado.

`[MEDIDO]` Exemplo real: em 17/11, o movimento mediano do mid em 180 s foi
**+40 pts** numa amostra aleatória. Qualquer padrão medido naquele dia parece
funcionar só por causa disso.

### R2 — Mediana decide

A distribuição de P&L nesta pesquisa é bimodal: poucos acertos grandes, muitos
erros pequenos. A média é dominada por um evento.

`[MEDIDO]` Exemplo real: num teste com 24 trades, média +42,9 e mediana −1,7. O
maior trade sozinho respondia por 90 % do P&L.

**Regra:** se média e mediana divergem, reportar as duas e decidir pela mediana.
Sempre reportar também "quanto do P&L vem do maior evento".

### R3 — Normalizar dentro da janela comparada

Percentis calculados sobre a sessão inteira distorcem comparações entre horários.
`[MEDIDO]` Num teste de recorte horário, o mesmo dado deu 11h como melhor hora
(3,49 %) usando normalização global e como pior (0,00 %) usando normalização por
hora. **As duas normalizações são defensáveis e dão respostas opostas** — logo
nenhuma das duas decide nada com uma sessão.

### R4 — n declarado e respeitado

`n < 30` não decide nada. `n` entre 30 e 100 só detecta efeito grande.

`[MEDIDO]` Para detectar um efeito de magnitude `d` com 80 % de poder e α=5 %:
`n ≈ (2,8 / d)²`. Com desvio de 60 pts e efeito de 15 pts, `n ≈ 125`.

### R5 — Direção vem do dado, nunca da ordem da lista

`[MEDIDO]` Um simulador gerou 9 operações **todas de compra** num dia de queda
porque a direção era derivada de "próxima região na lista", e a lista era
ordenada por preço. A direção tem que vir de onde o preço veio.

### R6 — Congelar antes de testar

Hipótese, alvo, custo, régua de decisão e correção para múltiplas comparações
são definidos **antes** de olhar o resultado. Alterar depois invalida o teste.

### R7 — P&L executável, não mid-to-mid

Toda medição usa entrada e saída que pagam spread e custo. Um resultado que só
existe em mid-to-mid não é reportado como sucesso.

## Estrutura de uma hipótese

Toda hipótese em `04-HIPOTESES.md` segue este formato:

```
ID, nome
DEFINIÇÃO    condição numérica exata que dispara o gatilho
DIREÇÃO      o que se aposta e por quê
ALVO         horizonte e métrica de desfecho
CONTROLE     o que se compara
N ESPERADO   quantos eventos por sessão (estimativa antes de medir)
STATUS       [HIPOTESE] / [MEDIDO-n=X] / [REFUTADO]
```

## Correção para múltiplas comparações

`[LITERATURA]` O protocolo v2 usa Holm-Bonferroni com família de 3 hipóteses,
α = 0,05, o que exige p < 0,0167 para a menor. Nenhuma hipótese tem posição
privilegiada que escape da correção.

`[LITERATURA]` Mesmo com correção, com 2 sessões e busca de parâmetros, um
resultado aparentemente significativo é esperado por construção. Bailey et al.
(DOI 10.21314/jcf.2016.322) mostram que sobre random walk puro, 8.800
configurações produzem Sharpe anualizado de 1,27 com p < 1 % de ser falso —
corretamente diagnosticado pelo CSCV.

**Consequência:** antes de acreditar em qualquer resultado, rodar o diagnóstico de
overfitting (CSCV/PBO) e a deflação do Sharpe.

## Validação temporal

`[LITERATURA]` Li (2026, arXiv:2609.29530) mede, em ruído puro com IC verdadeiro
zero: 5-fold embaralhado reporta IC **+0,318**; contíguo **+0,004**; purgado com
gap=H **+0,000**; walk-forward **+0,017**.

**Regra adotada:**
- **Purged K-fold** serve para *tuning* e comparação de modelos.
- **Walk-forward causal** é o único esquema válido para afirmar performance ao
  vivo.
- O gap/embargo deve ser dimensionado em `H + 2·τ`, onde `H` é o horizonte do
  rótulo e `τ` a escala de dependência. Com rótulos de 5 min e clustering de
  volatilidade, **embargo de poucos segundos é insuficiente**.

## O que conta como desfecho

Duas réguas, sempre as duas:

1. **Taxa de acerto** na direção apostada.
2. **P&L líquido** por evento, já descontado o custo, com mediana e percentual do
   P&L vindo do maior evento.

Um resultado com 60 % de acerto e P&L mediano negativo é um **fracasso**, não um
sucesso — a taxa de acerto só importa junto com o tamanho do ganho versus o do
erro.

## Réguas de decisão

| achado | decisão |
|---|---|
| P&L mediano líquido < 0 em todas as configurações | hipótese refutada |
| P&L positivo mas só com 1 evento carregando | não conclusivo, ampliar amostra |
| P&L positivo e estável entre sessões | candidato — testar em amostra nova |
| efeito some ao controlar por viés de sessão | refutado (era o dia) |
