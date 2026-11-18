# 05 — Resultados

Somente números de execução real, com controle ao lado. Ordenado do mais
confiável ao menos confiável.

## Nível de confiança

| nível | critério | quantos resultados |
|---|---|---|
| **A** | replicou em ≥ 2 sessões independentes, com controle | 0 |
| **B** | medido em 1 sessão com n ≥ 100, com controle | 1 |
| **C** | medido com n < 30, ou sem replicação | 5 |
| **D** | observação, não medição | vários |

**Nenhum resultado está no nível A.** Isso é o estado real do projeto.

---

## B1 — Resposta de fluxo (A5b) — **replicado**

`[MEDIDO-n=99]` Duas sessões independentes.

| sequência | 16/11 n | excesso s/ controle | 17/11 n | excesso s/ controle |
|---|---:|---:|---:|---:|
| compra ataca, venda responde | 16 | **−29,5** | 28 | **−17,8** |
| venda ataca, compra responde | 26 | **+21,5** | 29 | **+24,9** |

Controle: **−1,9** (16/11) e **+2,0** (17/11).

`[MEDIDO]` O sinal é o mesmo nos dois dias apesar de 16/11 ter caído e 17/11 ter
subido. **Isso descarta viés de sessão.**

Reproduzir: `python scripts/analise_a5b.py 2026-11-16 2026-11-17`

**Limitação:** desfecho medido em mid, não em P&L executável. Falta descontar
custo e calcular taxa de acerto por evento.

---

## C1 — Perfil de tempo (A6)

`[MEDIDO]` Duas sessões.

| sessão | preços | regiões | largura mediana | memória |
|---|---:|---:|---:|---:|
| 16/11 | 684 | 10 | 32,5 pts | 8,2 KB |
| 17/11 | 519 | 10 | — | — |

`[MEDIDO]` Concordância tempo × volume (16/11): POC tempo 172.325, POC volume
172.305, diferença de **20 pts**.

---

## C2 — Absorção medida evento a evento

`[MEDIDO]` Casos individuais, não estatística.

`[MEDIDO]` 16/11 10:16:17 — 87 contratos comprados, 6 vendidos, mid moveu +5 pts.
Absorção clássica.

`[MEDIDO]` 17/11 12:07:46 — um único tick de **414 contratos de venda** a
172.825, cercado de ticks de 1–2 contratos. O maior do dia (segundo maior: 167).
O preço caiu 45 pts e recuperou; em 3 min estava **+230 pts**.

`[MEDIDO]` 17/11 10:18:20–22 — subida de +30 pts com 7 contratos de compra. Subiu
com **mais venda que compra** no segundo do meio: andou por ausência de oferta.
Desfecho: −85 pts em 13 s.

---

## C3 — Blocos grandes de tick

`[MEDIDO-n=149]` Blocos ≥ 50 contratos, sessão 17/11 inteira.

| | n | movimento médio 180 s |
|---|---:|---:|
| blocos de compra | 65 | −3,4 pts |
| blocos de venda | 84 | **+74,6 pts** |

`[MEDIDO]` Controle por hora: em 9 h, blocos de venda movem +77,5 vs controle
+30,0 (**excesso +47,5**, n=36).

`[MEDIDO]` Blocos ≥ 100 contratos nas 9 h: n=5, excesso **0,0**.

**Leitura:** `[INFERIDO]` o efeito aparente dos blocos é em boa parte o viés
altista do dia. Com n=5 no limiar alto, não há efeito detectável.

---

## C4 — Simulação de rompimento (A8)

`[MEDIDO-n=24]` Sessão 17/11.

| cooldown | trades | acerto | mediana | total |
|---:|---:|---:|---:|---:|
| 0 s | 185 | 16 % | −22,5 | −2.772 |
| 300 s | 39 | 33 % | −26,2 | −11 |
| 600 s | 24 | 33 % | −22,5 | +201 |

`[MEDIDO]` Grade completa 7 alvos × 4 stops = 63 células: **mediana negativa em
todas as 63**.

`[MEDIDO]` 2 entradas de 24 respondiam por todo o resultado positivo. Sem elas,
as outras 22 somavam **−353 pts**.

---

## A7 — Absorção/exaustão nas beiradas, com rotulagem corrigida

`[MEDIDO-n=235]` Sessão 16/11. 235 episódios únicos após remover look-ahead
(zonas expansivas), corrigir rotulagem (sinal de `def_queda`) e dedupe (94 % dos
4.102 episódios originais eram duplicatas).

Controle: 1.000 sorteios — medianas 0 / −5 / −10 / −35 pts em 30/60/120/300 s.

| classe | desfecho | n | alinhado | p bruto | p Holm |
|---|---|---:|---:|---:|---:|
| consumo | passou | 66 | 51,5 % | 0,902 | 1,000 |
| **consumo** | **segurou** | 98 | **35,7 %** | **0,0061** | **0,0244** |
| reforço | passou | 23 | 69,6 % | 0,093 | 0,279 |
| reforço | segurou | 39 | 43,6 % | 0,522 | 1,000 |

4 testes, Holm-Bonferroni aplicado.

**Único sobrevivente:** `consumo/segurou` a **35,7 %** — abaixo do acaso.

Sensibilidade (9 células: densidade 1,25/1,5/2 × janela 30/60/120):
- `consumo/segurou`: **33–37 % em 6 de 9** — estável e sempre < 50 %
- `reforço/passou`: **57–76 %**, varia 19 pts entre células vizinhas — **artefato**

Reproduzir: `python scripts/analise_a7.py 2026-11-16`

**O achado anterior de "exaustão invertida" (73 % de acerto) era produto de
quatro erros somados.** Ver `06-BECOS-SEM-SAIDA.md` §11.

---

## D1 — Observações não estatísticas

`[MEDIDO]` Integridade de forma: 17/11, 13.897 snapshots, **todos** com exatamente
10 níveis.

`[MEDIDO]` Spread mediano 5 pts nas três sessões.

`[MEDIDO]` Book balanceado em 17/11: 14.059 mil contratos no bid, 14.126 mil no
ask.

---

## O que estes resultados permitem concluir

`[INFERIDO]` Nada sobre lucratividade. O único resultado com amostra razoável
(B1) é de uma sessão e não foi replicado. O achado anterior de "exaustão
invertida" em A7 **era artefato de rotulagem** e caiu após correção.

`[INFERIDO]` O que os dados **permitem** afirmar: a infraestrutura de medição
funciona (integridade de 10 níveis, latência sub-segundo, controle reprodutível),
e a descrição visual do pesquisador corresponde a eventos que existem e são
localizáveis nos dados — o problema é a definição numérica, não a observação.
