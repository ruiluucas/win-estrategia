# Instruções para agentes de IA revisores

Você foi convidado a revisar esta pesquisa. Este arquivo diz o que se espera de
você e o que **não** fazer.

## O que o autor quer de você

1. **Criticar o método antes do resultado.** Se a medição está errada, o número
   não importa.
2. **Apontar definição que não corresponde ao fenômeno.** Este é o erro mais
   frequente do projeto (ver `06-BECOS-SEM-SAIDA.md` §padrão comum).
3. **Sugerir controle que falta.** Nenhum resultado vale sem controle da mesma
   sessão e horário.
4. **Dizer o que é conclusivo e o que não é.** A maioria dos números aqui tem
   n < 30 e não decide nada.

## O que NÃO fazer

- **Não trate hipótese como fato.** Cada afirmação tem marcador
  (`00-LEIA-PRIMEIRO.md`). Se você vir afirmação sem marcador, é erro de doc.
- **Não invente paper.** Se citar literatura, traga DOI verificável. Já houve
  citação imprecisa neste projeto (um resumo mais forte que a fonte).
- **Não otimize parâmetros.** Com 2 sessões, qualquer tuning é overfitting.
- **Não confunda ausência de medição com ausência de fenômeno.** O projeto já
  cometeu esse erro e o pesquisador corrigiu.
- **Não sugira deep learning como próximo passo** sem antes explicar como
  resolver o problema de contagem de eventos. Ver `01-PROBLEMA.md`.

## Contexto que você não tem

- O pesquisador humano tem **anos de experiência em mesa** e descreve padrões
  por reconhecimento visual. A descrição dele vem antes das métricas e é a fonte
  das hipóteses. Quando ele diz "aqui aconteceu absorção", naquele instante
  aconteceu algo — o problema é que a métrica ainda não captura o quê.
- O projeto é **de uma pessoa**, em horas noturnas. Escopo estreito é decisão
  consciente.
- **Nada foi validado em produção.** Nenhuma ordem real foi enviada.

## Como reportar sua revisão

Estrutura sugerida:

```
## 1. Erros de método
   (o que invalida um resultado, com referência ao documento)

## 2. Definições suspeitas
   (definição vs. fenômeno descrito)

## 3. Controles que faltam

## 4. O que você consideraria conclusivo hoje
   (provavelmente: quase nada — diga isso se for o caso)

## 5. Próximo experimento que você faria
   (com a definição numérica completa)
```

## Perguntas abertas (do `08-ROADMAP.md`)

1. O limiar "densidade de tempo > 1,5×" para definir região é arbitrário. Existe
   justificativa melhor?
2. Como separar cancelamento de execução sem Level-3?
3. A janela de 60 s do episódio é adequada?
4. Com ~15–30 eventos por sessão, 20 sessões bastam para detectar efeito de
   magnitude realista?
