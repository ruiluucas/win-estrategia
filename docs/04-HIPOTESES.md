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

## A7 — Absorção e exaustão definidas pelo book (em avaliação)

`[HIPOTESE EM AVALIAÇÃO — resultado não replica]`

**DEFINIÇÃO** Episódio em que o mid entra no campo de ±2 ticks de uma borda de
região. Dentro do episódio mede-se:

- `def_queda` = quanto o volume parado no nível da borda caiu (1 − final/inicial)
- `net` = agressão líquida na direção da borda (compra − venda inferidas)

Classes:
- **EXAUSTÃO:** `def_queda < 15 %` (a parede aguentou firme)
- **ABSORÇÃO:** `def_queda > 30 %` (a parede foi comida mas o preço não passou)

**MEDIÇÃO** Duas sessões de manhã, avanço na direção do ataque:

| classe | 16/11 | 17/11 |
|---|---:|---:|
| exaustão n=17 / n=14, +60 s | 24 % | 36 % |
| exaustão n=17 / n=14, +300 s | 29 % | 50 % |
| absorção n=29 / n=21, +60 s | 41 % | 48 % |
| absorção n=29 / n=21, +300 s | 38 % | 48 % |

**VEREDITO** Tudo próximo de 50 %. **Não replica.** E há um sinal de que a
rotulagem está invertida: na classe "defesa segurou", `def_queda` mediu **−227 %**
e **−213 %**, ou seja o volume *cresceu* — a parede não estava segurando, estava
sendo reabastecida. Ver `06-BECOS-SEM-SAIDA.md` §4.

---

## A8 — Rompimento (arquivada)

`[REFUTADO]`

**DEFINIÇÃO** Preço atravessa região de tempo forte e continua.

**MEDIÇÃO** 63 combinações de stop × alvo. **Mediana −22,5 pts em todas.**

**VEREDITO** Arquivada em 17/11 por decisão do pesquisador, para focar em
absorção e exaustão. Pode voltar depois que A7 estiver resolvida.
