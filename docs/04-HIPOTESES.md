# 04 — Hipóteses

Todas seguem o formato definido em `03-METODO.md`. Status em 18/11/2026.

Ordem cronológica de criação. As refutadas ficam registradas — não são apagadas.

---

## V1 — OFI clássico (refutada)

`[REFUTADO]`

**DEFINIÇÃO** Order Flow Imbalance de 1 s (Cont, Kukanov & Stoikov, 2014):
soma assinada das mudanças de volume nos melhores níveis, incluindo limites,
mercado e cancelamentos. Alvo: retorno do mid em horizonte fixo.

**MEDIÇÃO** Sessão 16/11, n ≈ 68.304 janelas.

| horizonte | correlação | quintil Q1 → Q5 (executável) |
|---|---:|---:|
| 30 s | −0,022 | — |
| 1 min | −0,019 | −20,6 → −18,0 pts |
| 3 min | +0,002 | — |
| 5 min | +0,014 | todos negativos |

**VEREDITO** Explica 0,05 % da variância. O sinal aparente vai *contra* o
movimento esperado em 30 s–2 min. Todos os quintis negativos depois do custo.

---

## A1 — Absorção (por volume de tick, refutada)

`[REFUTADO]`

**DEFINIÇÃO** Janela de 30 s com volume agressivo no quintil superior **e**
eficiência (`|Δmid| / volume dominante`) no quintil inferior.

**MEDIÇÃO** 16/11 manhã: **2 eventos**. A condição dupla global quase nunca
dispara.

**VEREDITO** A definição `[REFUTADO]`-se por escassez: exige duas condições
extremas na mesma janela. Não é que o fenômeno não exista — o detector é que não
funciona. Ver A4.

---

## A2 — Reposição de liquidez

`[HIPOTESE]` — nunca testada.

**DEFINIÇÃO** Volume no nível 0 cai e volta a ≥ 80 % em ≤ 2 s.

**BLOQUEIO** `[DESCONHECIDO]` o schema não distingue cancelamento de execução
(ver `02-DADOS.md`). Sem essa separação, "reposição" não é mensurável.

---

## A3 — Cancelamento defensivo

`[HIPOTESE]` — nunca testada, mesmo bloqueio de A2.

---

## A5a — Exaustão por eficiência (refutada)

`[REFUTADO]`

**DEFINIÇÃO** Janela com eficiência de movimento no quartil superior **e** volume
no quartil inferior. Aposta na reversão.

**MEDIÇÃO** Duas sessões de manhã:

| | 16/11 (n=5) | 17/11 (n=7) |
|---|---:|---:|
| +30 s acerto | 20 % | 29 % |
| +60 s mediana | −190 pts | +50 pts |

**VEREDITO** Resultados opostos entre sessões; n minúsculo. A definição
`[REFUTADO]`-se.

---

## A5b — Resposta de fluxo

`[MEDIDO-n=99] STATUS: REPLICADO EM 2 SESSÕES` — nível **B**

**DEFINIÇÃO** Janela de 10 s com fluxo desbalanceado ≥ 1,5× num lado, seguida
imediatamente por janela com desbalanceamento ≥ 1,5× no lado oposto. Aposta na
direção de **quem respondeu**.

**MEDIÇÃO** Duas sessões de manhã, desfecho em 20 s:

| sequência | 16/11 n | excesso | 17/11 n | excesso |
|---|---:|---:|---:|---:|
| C→V (compra ataca, venda responde) | 16 | **−29,5** | 28 | **−17,8** |
| V→C (venda ataca, compra responde) | 26 | **+21,5** | 29 | **+24,9** |

Controle: −1,9 (16/11) e +2,0 (17/11).

**POR QUE ISSO IMPORTA** `[INFERIDO]` O efeito é **simétrico e do mesmo sinal**
nas duas sessões, apesar de 16/11 ter caído e 17/11 ter subido. Se fosse viés do
dia, o C→V daria positivo em 17/11 — deu −15,7.

**PENDENTE**
- Não foi medido em P&L executável (falta descontar 7,5 pts e simular entrada)
- Magnitude (+21 a +27 pts) é 3–4× o custo, mas o acerto por evento ainda não foi
  calculado
- Falta replicar em sessões com regime diferente (dia lateral)

