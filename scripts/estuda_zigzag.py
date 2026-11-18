"""Estudo do filtro do zigzag: malha fina + criterio para escolher sem overfit.

Perguntas:
  1. Como o resultado varia de 25 a 100 pts, em passo fino?
  2. Existe um PLATO (varios filtros vizinhos bons) ou so um pico?
  3. O filtro otimo muda conforme a hora do dia? (se muda, e instavel)
  4. Qual filtro escolher SEM olhar o resultado? (regra independente)
  5. O que o zigzag mede com cada filtro (n de pernadas, amplitude)

Uso:
    python estuda_zigzag.py 2026-11-16
"""
import sys

import numpy as np
import pandas as pd

import grade_frequencia as gf
import mede_frequencia as mf

CUSTO = 7.5
ALVO_PCT, STOP_PCT = 60, 20
FILTROS = list(range(25, 105, 5))


def roda(snaps, ev, atr, mid, filtro, contra=False):
    a = gf.amplitudes_causais(mid, filtro=filtro)
    df = gf.simula(snaps, ev, atr, a, ALVO_PCT, STOP_PCT, contra)
    if not len(df):
        return None, a
    p = df.pnl.values
    return dict(n=len(df), total=p.sum(), mediana=np.median(p),
                acerto=(p > 0).mean(), top5=np.sort(p)[::-1][:5].sum()), a


def main(dia, contra=False):
    tk, snaps, ev = gf.carrega(dia)
    atr = gf.atr_series(snaps)
    mid = snaps.mid.values
    print(f"{dia} | {len(ev)} episodios | alvo p{ALVO_PCT} / stop p{STOP_PCT} | custo {CUSTO}")

    # ---- 1) malha fina
    print(f"\n=== MALHA FINA DO FILTRO ===")
    print(f"{'filtro':>7s} {'pernadas':>9s} {'n':>4s} {'total':>9s} {'mediana':>8s} "
          f"{'acerto':>7s} {'sem_top5':>9s}")
    res = []
    for f in FILTROS:
        r, a = roda(snaps, ev, atr, mid, f)
        nmed = np.median([len(x) for x in a if x is not None and len(x)])
        if r is None:
            print(f"{f:7d} {nmed:9.0f} {'--':>4s}")
            continue
        sem = r['total'] - r['top5']
        print(f"{f:7d} {nmed:9.0f} {r['n']:4d} {r['total']:+9.0f} {r['mediana']:+8.1f} "
              f"{r['acerto']*100:6.0f}% {sem:+9.0f}")
        res.append(dict(filtro=f, **r, n_pernadas=nmed, sem_top5=sem))

    r = pd.DataFrame(res)
    if not len(r):
        return

    # ---- 2) plato ou pico
    print(f"\n=== HA PLATO OU PICO? ===")
    melhores = r.nlargest(3, 'total')
    print(f"  top 3 filtros: {list(melhores.filtro.astype(int))} "
          f"com {list(melhores.total.astype(int))}")
    vizinhos_bons = (r.total > 0.5 * r.total.max()).sum()
    med_pos = (r.mediana > 0).sum()
    print(f"  filtros com total > 50% do maximo: {vizinhos_bons}/{len(r)}")
    print(f"  filtros com mediana positiva: {med_pos}/{len(r)}")

    # verifica se o melhor e isolado
    idx_max = r.total.idxmax()
    f_max = r.loc[idx_max, 'filtro']
    viz = r[r.filtro.isin([f_max - 5, f_max + 5])]
    if len(viz) == 2:
        queda = (r.total.max() - viz.total.mean()) / abs(r.total.max()) * 100
        print(f"  vizinhos ({f_max-5:.0f} e {f_max+5:.0f}): media {viz.total.mean():+.0f} "
              f"= queda de {queda:.0f}% em relacao ao pico")
        if queda > 50:
            print("  -> PICO ISOLADO: overfit de parametro")
        elif queda > 25:
            print("  -> PLATO FRACO")
        else:
            print("  -> PLATO: varios vizinhos bons")

    # ---- 3) estabilidade por hora
    print(f"\n=== ESTABILIDADE POR HORA (melhor filtro por hora) ===")
    print(f"{'hora':>5s} {'melhor_f':>9s} {'total':>9s} {'n':>4s} {'2o melhor':>10s}")
    for h in [9, 10, 11, 12]:
        ini = pd.Timestamp(f'{dia} {h:02d}:00:00')
        fim = ini + pd.Timedelta(hours=1)
        e_h = ev[(ev.t_fim >= ini) & (ev.t_fim < fim)]
        if len(e_h) < 10:
            print(f"{h:4d}h {'poucos':>9s}")
            continue
        tot_h = {}
        for f in FILTROS:
            rr, _ = roda(snaps, e_h, atr, mid, f)
            if rr:
                tot_h[f] = rr['total']
        if tot_h:
            ord_ = sorted(tot_h.items(), key=lambda x: -x[1])
            print(f"{h:4d}h {ord_[0][0]:9d} {ord_[0][1]:+9.0f} {len(e_h):4d} "
                  f"{ord_[1][0]:>8d} ({ord_[1][1]:+.0f})")

    # ---- 4) regra sem olhar resultado
    print(f"\n=== ESCOLHA SEM OLHAR O RESULTADO ===")
    # candidato 1: filtro = ATR mediano
    atr_med = atr.median()
    print(f"  ATR mediano {atr_med:.0f} pts -> filtro sugerido {int(atr_med):.0f}")
    # candidato 2: filtro que deixa ~100 pernadas (1 a cada 2 minutos)
    alvo_n = 100
    melhor_n = min(res, key=lambda x: abs(x['n_pernadas'] - alvo_n))
    print(f"  filtro que deixa ~{alvo_n} pernadas: {melhor_n['filtro']:.0f} "
          f"(deixa {melhor_n['n_pernadas']:.0f})")
    # candidato 3: filtro = largura mediana das zonas
    from analise_a7 import zonas_expansivas
    z = zonas_expansivas(snaps)
    if len(z):
        larg = (z.hi - z.lo)
        print(f"  largura mediana das zonas: {larg.median():.0f} pts")
    for nome, f in [('ATR', int(atr_med)), ('100 pernadas', int(melhor_n['filtro']))]:
        rr = r[r.filtro == f]
        if len(rr):
            x = rr.iloc[0]
            print(f"  -> {nome} (filtro {f}): total {x.total:+.0f} | mediana {x.mediana:+.1f} "
                  f"| acerto {x.acerto*100:.0f}%")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '2026-11-16',
         contra='--contra' in sys.argv)
