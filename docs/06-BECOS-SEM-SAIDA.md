# 06 — Becos sem saída

Registro do que já falhou. Serve para duas coisas: não repetir, e dar ao revisor
a chance de discordar com base no erro concreto.

Cada entrada tem **o que foi tentado**, **o que deu** e **por que falhou**.

---

## 1. OFI de 1 s como preditor

**Tentado:** Cont/Kukanov/Stoikov aplicado literalmente, correlação com retorno
futuro em 30 s a 5 min.

**Deu:** correlação entre −0,022 e +0,014.

**Por que falhou:** `[INFERIDO]` o efeito que o paper mede é de **explicação
contemporânea** do preço, não de previsão. E o horizonte onde ele é forte está
abaixo do que o polling de 8,5/s alcança.

---

## 2. Definição de absorção por volume de tick agregado

**Tentado:** janela de 30 s com `volume ≥ p95` **e** `eficiência ≤ p5`.

**Deu:** **2 eventos** na sessão inteira.

**Por que falhou:** condição dupla em percentis extremos. Com 317 janelas, a
interseção de dois p5 é da ordem de 0–2 eventos. `[INFERIDO]` O erro foi usar
percentil global num fenômeno que é local — absorção acontece na beirada, onde o
volume natural é menor.

---

## 3. "O dia não permite testar reversão"

**Tentado:** justificar ausência de resultado dizendo que dia de tendência
impede medir reversão.

**Por que é erro:** absorção e exaustão acontecem em qualquer dia. A ausência
era do **detector**, não do fenômeno. Esta entrada existe porque o pesquisador
apontou o erro, corretamente.

---

## 4. Rotulagem invertida em A7

**Tentado:** classificar episódio de beirada como "exaustão" quando o volume no
nível não caía, e "absorção" quando caía.

**Deu:** na classe "exaustão", `def_queda` mediu **−227 %** e **−213 %** — o
volume **cresceu** 2×.

**Por que falhou:** `[INFERIDO]` o rótulo estava invertido. Quando o volume no
nível cresce durante o ataque, a parede não está "aguentando passivamente" — ela
está sendo **reabastecida**. É absorção, não exaustão. A classificação precisa ser
refeita a partir do sinal de `def_queda`, não de uma suposição.

**Status:** pendente de correção. Ver `04-HIPOTESES.md` A7.

---

## 5. Direção derivada da ordem da lista

**Tentado:** simular entrada na "próxima região", com direção = sinal de
(`próxima − atual`).

**Deu:** 9 operações, **todas de compra**, num dia que caiu 3.500 pts.

**Por que falhou:** a lista de regiões era ordenada por preço, então "próxima" era
sempre mais caro. `[INFERIDO]` Direção tem que vir do primeiro toque — de onde o
preço veio.

---

## 6. Média em amostra de 9

**Tentado:** avaliar estratégia pela média de P&L em 9 operações.

**Deu:** média +42,9 pts, mediana −1,7. O maior trade respondia por 90 % do P&L.

**Por que falhou:** com n=9, um único evento move a média mais de 20 %. `[INFERIDO]`
Mediana e "% do P&L do maior evento" deveriam ter sido reportados desde o início.

---

## 7. Normalização global de percentil para comparar horários

**Tentado:** comparar taxa de absorção por hora, normalizando `ρ` sobre a sessão.

**Deu:** 11 h e 14 h apareceram como melhores (3,49 % e 3,61 %).

**Refeito:** normalizando **por hora**, 11 h e 14 h deram **0,00 %**.

**Por que falhou:** `[MEDIDO]` o movimento mediano em 10 s cai de 20 pts (manhã)
para 10 pts (tarde). Com o mesmo volume, `ρ` cai pela metade — não por absorção,
mas porque o mercado desacelerou. Normalizar globalmente faz as horas lentas
concentrarem os valores extremos.

---

## 8. Doctor de timezone duplo

**Tentado:** filtrar por horário no SQL com `at time zone` e depois converter de
novo no pandas.

**Deu:** janelas de 3 h antes do período pretendido. Um `p0` lido como 171.075
quando o preço real era 172.900 (diferença de 1.825 pts).

**Por que falhou:** conversão aplicada duas vezes. `[MEDIDO]` O correto é
converter no SQL e trazer como texto local, sem reconverter.

---

## 9. Exigir `lado_inferido == 2` para venda

**Tentado:** contar vendas agressivas com `lado_inferido = 2`.

**Deu:** 7.640 compras, **0 vendas**, 8.962 "outros".