Reproduzir: `python scripts/analise_a5b.py 2026-11-16 2026-11-17`

---

## A6 — Regiões de tempo (perfil)

`[MEDIDO]` — não é preditor, é descritor de contexto.

**DEFINIÇÃO** Preço acumula tempo enquanto o mid está nele. Região = faixa de
preços contíguos com densidade > 1,5× a esperada.

**MEDIÇÃO** 16/11: 10 regiões, largura mediana **32,5 pts**, custo de memória
**8,2 KB** para 684 preços.

`[MEDIDO]` POC de tempo (172.325) e POC de volume (172.305) coincidiram com
20 pts de diferença na sessão de 16/11 — as duas medidas concordam quando a zona
é real.

**USO** Serve como contexto para os gatilhos (A4/A7), não como sinal próprio.

---

## A7 — Absorção e exaustão definidas pelo book, rotulagem corrigida

`[MEDIDO-n=235]` **Sessão 16/11 apenas. Uma sessão, n=235 episódios únicos.**
O resultado anterior (que indicava "exaustão invertida" com 73 % de acerto) foi
**REFUTADO** — era produto de quatro erros somados. Ver
`06-BECOS-SEM-SAIDA.md` §11.

**DEFINIÇÃO (corrigida em 18/11/2026)**

1. Zonas calculadas em **janela expansível** — no instante `t`, só snapshots
   `≤ t`. (A versão anterior usava a sessão inteira = look-ahead.)
2. Episódio = mid dentro do campo de ±2 ticks de uma borda de zona.
3. `def_queda` = `1 − v_fim / v_ini` do nível da borda, no lado que domina
   (bid ou ask, medido).
4. Classes pelo **sinal** de `def_queda`, sem suposição:
   - **consumo:** `def_queda > +10 %` (volume no nível caiu)
   - **reforço:** `def_queda < −10 %` (volume no nível subiu)
5. Escolha do atacante vem da **fita** (`lado_inferido`), não da posição da borda.
6. Desfecho `passou` medido 60 s **após** o fim do episódio.

**MEDIÇÃO** Controle de 1.000 sorteios (medianas 0/−5/−10/−35 pts em
30/60/120/300 s). 4 testes com Holm.

| classe | desfecho | n | alinhado | p bruto | p Holm |
|---|---|---:|---:|---:|---:|
| consumo | passou | 66 | 51,5 % | 0,902 | 1,000 |
| **consumo** | **segurou** | 98 | **35,7 %** | **0,0061** | **0,0244** |
| reforço | passou | 23 | 69,6 % | 0,093 | 0,279 |
| reforço | segurou | 39 | 43,6 % | 0,522 | 1,000 |

**SENSIBILIDADE** 9 células (densidade 1,25/1,5/2 × janela 30/60/120):
- `consumo/segurou`: 33–37 % em 6 de 9 células — estável, sempre < 50 %
- `reforço/passou`: 57–76 % — varia 19 pts entre células vizinhas → **artefato**

**VEREDITO** `[MEDIDO]` Único efeito que sobrevive a Holm e à sensibilidade é
**negativo**: quando o nível foi **consumido** e o preço **não rompeu**, o lado
agressor acerta a direção em 35,7 % — pior que cara ou coroa.

`[INFERIDO]` Sugere agressor do lado errado nesse contexto, mas `n=98` em
**uma sessão** não sustenta afirmação. **Hipótese, não achado.**

Reproduzir: `python scripts/analise_a7.py 2026-11-16`

---

## A8 — Rompimento (arquivada)

`[REFUTADO]`

**DEFINIÇÃO** Preço atravessa região de tempo forte e continua.

**MEDIÇÃO** 63 combinações de stop × alvo. **Mediana −22,5 pts em todas.**

**VEREDITO** Arquivada em 17/11 por decisão do pesquisador, para focar em
absorção e exaustão. Pode voltar depois que A7 estiver resolvida.

---

## A9 — Frequência do mercado (PRIMEIRA HIPÓTESE REPLICADA)

`[MEDIDO — replicado em 2 sessões independentes]` **Nível B.**

Origem: intuição do pesquisador de que "o preço anda em pernadas de tamanho
parecido". Testada em 18/11.

### Definição

