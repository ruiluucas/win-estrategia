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

## Padrão comum

`[INFERIDO]` Nove dos dez erros têm a mesma forma: **a definição numérica mede
algo correlato, mas diferente, do fenômeno descrito**. Não foram erros de
aritmética — foram erros de tradução entre a intuição e a métrica.

O único erro de outra natureza é o #8 (timezone), que é puramente técnico.

**Implicação para quem for revisar:** antes de testar uma definição nova, vale
perguntar "se este número estiver alto, o que exatamente aconteceu no mercado?".
Se a resposta não for o fenômeno que se quer medir, a definição está errada antes
de rodar.
