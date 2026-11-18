# LEIA PRIMEIRO — como interpretar este repositório

Este repositório é um **registro de pesquisa em andamento**, não um sistema
pronto. Ele é escrito para ser lido e criticado por outras IAs e por humanos.
Por isso, toda afirmação carrega um marcador de status epistêmico.

## Marcadores de evidência

Toda afirmação factual neste repositório tem um destes marcadores:

| marcador | significado | como foi obtido |
|---|---|---|
| `[MEDIDO]` | número que saiu de execução real sobre os dados | comando reproduzível citado ao lado |
| `[MEDIDO-n=X]` | idem, com tamanho de amostra explícito | — |
| `[INFERIDO]` | conclusão minha a partir de medições | não testado diretamente |
| `[HIPOTESE]` | ideia não testada | — |
| `[REFUTADO]` | foi testado e não se sustentou | medição citada |
| `[LITERATURA]` | vem de paper, com DOI | — |
| `[DESCONHECIDO]` | não sabemos e não temos como saber com os dados atuais | — |

**Regra:** se você (leitor/IA) encontrar afirmação sem marcador, trate como
erro de documentação e sinalize. Isso não deveria acontecer.

## Convenções de número

- **Mediana** é a métrica de decisão. Média só é reportada ao lado da mediana,
  porque a distribuição de P&L nesta pesquisa é dominada por outliers.
- **Acerto** = fração de eventos em que o movimento foi na direção apostada.
- **Controle** = mesma medição em janelas aleatórias da mesma sessão e mesmo
  horário. **Nenhum resultado vale sem controle.** Se não houver controle na
  tabela, o resultado não deve ser usado para decidir nada.
- Sempre que houver n, ele aparece. `n < 30` significa que o número não decide
  nada; está reportado por transparência.

## O que este repositório NÃO afirma

- **Não afirma que existe edge.** Nenhuma hipótese passou do crivo de 20 sessões.
- **Não afirma que absorção/exaustão são falsos.** Afirma que *as implementações
  testadas até agora* não mediram o fenômeno — ver `06-BECOS-SEM-SAIDA.md`.
- **Não contém dados.** O leitor que quiser reproduzir precisa do banco descrito
  em `02-DADOS.md`.

## Contexto que muda a leitura

Três coisas que um revisor precisa saber antes de criticar:

1. **São 2 sessões, não 20.** Tudo aqui é preliminar. O protocolo em
   `03-METODO.md` exige 20 sessões de manhã.
2. **A coleta tem falhas conhecidas.** Duas das três sessões disponíveis estão
   truncadas. Ver `02-DADOS.md` §limitações.
3. **O autor humano tem vivência de mercado** e descreve padrões por
   reconhecimento visual. O trabalho da máquina é transformar essa descrição em
   definição numérica testável — e as primeiras tentativas erraram nisso.

## Histórico de versões do entendimento

| data | o que mudou |
|---|---|
| 16/11/2026 | protocolo v1 congelado (OFI 1s). Refutado no mesmo dia. |
| 16/11/2026 | protocolo v2 congelado (A1/A2/A3). |
| 17/11/2026 | janela de operação restrita a 30 s – 5 min. |
| 17/11/2026 | escopo reduzido para sessão da manhã. |
| 18/11/2026 | recolhimento: absorção e exaustão redefinidas pelo book; rompimento arquivado. |
