"""Conexao somente-leitura com o banco do WIN Book Lab.

TODA analise deste repositorio usa este modulo. Ele e read-only de proposito:
script de analise que escreve no banco e bug.

Uso:
    from db import conexao, carrega_book, carrega_tick, zonas_de
"""
import os

import numpy as np
import pandas as pd
import psycopg2

DB = dict(
    host=os.environ.get('WIN_DB_HOST', '127.0.0.1'),
    port=int(os.environ.get('WIN_DB_PORT', 5434)),
    user=os.environ.get('WIN_DB_USER', 'postgres'),
    dbname=os.environ.get('WIN_DB_NAME', 'mercado'),
    password=os.environ.get('WIN_DB_PASS', 'mercado_local'),
)

TICK_SIZE = 5      # WIN anda de 5 em 5 pontos
CAMPO = 10         # beirada de zona = 2 ticks


def conexao():
    """Conexao somente-leitura. Qualquer INSERT/UPDATE aqui levanta erro."""
    cn = psycopg2.connect(**DB)
    cn.set_session(readonly=True, autocommit=True)
    return cn


def _horario(dia, ini='09:00', fim='12:15'):
    """Filtro de horario local. Devolve a condicao SQL (sem converter de novo)."""
    return (f"ts::date = '{dia}' AND "
            f"(ts AT TIME ZONE 'America/Sao_Paulo')::time BETWEEN '{ini}' AND '{fim}'")


def carrega_book(dia, ini='09:00', fim='12:15'):
    """Book nivel a nivel, com bid/ask/mid repetidos em cada linha.

    IMPORTANTE: o ts volta como TEXTO em horario local, sem timezone. Nao
    reconverta no pandas - isso aplica o deslocamento duas vezes e ja causou
    leitura de janela 3h antes do periodo pretendido.
    """
    q = f"""
      WITH mid AS (
        SELECT ts,
               max(CASE WHEN lado = 2 THEN preco END) AS bid,
               min(CASE WHEN lado = 1 THEN preco END) AS ask
        FROM book WHERE {_horario(dia, ini, fim)}
        GROUP BY ts
      )
      SELECT to_char(b.ts AT TIME ZONE 'America/Sao_Paulo',
                     'YYYY-MM-DD HH24:MI:SS.MS') AS t_local,
             b.preco, b.volume, b.lado,
             m.bid, m.ask, (m.bid + m.ask) / 2.0 AS mid
      FROM book b JOIN mid m ON m.ts = b.ts
      ORDER BY b.ts, b.lado, b.preco"""
    df = pd.read_sql(q, conexao())
    df['t'] = pd.to_datetime(df.t_local)
    return df


def carrega_tick(dia, ini='09:00', fim='12:15'):
    """Fita de negocios. lado_inferido: +1 compra, -1 venda, 0 indeterminado.

    ATENCAO: venda e -1, NAO 2. Usar `== 2` devolve zero vendas.
    """
    q = f"""
      SELECT to_char(ts AT TIME ZONE 'America/Sao_Paulo',
                     'YYYY-MM-DD HH24:MI:SS.MS') AS t_local,
             last, volume, lado_inferido
      FROM tick WHERE {_horario(dia, ini, fim)}
      ORDER BY ts"""
    df = pd.read_sql(q, conexao())
    df['t'] = pd.to_datetime(df.t_local)
    return df


def zonas_de(snaps, tick_size=TICK_SIZE, densidade=1.5, minimo=3):
    """Regioes onde o preco morou.

    snaps: DataFrame com colunas t e mid, um por snapshot (use snaps_do_book).

    Definicao: acumula tempo por preco; zona = faixa contigua de precos cuja
    densidade de tempo excede `densidade` vezes a esperada. Limiar arbitrario -
    ver questao aberta 1 em docs/08-ROADMAP.md.
    """
    preco = np.round(snaps.mid.values / tick_size).astype(int) * tick_size
    dt = snaps.t.diff().dt.total_seconds().fillna(0).clip(upper=1.0).values
    tempo = pd.Series(dt).groupby(preco).sum()
    if not len(tempo):
        return []
    esperado = len(snaps) * 0.1 / len(tempo)
    forte = tempo[tempo > esperado * densidade].sort_index()
    zonas, atual = [], []
    for p in forte.index:
        if atual and p - atual[-1] > tick_size * 2:
            zonas.append(atual)
            atual = []
        atual.append(p)
    if atual:
        zonas.append(atual)
    return [z for z in zonas if len(z) >= minimo]


def snaps_do_book(bk):
    """Colapsa o book nivel a nivel em um registro por snapshot."""
    return bk.groupby('t').agg(
        mid=('mid', 'first'), bid=('bid', 'first'), ask=('ask', 'first')
    ).reset_index()


def mid_futuro(snaps, t, segundos):
    """Mid `segundos` a frente de t. NaN se sair do range."""
    mts = snaps.t.values.astype('datetime64[ns]')
    mid = snaps.mid.values
    alvo = np.datetime64(pd.Timestamp(t) + pd.Timedelta(seconds=segundos))
    j = np.searchsorted(mts, alvo.astype('datetime64[ns]'), side='right') - 1
    if j < 0 or j >= len(mid):
        return np.nan
    return mid[j]
