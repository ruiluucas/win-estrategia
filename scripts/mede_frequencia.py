"""Mede a FREQUENCIA do mercado: tamanho tipico das pernadas.

Antes de usar como alvo/stop, precisa saber se ela existe e qual e.

Metodo:
  1. Zigzag no mid: marca topos e fundos locais com filtro de tamanho minimo.
  2. Mede a amplitude de cada pernada (topo->fundo, fundo->topo).
  3. Olha a distribuicao: se for concentrada, ha frequencia; se for uniforme,
     nao ha.
  4. Compara com ATR e com a largura das zonas.

Uso:
    python mede_frequencia.py 2026-11-16
    python mede_frequencia.py 2026-11-16 --filtro 40
"""
import sys

import numpy as np
import pandas as pd

import db
import analise_a7 as a7


def zigzag(mid, limiar):
    """Topos e fundos locais separados por pelo menos `limiar` pontos."""
    if len(mid) < 3:
        return []
    pontos = []
    tendencia = 0          # +1 alta, -1 baixa
    extremo_i = 0
    extremo_v = mid[0]

    for i in range(1, len(mid)):
        v = mid[i]
        if tendencia >= 0:
            if v > extremo_v:
                extremo_v, extremo_i = v, i
            elif extremo_v - v >= limiar:
                pontos.append((extremo_i, extremo_v, 'topo'))
                tendencia = -1
                extremo_v, extremo_i = v, i
        if tendencia <= 0:
            if v < extremo_v:
                extremo_v, extremo_i = v, i
            elif v - extremo_v >= limiar:
                pontos.append((extremo_i, extremo_v, 'fundo'))
                tendencia = 1
                extremo_v, extremo_i = v, i
    if pontos:
        pontos.append((extremo_i, extremo_v, 'fim'))
    return pontos


def main(dia, limiar=None):
    bk = db.carrega_book(dia)
    snaps = db.snaps_do_book(bk)
    mid = snaps.mid.values
    print(f"{dia} | {len(snaps)} snapshots | preco {mid.min():.0f}-{mid.max():.0f} "
          f"(amplitude {mid.max()-mid.min():.0f} pts)")

    # ATR de referencia para calibrar o filtro
    m = snaps.set_index('t').mid
    atr20 = m.rolling('20s').apply(lambda s: s.max() - s.min(), raw=True).median()
    print(f"ATR(20s) mediano: {atr20:.0f} pts")

    if limiar is None:
        limiar = max(20, int(atr20 * 0.8))
    print(f"filtro do zigzag: {limiar} pts (ignora oscilacoes menores)\n")

    pts = zigzag(mid, limiar)
    print(f"pontos de virada: {len(pts)}")

    # amplitudes das pernadas
    amps = []
    for i in range(1, len(pts)):
        amps.append(abs(pts[i][1] - pts[i - 1][1]))
    if not amps:
        print('poucas pernadas'); return
    amps = np.array(amps)
    dur = []
    for i in range(1, len(pts)):
        dur.append((snaps.t.iloc[pts[i][0]] - snaps.t.iloc[pts[i - 1][0]]).total_seconds())

    print(f"\n=== AMPLITUDE DAS PERNADAS ({len(amps)} pernadas) ===")
    q = np.percentile(amps, [10, 25, 50, 75, 90])
    print(f"  p10 {q[0]:5.0f} | p25 {q[1]:5.0f} | MEDIANA {q[2]:5.0f} | "
          f"p75 {q[3]:5.0f} | p90 {q[4]:5.0f} pts")
    print(f"  media {amps.mean():.0f} | desvio {amps.std():.0f} | "
          f"coef. variacao {amps.std()/amps.mean()*100:.0f}%")
    print(f"  duracao mediana: {np.median(dur):.0f}s")

    # teste de frequencia: a distribuicao e concentrada?
    cv = amps.std() / amps.mean()
    print(f"\n=== HA FREQUENCIA? ===")
    print(f"  coef. de variacao {cv*100:.0f}%")
    if cv < 0.35:
        print("  -> SIM: pernadas de tamanho parecido (distribuicao concentrada)")
    elif cv < 0.6:
        print("  -> FRACO: ha tendencia central mas muita dispersao")
    else:
        print("  -> NAO: tamanhos muito diversos, nao ha frequencia clara")

    # histograma
    print(f"\n=== DISTRIBUICAO ===")
    bins = [0, 30, 50, 75, 100, 150, 200, 300, 5000]
    hist, _ = np.histogram(amps, bins=bins)
    for i in range(len(bins) - 1):
        if hist[i]:
            lbl = f"{bins[i]}-{bins[i+1]}" if bins[i+1] < 5000 else f">{bins[i]}"
            print(f"  {lbl:10s} {hist[i]:3d} ({hist[i]/len(amps)*100:4.0f}%) "
                  f"{'█' * int(hist[i]/len(amps)*60)}")

    # quantas pernadas cabem por dia
    print(f"\n=== USO PRATICO ===")
    med = np.median(amps)
    print(f"  pernada mediana: {med:.0f} pts")
    print(f"  se alvo = pernada inteira, R:R com stop de 20 pts = {med/20:.1f}")
    print(f"  pernadas por sessao (aprox): {len(amps)}")
    print(f"  pernadas por hora: {len(amps) / ((snaps.t.max()-snaps.t.min()).total_seconds()/3600):.0f}")

    # salva para uso dos outros scripts
    np.save('/tmp/pernadas.npy', amps)
    print(f"\nsalvo /tmp/pernadas.npy")


if __name__ == '__main__':
    dia = sys.argv[1] if len(sys.argv) > 1 else '2026-11-16'
    lim = None
    if '--filtro' in sys.argv:
        lim = int(sys.argv[sys.argv.index('--filtro') + 1])
    main(dia, lim)
