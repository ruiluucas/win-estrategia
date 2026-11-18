# 02 — Dados

## Onde os dados vivem

**Não neste repositório.** O banco é local, TimescaleDB em container Docker.

```
container : mercado-db
endereço  : 127.0.0.1:5434
database  : mercado
role      : postgres        (NÃO existe role "winbook")
senha     : definida em POSTGRES_PASSWORD do container
```

Projeto de coleta: `~/Projetos/win-book-lab`.
Projeto de código de análise: este repositório, pasta `scripts/`.

## Schema

### `book`

| coluna | tipo | observação |
|---|---|---|
| `ts` | timestamptz | timestamp da leitura |
| `symbol` | text | ex. `WINZ26` |
| `preco` | numeric | preço absoluto do nível |
| `volume` | int | contratos parados naquele nível |
| `lado` | smallint | **1 = ask (venda), 2 = bid (compra)** |

Um *snapshot* = todas as linhas com o mesmo `ts`. Cada snapshot tem **10 linhas**
(5 níveis de cada lado). Não existe coluna `nivel`: a posição é derivada da
ordenação do preço.

### `tick`

| coluna | tipo | observação |
|---|---|---|
| `ts` | timestamptz | timestamp |
| `symbol` | text | |
| `time_msc` | bigint | timestamp em milissegundos do MT5 |
| `bid`, `ask`, `last` | double | |
| `volume` | double | contratos do negócio |
| `lado_inferido` | smallint | **+1 = compra agressiva, −1 = venda agressiva, 0 = indeterminado** |

`[MEDIDO]` `lado_inferido` é **inferido**, não fornecido: o MT5 não expõe flag de
agressor nesta instalação. A regra é `last >= ask → compra`, `last <= bid →
venda`. Em 17/11: 7.660 compras, 8.547 vendas, 450 indeterminados.
`[DESCONHECIDO]` A taxa de erro dessa inferência não foi medida.

### `book_delta_v2`

Eventos de mudança entre snapshots consecutivos: `ts, symbol, preco, volume,
delta, evento`. Eventos possíveis: `vol_up`, `vol_down`, `entrou_janela`,
`saiu_janela`.

**Limitação central:** `[DESCONHECIDO]` o schema **não distingue cancelamento de
execução**. Um `vol_down` pode ser ordem cancelada ou ordem executada. Sem isso,
não é possível medir reposição de liquidez com precisão.

## Sessões disponíveis

| data | book | tick | janela | qualidade |
|---|---:|---:|---|---|
| 2026-11-13 | 2.227.480 | 260.622 | 09:20–21:00 | **exploratória** — usada para calibrar, queimada |
| 2026-11-16 | 1.691.830 | 219.863 | 09:58–16:39 | boa, manhã completa |
| 2026-11-17 | 796.985 | 107.450 | 08:35–12:37 | **truncada** — só manhã |

`[MEDIDO]` Taxa típica de coleta: **8,3–9,3 snapshots/s**.
`[MEDIDO]` Latência de aquisição do book: mediana **4,1 ms**, p95 8,5 ms.
`[MEDIDO]` Integridade de forma, 17/11: todos os snapshots com exatamente 10
níveis; gap máximo 1,63 s, p99 207 ms.

## Limitações duras

Estas não são bugs a corrigir — são propriedades do dado. Qualquer análise
precisa respeitá-las.

1. **O book é agregado e anônimo.** Não há ID de ordem. Não é possível reconstruir
   posição na fila, nem detectar spoofing individual. Isso exige Level-3.
2. **Polling perde eventos.** A 8,5 leituras/s, ordens entram, saem e são
   executadas entre duas leituras. O delta calculado é **líquido**, não fluxo.
3. **O feed de profundidade da B3 só popula durante o pregão.** Fora do horário,
   `market_book_get` devolve vazio inclusive para ações. Não é erro de permissão.
4. **Buraco de coleta no meio das sessões.** 16/11 tem um intervalo sem tick às
   16:21; 17/11 tem 11:43–11:58 sem dado. Qualquer janela que atravesse um buraco
   precisa ser descartada.

## Cuidados que já causaram erro

`[MEDIDO]` Erros cometidos nesta pesquisa e que devem ser evitados por quem
reanalisar:

- **Timezone.** Filtrar por `(ts at time zone 'America/Sao_Paulo')::time` no SQL
  e depois reconverter no pandas aplica o deslocamento **duas vezes**. O correto é
  fazer a conversão no SQL e trazer como texto local, sem reconverter.
- **`lado_inferido` não é 1/2.** Venda é `−1`. Usar `== 2` retorna zero vendas.
- **Agregar bid e ask numa cor só** apaga a informação de qual lado defende.
- **Normalizar percentil sobre a sessão inteira** quando se compara horários
  diferentes: horas com menos movimento concentram os valores extremos e o
  detector dispara por construção.