```
1. Zigzag no mid, filtro = 50 pts (oscilação mínima para contar pernada)
2. Amplitudes das pernadas já concluídas (causal: só até o instante t)
3. ALVO = percentil 60 dessas amplitudes
4. STOP = percentil 30 dessas amplitudes
5. Saída por alvo ou stop. Uma posição por vez. Sem tempo fixo.
```

Entrada: episódio A7 (mid na beirada de zona + lado agressor medido pela fita).

### Medição

`[MEDIDO]` Configuração fixa **alvo p60 / stop p30**, sem otimização por sessão:

| sessão | n | total | mediana | acerto |
|---|---:|---:|---:|---:|
| 2026-11-16 | 91 | **+1.595** | **+52,5** | 53 % |
| 2026-11-18 | 48 | **+914** | **+45,0** | 54 % |

`[MEDIDO]` Em 18/11, **as 25 células da grade (alvo p40-p80 × stop p10-p40)
foram positivas**. Em 16/11, 24 de 25.

`[MEDIDO]` Custo de 7,5 pts/trade já descontado. Sensibilidade: resultado
permanece positivo até 12 pts de custo.

### Robustez verificada

| teste | resultado |
|---|---|
| passo de recálculo 30/60/120/240 snapshots | +1.618 / +1.622 / +1.636 / +1.643 → **não depende de look-ahead** |
| custo 3 / 7,5 / 12 pts | +2.050 / +1.622 / +1.195 → **sobrevive** |
| duas sessões independentes | positivo nas duas |

### O que NÃO é robusto

`[MEDIDO]` **O filtro do zigzag é instável.** Análise por hora em 16/11:

| hora | melhor filtro | 
|---|---|
| 10h | 55 |
| 11h | 75 |
| 12h | 50 |

`[MEDIDO]` O pico da grade muda de sessão para sessão (16/11: p60/p20;
18/11: p70/p40). Escolher o melhor de cada dia **é overfitting retroativo**.

`[MEDIDO]` **Concentração alta:** em 18/11, os 5 maiores trades responderam por
58 % do resultado. Sem eles: +512 em 42 trades = 12 pts/trade.

### Veredito

`[INFERIDO]` A **direção** é sólida: alvo em p60-p70 das pernadas com stop largo
(p30-p40) foi positivo nas duas sessões, com acerto 53-54 % e mediana positiva.
Isso sobreviveu a dados novos — é o primeiro achado do projeto a fazer isso.

`[DESCONHECIDO]` Não se sabe se o efeito persiste em outras 3+ sessões, nem se
sobrevive a um regime de mercado diferente (dia lateral, abertura com gap).

**Decisão de método:** usar **alvo p60 / stop p30** fixo — ponto do meio do
plato, não o melhor de nenhuma sessão — e **não tocar** por 5 sessões.

Reproduzir:
```bash
python scripts/grade_frequencia.py 2026-11-16
python scripts/grade_frequencia.py 2026-11-18
python scripts/estuda_frequencia.py 2026-11-16
python scripts/estuda_zigzag.py 2026-11-16
```

---

## A10 — EGARCH escalado por horizonte

`[MEDIDO-n=71]` — **inconclusivo, amostra pequena.**

**DEFINIÇÃO** σ_t do EGARCH(1,1,1) com dist skew-t, expanding window,
reestimado a cada 5 min sobre retornos de 10 s. Alvo e stop em múltiplos de σ,
**escalado pela lei da raiz do tempo**: `σ_horizonte = σ_1passo × √(180/10)`.

**MEDIÇÃO** 16/11: 18 ajustes, γ significativo em 6 de 14, σ de 10 s = 37,6 pts,
fator 4,24× → σ do horizonte mediano **149,7 pts**.

Melhor célula: alvo 2,0σ / stop 2,5σ = +2.088, acerto 77 %, **n=13**.

**VEREDITO** `[MEDIDO]` O escalonamento corrigiu a escala (σ passou de 35 para
150 pts). Mas o stop de 2,5σ ≈ 375 pts bloqueia quase todos os episódios e
sobram 13 trades. **Sem amostra para julgar.**

`[INFERIDO]` Comparado à frequência, o EGARCH é pior em mediana (−39 contra
+17,5) e concentração quando não escalado. Precisa de grade mais fina em σ menor
e mais sessões.

Reproduzir: `python scripts/grade_egarch.py 2026-11-16`
