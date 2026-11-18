"""Quanto se perde por SAIR TARDE. Mede o custo da saida fixa em 60s.

Para cada trade:
  - pnl em 60s (a regra atual)
  - pnl no MELHOR momento dentro dos 60s (saida perfeita, teto teorico)
  - quanto tempo levou para chegar no melhor
  - pnl se saisse em +10s, +20s, +30s, +45s

Se o gap entre a saida fixa e o melhor momento for grande, o problema e a
regra de saida, nao a entrada.
"""
import sys

import numpy as np
import pandas as pd

import db
import analise_a7 as a7
import simula_a7 as sim

CUSTO = 7.5


def carrega(dia):
    bk = db.carrega_book(dia)
    tk = db.carrega_tick(dia)
    snaps = db.snaps_do_book(bk)
    z = a7.zonas_expansivas(snaps)
    ev = a7.desfechos(snaps, a7.episodios(bk, tk, z)).sort_values('t_fim').reset_index(drop=True)
    return snaps, ev


def main(dia, contra=False, t_max=60):
    snaps, ev = carrega(dia)
    mts = snaps.t.values.astype('datetime64[ns]')
    mid = snaps.mid.values

    def px(t):
        j = np.searchsorted(mts, np.datetime64(pd.Timestamp(t)), side='right') - 1
        return mid[j] if 0 <= j < len(mid) else np.nan

    linhas = []
    livre = None
    for r in ev.itertuples():
        if livre is not None and r.t_fim < livre:
            continue
        ent = px(r.t_fim)
        if np.isnan(ent):
            continue
        dirn = r.ataque if not contra else -r.ataque
        saida = r.t_fim + pd.Timedelta(seconds=t_max)

        # trajetoria dentro dos t_max
        i0 = np.searchsorted(mts, np.datetime64(pd.Timestamp(r.t_fim)), 'right')
        i1 = np.searchsorted(mts, np.datetime64(pd.Timestamp(saida)), 'right')
        seg = mid[i0:min(i1, len(mid))]
        if not len(seg):
            continue
        seg_t = snaps.t.iloc[i0:min(i1, len(snaps))]
        lucro = (seg - ent) * dirn          # em pontos, a favor
        melhor_i = int(np.argmax(lucro))
        melhor = lucro[melhor_i]
        seg_ate_melhor = (seg_t.iloc[melhor_i] - r.t_fim).total_seconds()

        vals = {}
        for s in [10, 20, 30, 45, 60]:
            j = np.searchsorted(mts, np.datetime64(pd.Timestamp(r.t_fim + pd.Timedelta(seconds=s))), 'right') - 1
            vals[s] = (mid[j] - ent) * dirn if 0 <= j < len(mid) else np.nan

        linhas.append(dict(
            t=r.t_fim, ent=ent, final=vals[60],
            melhor=melhor, t_melhor=seg_ate_melhor,
            **{f's{s}': vals[s] for s in [10, 20, 30, 45]},
        ))
        livre = saida

    df = pd.DataFrame(linhas)
    if not len(df):
        print('sem trades'); return

    print(f"{dia} | {'CONTRA' if contra else 'A FAVOR'} | {len(df)} trades | custo {CUSTO}\n")

    print("=== QUANTO SE PERDE POR ESPERAR 60s ===")
    print(f"{'saida em':>10s} {'total':>9s} {'mediana':>9s} {'acerto':>8s}")
    for col, rot in [('s10', '10s'), ('s20', '20s'), ('s30', '30s'),
                     ('s45', '45s'), ('final', '60s')]:
        v = df[col].values - CUSTO
        print(f"{rot:>10s} {v.sum():+9.0f} {np.median(v):+9.1f} {(v>0).mean()*100:7.0f}%")

    v60 = df.final.values - CUSTO
    vmel = df.melhor.values - CUSTO
    print(f"\n--- TETO TEORICO (saida no melhor instante) ---")
    print(f"total 60s fixo     : {v60.sum():+8.0f}")
    print(f"total saida perfeita: {vmel.sum():+8.0f}")
    print(f"perdido por sair tarde: {vmel.sum()-v60.sum():+8.0f} pts "
          f"({(vmel.sum()-v60.sum())/max(abs(v60.sum()),1)*100:.0f}% do resultado atual)")

    print(f"\ntempo mediano ate o melhor ponto: {df.t_melhor.median():.0f}s "
          f"(p25 {df.t_melhor.quantile(.25):.0f}s, p75 {df.t_melhor.quantile(.75):.0f}s)")

    # quantos trades estavam no lucro em algum momento e fecharam no prejuizo
    virou = ((df.melhor > CUSTO) & (df.final < CUSTO)).sum()
    print(f"\ntrades que CHEGARAM a lucrar e fecharam no prejuizo: {virou}/{len(df)} "
          f"({virou/len(df)*100:.0f}%)")
    if virou:
        sub = df[(df.melhor > CUSTO) & (df.final < CUSTO)]
        print(f"  nesses: lucro maximo mediano {sub.melhor.median():+.0f} pts "
              f"| fecharam em {sub.final.median():+.0f} pts")
        print(f"  tempo ate o pico: mediana {sub.t_melhor.median():.0f}s")

    df.to_csv('/tmp/saida_tardia.csv', index=False)
    print("\ndetalhe em /tmp/saida_tardia.csv")


if __name__ == '__main__':
    dia = sys.argv[1] if len(sys.argv) > 1 else '2026-11-16'
    main(dia, contra='--contra' in sys.argv)
