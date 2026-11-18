"""Estudo completo da estrategia de FREQUENCIA (alvo p60 / stop p20).

Perguntas que responde:
  1. O resultado se concentra em alguma hora do dia?
  2. Quantos trades por hora (frequencia operacional)?
  3. Sensibilidade ao filtro do zigzag (48 e arbitrario?)
  4. Sensibilidade a janela de recalculo das pernadas
  5. O resultado depende de poucos trades?
  6. Qual a sequencia de perdas maxima (risco psicologico)?
  7. Estatistica descritiva completa

Uso:
    python estuda_frequencia.py 2026-11-16
    python estuda_frequencia.py 2026-11-16 --contra
"""
import sys

import numpy as np
import pandas as pd

import grade_frequencia as gf

CUSTO = 7.5


def estat(p):
    n = len(p)
    if not n:
        return {}
    pos, neg = p[p > 0], p[p < 0]
    seq = mx = 0
    for x in p:
        seq = seq + 1 if x < 0 else 0
        mx = max(mx, seq)
    cum = np.cumsum(p)
    return dict(
        n=n, total=p.sum(), mediana=np.median(p), media=p.mean(),
        desvio=p.std(), acerto=(p > 0).mean(),
        ganho_medio=pos.mean() if len(pos) else 0,
        perda_media=neg.mean() if len(neg) else 0,
        maior_g=pos.max() if len(pos) else 0,
        maior_p=neg.min() if len(neg) else 0,
        dd=(cum - np.maximum.accumulate(cum)).min(),
        seq_perdas=mx,
        top5=np.sort(p)[::-1][:5].sum(),
    )


def imprime(rot, s):
    if not s:
        print(f"{rot}: sem trades")
        return
    print(f"\n{rot}")
    print(f"  n={s['n']:3d} total {s['total']:+8.0f} mediana {s['mediana']:+7.1f} "
          f"media {s['media']:+7.1f} desvio {s['desvio']:6.1f}")
    print(f"  acerto {s['acerto']*100:3.0f}% | ganho medio {s['ganho_medio']:+6.1f} | "
          f"perda media {s['perda_media']:+6.1f} | razao "
          f"{abs(s['ganho_medio']/s['perda_media']) if s['perda_media'] else 0:.2f}")
    print(f"  maior ganho {s['maior_g']:+7.0f} | maior perda {s['maior_p']:+7.0f} | "
          f"drawdown {s['dd']:+7.0f} | seq perdas {s['seq_perdas']:2d}")
    print(f"  top5 = {s['top5']:.0f} ({s['top5']/s['total']*100 if s['total'] else 0:4.0f}% do total) | "
          f"sem top5 = {s['total']-s['top5']:+.0f}")


def main(dia, contra=False):
    tk, snaps, ev = gf.carrega(dia)
    atr = gf.atr_series(snaps)
    mid = snaps.mid.values
    amps = gf.amplitudes_causais(mid)

    print(f"{'='*70}\n{dia} | {'CONTRA' if contra else 'A FAVOR'} do agressor | custo {CUSTO}")
    print(f"{'='*70}")

    df = gf.simula(snaps, ev, atr, amps, 60, 20, contra)
    if not len(df):
        print("sem trades"); return
    p = df.pnl.values
    s = estat(p)
    imprime("ESTRATEGIA: alvo p60 das pernadas / stop p20", s)

    # --- por hora
    df['hora'] = pd.to_datetime(df.t).dt.hour
    print(f"\n=== POR HORA ===")
    print(f"{'hora':>5s} {'n':>4s} {'total':>9s} {'mediana':>8s} {'acerto':>7s} {'seq_perdas':>10s}")
    for h, g in df.groupby('hora'):
        gg = estat(g.pnl.values)
        print(f"{h:4d}h {gg['n']:4d} {gg['total']:+9.0f} {gg['mediana']:+8.1f} "
              f"{gg['acerto']*100:6.0f}% {gg['seq_perdas']:10d}")

    # --- sensibilidade ao filtro
    print(f"\n=== SENSIBILIDADE AO FILTRO DO ZIGZAG ===")
    print(f"{'filtro':>7s} {'pernadas':>9s} {'n':>4s} {'total':>9s} {'mediana':>8s} {'acerto':>7s}")
    for f in [30, 40, 48, 60, 80]:
        a2 = gf.amplitudes_causais(mid, filtro=f)
        d2 = gf.simula(snaps, ev, atr, a2, 60, 20, contra)
        if len(d2):
            g2 = estat(d2.pnl.values)
            nmed = np.median([len(x) for x in a2 if x is not None and len(x)])
            print(f"{f:7d} {nmed:9.0f} {g2['n']:4d} {g2['total']:+9.0f} "
                  f"{g2['mediana']:+8.1f} {g2['acerto']*100:6.0f}%")
        else:
            print(f"{f:7d} {'--':>9s} {'--':>4s}")

    # --- sensibilidade ao passo de recalculo
    print(f"\n=== SENSIBILIDADE AO PASSO DE RECALCULO (causalidade) ===")
    print(f"{'passo':>7s} {'n':>4s} {'total':>9s} {'mediana':>8s} {'acerto':>7s}")
    for p_ in [30, 60, 120, 240]:
        a2 = gf.amplitudes_causais(mid, passo=p_)
        d2 = gf.simula(snaps, ev, atr, a2, 60, 20, contra)
        if len(d2):
            g2 = estat(d2.pnl.values)
            print(f"{p_:7d} {g2['n']:4d} {g2['total']:+9.0f} {g2['mediana']:+8.1f} "
                  f"{g2['acerto']*100:6.0f}%")

    # --- sensibilidade ao custo
    print(f"\n=== SENSIBILIDADE AO CUSTO (round trip) ===")
    for c in [3.0, 5.0, 7.5, 10.0, 12.0]:
        d2 = gf.simula(snaps, ev, atr, amps, 60, 20, contra)
        p2 = (d2.pnl + CUSTO - c).values
        g2 = estat(p2)
        print(f"  custo {c:5.1f}: total {g2['total']:+8.0f} | mediana {g2['mediana']:+7.1f} "
              f"| acerto {g2['acerto']*100:3.0f}%")

    # --- distribuicao
    print(f"\n=== DISTRIBUICAO ===")
    for lo, hi, lbl in [(-9999, -100, 'perda > 100'), (-100, -50, 'perda 50-100'),
                        (-50, -20, 'perda 20-50'), (-20, 0, 'perda < 20'),
                        (0, 20, 'ganho < 20'), (20, 50, 'ganho 20-50'),
                        (50, 100, 'ganho 50-100'), (100, 9999, 'ganho > 100')]:
        m = ((p > lo) & (p <= hi)).sum()
        if m:
            print(f"  {lbl:14s} {m:3d} ({m/len(p)*100:4.0f}%) {'█' * int(m/len(p)*60)}")

    print(f"\nATENCAO: 1 sessao. Todos os numeros sao in-sample e nao validam a estrategia.")


if __name__ == '__main__':
    dia = sys.argv[1] if len(sys.argv) > 1 else '2026-11-16'
    main(dia, contra='--contra' in sys.argv)
