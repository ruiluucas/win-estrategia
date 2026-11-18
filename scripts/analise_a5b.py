"""A5b — Resposta de fluxo.

Hipotese: quando um lado ataca forte (>= 1,5x o outro) e o lado oposto
responde com forca maior na janela seguinte, o preco vai na direcao de QUEM
RESPONDEU, nao de quem atacou.

Este script existe para ser rodado em cada sessao nova. Resultado de uma sessao
nao decide nada (ver docs/03-METODO.md R4).

Uso:
    python analise_a5b.py 2026-11-16 2026-11-17
"""
import sys

import numpy as np
import pandas as pd

import db

JAN = 10          # janela de 10s
RAZAO = 1.5       # desbalanceamento minimo
FUTURO = 20       # mede o preco 20s depois


def janelas(tk):
    tk = tk.copy()
    tk['w'] = tk.t.dt.floor(f'{JAN}s')
    g = tk.groupby('w').apply(lambda d: pd.Series({
        'compra': d.volume[d.lado_inferido == 1].sum(),
        'venda':  d.volume[d.lado_inferido == -1].sum(),
        'mid':    d.mid.iloc[-1],
    }), include_groups=False).reset_index()
    g['razao'] = g.compra / g.venda.replace(0, np.nan)
    g['tipo'] = np.where(g.razao >= RAZAO, 'C',
                 np.where(g.razao <= 1 / RAZAO, 'V', 'N'))
    return g


def analisa(dia):
    bk = db.carrega_book(dia)
    tk = db.carrega_tick(dia)
    snaps = db.snaps_do_book(bk)

    # mid de cada tick
    mts = snaps.t.values.astype('datetime64[ns]')
    mid = snaps.mid.values
    j = np.clip(np.searchsorted(mts, tk.t.values.astype('datetime64[ns]'), side='right') - 1,
                0, len(mid) - 1)
    tk['mid'] = mid[j]

    g = janelas(tk)
    # movimento 20s depois, usando o mid da janela
    g['mov'] = [db.mid_futuro(snaps, w, FUTURO) - m for w, m in zip(g.w, g.mid)]

    ctl = g.mov.dropna()
    print(f"\n{'='*68}")
    print(f"{dia} | {len(g)} janelas de {JAN}s | controle: movimento medio {ctl.mean():+.1f} "
          f"| mediana {ctl.median():+.1f}")

    # sequencias pico -> resposta oposta
    res = {'C->V': [], 'V->C': []}
    for i in range(len(g) - 1):
        a, b = g.tipo.iloc[i], g.tipo.iloc[i + 1]
        if (a, b) == ('C', 'V'):
            res['C->V'].append(g.mov.iloc[i])
        elif (a, b) == ('V', 'C'):
            res['V->C'].append(g.mov.iloc[i])

    for k, v in res.items():
        v = np.array([x for x in v if not np.isnan(x)])
        if len(v) < 3:
            print(f"  {k}: n={len(v)} (insuficiente)")
            continue
        print(f"  {k}: n={len(v):3d} | mov20s medio {v.mean():+7.1f} | mediana {np.median(v):+7.1f} "
              f"| vs controle {v.mean()-ctl.mean():+7.1f}")

    return g, res


if __name__ == '__main__':
    dias = sys.argv[1:] or ['2026-11-16']
    for d in dias:
        analisa(d)