**Por que falhou:** o valor de venda é **−1**, não 2. Os registros estavam lá o
tempo todo.

---

## 10. Recuo de janela em gráfico de candles

**Tentado:** `getCandles` recuava a janela quando havia menos de 5 candles, para
mercado fechado.

**Deu:** gráfico congelado em 11:42 com o banco gravando normalmente.

**Por que falhou:** o refresh parcial pedia janela de 2 min, que nunca tem 5
candles — o laço então andava 24 min para trás a cada ciclo e reescrevia sempre o
mesmo candle.

---

## 11. "Exaustão invertida" — quatro erros que se somavam

**Data:** 18/11/2026. **Sessão:** 16/11 (única válida).

**O que se acreditava:** que "quando a parede segura firme, o preço recua
77–177 pts" (acerto 73 %), tratado no README como achado estável.

**Status: REFUTADO.** Rebaixado para `[HIPOTESE]` no README.

### Erro 1 — rotulagem invertida

A classe "exaustão" era `def_queda < 15 %` (volume não caiu). Medindo o valor
real: `[MEDIDO]` a mediana de `def_queda` nessa classe foi **−227 %** e
**−213 %** — o volume **cresceu** mais que o dobro.

O rótulo dizia "parede aguentou"; o dado dizia "parede reabastecida". Fenômenos
opostos.

### Erro 2 — look-ahead na definição de zona

`[MEDIDO]` `db.zonas_de` usava a densidade de tempo da **sessão inteira**. No
instante `t` a definição de zona já "sabia" o futuro.

Corrigido: janela **expansível** — no instante `t`, só snapshots `≤ t`.

### Erro 3 — desfecho tautológico

`[MEDIDO]` `passou` era `max_alem > campo` **dentro** do episódio, mas o episódio
termina quando o preço sai do campo. Resultado: `passou = 0` em 4.102 de 4.102.

Corrigido: mede 60 s **depois** do fim do episódio.

### Erro 4 — duplicação de 94 %

`[MEDIDO]` Zonas expansivas reproduzem a mesma borda em 119 instantes e cada
instante re-detectava o mesmo episódio: **4.102 episódios para 235 únicos**.

Corrigido com dedupe por `(borda, t_ini)`.

### O que sobrou após as quatro correções

`[MEDIDO-n=235]` 235 episódios únicos, controle de 1.000 sorteios, 4 testes com
Holm:

| classe | desfecho | n | alinhado | p bruto | p Holm |
|---|---|---:|---:|---:|---:|
| consumo | passou | 66 | 51,5 % | 0,902 | 1,000 |
| **consumo** | **segurou** | 98 | **35,7 %** | **0,0061** | **0,0244** |
| reforço | passou | 23 | 69,6 % | 0,093 | 0,279 |
| reforço | segurou | 39 | 43,6 % | 0,522 | 1,000 |

**Único sobrevivente:** `consumo/segurou` com 35,7 % — **abaixo do acaso**. O
agressor acerta a direção em 1 de cada 3 casos.

### Sensibilidade (9 células: densidade 1,25/1,5/2 × janela 30/60/120)

- **`consumo/segurou`: 33–37 % em 6 de 9 células.** Estável, sempre abaixo de 50 %.
- **`reforço/passou`: 57–76 %.** Varia 19 pontos entre células vizinhas.
  **Artefato** — descartado.

### Conclusão

`[INFERIDO]` O "achado estável" não existia: era produto de quatro erros
somados, o principal sendo a rotulagem invertida.

`[MEDIDO]` O que existe agora é um resultado **negativo e estável** — mas de
**uma sessão**, com n=98. Candidato a hipótese, não achado.

**Reproduzir:** `python scripts/analise_a7.py 2026-11-16`

---

## Padrão comum

`[INFERIDO]` Dez dos onze erros têm a mesma forma: **a definição numérica mede
algo correlato, mas diferente, do fenômeno descrito**. Não foram erros de
aritmética — foram erros de tradução entre a intuição e a métrica.

O único erro de outra natureza é o #8 (timezone), que é puramente técnico.

**Implicação para quem for revisar:** antes de testar uma definição nova, vale
perguntar "se este número estiver alto, o que exatamente aconteceu no mercado?".
Se a resposta não for o fenômeno que se quer medir, a definição está errada antes
de rodar.

**Segunda implicação, aprendida no #11:** uma definição errada pode produzir
resultado *estável entre sessões* e ainda assim ser artefato. Estabilidade não é
prova de validade — só a correção da definição é.
