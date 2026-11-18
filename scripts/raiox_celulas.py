"""Raio-x das melhores celulas: stop 0.25-0.50 x frac 0.50.

Olha debaixo do capô:
  - distribuicao completa dos P&L (histograma em texto)
  - quanto do lucro vem dos maiores trades
  - curva de patrimonio
  - taxa de stop x taxa de alvo
  - desempenho por hora / por classe de episodio
  - duracao media do trade
"""
import sys

import numpy as np
import pandas as pd

import db
import analise_a7 as a7
import grade_parede as gp

CUSTO = 7.5


def detalha(snaps, tk, ev, atr, perfis, m_stop, frac, rot):
    df = gp.simula(snaps, ev, atr, perfis, m_stop, frac)
    if not len(df):
        print('sem trades'); return df
    p = df.pnl.values
    n = len(p)

    print(f"\n{'='*74}")
    print(f"{rot}")
    print(f"{'='*74}")
    print(f"trades {n} | total {p.sum():+.0f} | mediana {np.median(p):+.1f} | "
          f"media {p.mean():+.1f} | desvio {p.std():.1f}")
    print(f"acerto {(p>0).sum()}/{n} ({(p>0).mean()*100:.0f}%)")
    print(f"saidas: {df.saida.value_counts().to_dict()}")
    print(f"alvo mediano {df.alvo.median():.0f} pts | stop mediano {df.stop.median():.0f} | "
          f"R:R {df.alvo.median()/df.stop.median():.2f}")

    # ---- concentracao
    ordem = np.argsort(p)[::-1]
    top1 = p[ordem[0]]
    top5 = p[ordem[:5]].sum()
    top10 = p[ordem[:10]].sum()
    print(f"\nCONCENTRACAO")
    print(f"  maior trade      {top1:+8.0f} = {top1/p.sum()*100:6.1f}% do total")
    print(f"  top 5 trades     {top5:+8.0f} = {top5/p.sum()*100:6.1f}%")
    print(f"  top 10 trades    {top10:+8.0f} = {top10/p.sum()*100:6.1f}%")
    sem_top5 = p.sum() - top5
    print(f"  total SEM top 5  {sem_top5:+8.0f}  {'(positivo)' if sem_top5>0 else '(NEGATIVO)'}")
    sem_top10 = p.sum() - top10
    print(f"  total SEM top 10 {sem_top10:+8.0f}  {'(positivo)' if sem_top10>0 else '(NEGATIVO)'}")

    # ---- distribuicao
    print(f"\nDISTRIBUICAO")
    for lo, hi, lbl in [(-999, -50, 'perda > 50'), (-50, -20, 'perda 20-50'),
                        (-20, -0.01, 'perda < 20'), (0, 0.01, 'zero'),
                        (0.01, 20, 'ganho < 20'), (20, 50, 'ganho 20-50'),
                        (50, 100, 'ganho 50-100'), (100, 9999, 'ganho > 100')]:
        m = ((p > lo) & (p <= hi)).sum()
        if m:
            barra = '█' * int(m / n * 60)
            print(f"  {lbl:14s} {m:3d} ({m/n*100:4.0f}%) {barra}")

    # ---- evolucao no tempo
    p_cum = np.cumsum(p)
    metade = n // 2
    print(f"\nEVOLUCAO")
    print(f"  1a metade ({metade} trades): {p[:metade].sum():+8.0f}")
    print(f"  2a metade ({n-metade} trades): {p[metade:].sum():+8.0f}")
    print(f"  maximo da curva: {p_cum.max():+8.0f}")
    print(f"  drawdown maximo: {(p_cum - np.maximum.accumulate(p_cum)).min():+8.0f}")
    # sequencia de perdas
    seq = mx = 0
    for x in p:
        seq = seq + 1 if x < 0 else 0
        mx = max(mx, seq)
    print(f"  maior sequencia de perdas: {mx}")

    df['acum'] = p_cum
    return df


def main(dia):
    bk, tk, snaps, ev = gp.carrega(dia)
    atr = gp.atr_series(snaps)
    perfis = gp.perfil_volume(tk, snaps)
    print(f"{dia} | {len(ev)} episodios | ATR mediano {atr.median():.0f} pts")

    d1 = detalha(snaps, tk, ev, atr, perfis, 0.25, 0.50, "stop 0,25x ATR  /  alvo 0,50 da parede")
    d2 = detalha(snaps, tk, ev, atr, perfis, 0.50, 0.50, "stop 0,50x ATR  /  alvo 0,50 da parede")

    # comparacao direta
    if len(d1) and len(d2):
        print(f"\n{'='*74}")
        print("COMPARACAO")
        print(f"{'':>22s} {'stop 0.25':>12s} {'stop 0.50':>12s}")
        print(f"{'trades':>22s} {len(d1):12d} {len(d2):12d}")
        print(f"{'total':>22s} {d1.pnl.sum():+12.0f} {d2.pnl.sum():+12.0f}")
        print(f"{'mediana':>22s} {d1.pnl.median():+12.1f} {d2.pnl.median():+12.1f}")
        print(f"{'acerto':>22s} {(d1.pnl>0).mean()*100:11.0f}% {(d2.pnl>0).mean()*100:11.0f}%")
        print(f"{'stops':>22s} {(d1.saida=='stop').sum():12d} {(d2.saida=='stop').sum():12d}")
        print(f"{'alvos':>22s} {(d1.saida=='alvo').sum():12d} {(d2.saida=='alvo').sum():12d}")
        md1 = (d1.pnl.cumsum() - d1.pnl.cumsum().cummax()).min()
        md2 = (d2.pnl.cumsum() - d2.pnl.cumsum().cummax()).min()
        print(f"{'drawdown max':>22s} {md1:+12.0f} {md2:+12.0f}")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '2026-11-16')
