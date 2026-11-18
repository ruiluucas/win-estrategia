"""Grade alvo x stop — SEM tempo fixo.

Sai por alvo ou por stop, o que vier primeiro. Se nenhum dos dois for tocado
ate o fim dos dados, sai no ultimo preco disponivel (e isso e reportado).

Uma posicao por vez.

Uso:
    python grade_alvo_stop.py 2026-11-16
    python grade_alvo_stop.py 2026-11-16 --contra
"""
import sys

import numpy as np
import pandas as pd

import db
import analise_a7 as a7

CUSTO = 7.5
ALVOS = [30, 50, 75, 100, 150, 200, 300]
STOPS = [15, 20, 30, 40, 50, 75]


def carrega(dia):
    bk = db.carrega_book(dia)
    tk = db.carrega_tick(dia)
    snaps = db.snaps_do_book(bk)
    z = a7.zonas_expansivas(snaps)
    ev = a7.desfechos(snaps, a7.episodios(bk, tk, z))
    return snaps, ev.sort_values('t_fim').reset_index(drop=True)


def simula(snaps, ev, alvo, stop, contra=False):
    """Sai por alvo ou stop. Uma posicao por vez."""
    mts = snaps.t.values.astype('datetime64[ns]')
    mid = snaps.mid.values

    def idx(t):
        return int(np.searchsorted(mts, np.datetime64(pd.Timestamp(t)), side='right'))

    trades = []
    livre = None
    for r in ev.itertuples():
        if livre is not None and r.t_fim < livre:
            continue
        i0 = idx(r.t_fim) - 1
        if i0 < 0 or i0 >= len(mid):
            continue
        ent = mid[i0]
        dirn = r.ataque if not contra else -r.ataque

        pnl, saida, t_sai = None, None, None
        for k in range(i0 + 1, len(mid)):
            d = (mid[k] - ent) * dirn
            if d >= alvo:
                pnl, saida = alvo, 'alvo'
                break
            if d <= -stop:
                pnl, saida = -stop, 'stop'
                break
        if pnl is None:
            pnl = (mid[-1] - ent) * dirn
            saida = 'fim'
            t_sai = snaps.t.iloc[-1]
        else:
            t_sai = snaps.t.iloc[k]

        trades.append(dict(t=r.t_fim, pnl=pnl - CUSTO, bruto=pnl, saida=saida))
        livre = t_sai
    return pd.DataFrame(trades)


def main(dia, contra=False):
    snaps, ev = carrega(dia)
    print(f"{dia} | {'CONTRA' if contra else 'A FAVOR'} do agressor | "
          f"{len(ev)} episodios | custo {CUSTO}\n")
    print(f"{'':>7s}" + "".join(f"{a:>9d}" for a in ALVOS) + "     <- ALVO")
    print(f"{'stop':>7s}" + "".join(f"{'─'*9}" for _ in ALVOS))

    melhor = (-1e9, None, None)
    for stop in STOPS:
        linha = f"{stop:7d}"
        for alvo in ALVOS:
            df = simula(snaps, ev, alvo, stop, contra)
            tot = df.pnl.sum()
            linha += f"{tot:+9.0f}"
            if tot > melhor[0]:
                melhor = (tot, alvo, stop)
        print(linha)

    print(f"\nmelhor celula: alvo {melhor[1]} / stop {melhor[2]} = {melhor[0]:+.0f} pts")

    # detalhe da melhor
    df = simula(snaps, ev, melhor[1], melhor[2], contra)
    p = df.pnl.values
    print(f"\n--- detalhe alvo {melhor[1]} / stop {melhor[2]} ---")
    print(f"trades {len(df)} | total {p.sum():+.0f} | mediana {np.median(p):+.1f} "
          f"| acerto {(p>0).sum()}/{len(p)} ({(p>0).mean()*100:.0f}%)")
    print(f"saidas: {df.saida.value_counts().to_dict()}")
    if (df.saida == 'fim').any():
        print(f"  ATENCAO: {(df.saida=='fim').sum()} trades sairam no fim dos dados "
              f"(sem alvo nem stop) — resultado inflado por isso")

    # quantos trades por configuracao (posicao unica faz variar)
    print(f"\n{'alvo/stop':>12s} {'n':>5s} {'total':>9s} {'mediana':>9s} {'acerto':>7s}  saidas")
    for alvo, stop in [(50, 30), (100, 30), (100, 50), (150, 50), (200, 50), (300, 50)]:
        df = simula(snaps, ev, alvo, stop, contra)
        p = df.pnl.values
        s = df.saida.value_counts().to_dict()
        print(f"{alvo:6d}/{stop:<5d} {len(df):5d} {p.sum():+9.0f} {np.median(p):+9.1f} "
              f"{(p>0).mean()*100:6.0f}%  {s}")


if __name__ == '__main__':
    dia = sys.argv[1] if len(sys.argv) > 1 else '2026-11-16'
    main(dia, contra='--contra' in sys.argv)
