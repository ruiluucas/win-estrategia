"""Saida antecipada por evento contrario no book.

Ideia: dentro do trade, a cada snapshot olha o book. Se aparece ABSORCAO no lado
oposto ao nosso movimento (volume agressivo contrario alto e o preco nao cede),
sai antes do stop. Isso permite stop curto sem ser estopado por ruido.

Deteccao do evento contrario (por snapshot, causal):
  - agressao liquida dos ultimos SEG_JAN segundos, na direcao contraria
  - |movimento do mid| nessa janela pequeno
  -> ou seja: o outro lado esta atacando e nao consegue andar = defesa

Regras:
  - sai por ALVO, por STOP, ou por EVENTO CONTRARIO (o que vier primeiro)
  - uma posicao por vez

Uso:
    python saida_evento.py 2026-11-16
    python saida_evento.py 2026-11-16 --sem-evento   (baseline, so alvo/stop)
"""
import sys

import numpy as np
import pandas as pd

import db
import analise_a7 as a7

CUSTO = 7.5
JAN_ATR = 20
SEG_JAN = 10           # janela para medir agressao e movimento
MULT_STOP = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
FRACAO_ALVO = [0.5, 0.75, 1.0]
PCT_FORTE = 96
MIN_SEPARACAO = 2


def carrega(dia):
    bk = db.carrega_book(dia)
    tk = db.carrega_tick(dia)
    snaps = db.snaps_do_book(bk)
    z = a7.zonas_expansivas(snaps)
    ev = a7.desfechos(snaps, a7.episodios(bk, tk, z)).sort_values('t_fim').reset_index(drop=True)
    return tk, snaps, ev


def atr_series(snaps, jan=JAN_ATR):
    m = snaps.set_index('t').mid
    return m.rolling(f'{jan}s').apply(lambda s: s.max() - s.min(), raw=True).ffill()


def perfil_volume(tk, snaps, tick=5):
    tk = tk.sort_values('t')
    tp, pp, vv = tk.t.values, (np.round(tk['last'].values / tick) * tick).astype(int), tk.volume.values
    mts = snaps.t.values
    idx = np.searchsorted(tp, mts, side='right')
    perfis, acum, cur = [], {}, 0
    for n in idx:
        while cur < n:
            p = pp[cur]
            acum[p] = acum.get(p, 0.0) + vv[cur]
            cur += 1
        perfis.append(dict(acum))
    return perfis


def paredes(perfil, pct=PCT_FORTE):
    if len(perfil) < 8:
        return np.array([])
    precos = np.array(sorted(perfil))
    vols = np.array([perfil[p] for p in precos])
    corte = np.percentile(vols, pct)
    fortes = precos[vols >= corte]
    if not len(fortes):
        return np.array([])
    grupos, atual = [], [fortes[0]]
    for p in fortes[1:]:
        if p - atual[-1] <= MIN_SEPARACAO * 5:
            atual.append(p)
        else:
            grupos.append(atual); atual = [p]
    grupos.append(atual)
    return np.array([max(g, key=lambda p: perfil[p]) for g in grupos])


def agressao_janela(tk_arr, tk_lado, tk_vol, i_ini, i_fim):
    """Soma de volume comprador e vendedor entre dois indices de tick."""
    if i_fim <= i_ini:
        return 0.0, 0.0
    seg = slice(i_ini, i_fim)
    lados = tk_lado[seg]
    vols = tk_vol[seg]
    comp = float(vols[lados == 1].sum())
    vend = float(vols[lados == -1].sum())
    return comp, vend


def simula(snaps, tk, ev, atr, perfis, m_stop, frac, usar_evento=True,
           contra=False, lim_ratio=1.5, lim_move=0.35):
    """lim_ratio: agressao contraria / favoravel para disparar
       lim_move: movimento permitido na janela, em fracao de ATR
    """
    mts = snaps.t.values.astype('datetime64[ns]')
    mid = snaps.mid.values
    atr_v = atr.values
    tk_t = tk.t.values.astype('datetime64[ns]')
    tk_lado = tk.lado_inferido.values
    tk_vol = tk.volume.values

    def ib(t):
        return int(np.searchsorted(mts, np.datetime64(pd.Timestamp(t)), side='right')) - 1

    def it(t):
        return int(np.searchsorted(tk_t, np.datetime64(pd.Timestamp(t)), side='right'))

    trades = []
    livre = None
    for r in ev.itertuples():
        if livre is not None and r.t_fim < livre:
            continue
        i0 = ib(r.t_fim)
        if i0 < 0 or i0 >= len(mid):
            continue
        ent = mid[i0]
        a = atr_v[i0]
        if not np.isfinite(a) or a <= 0:
            continue
        dirn = r.ataque if not contra else -r.ataque
        stop = m_stop * a

        par = paredes(perfis[i0])
        alvo_pt = None
        if len(par):
            cand = par[par > ent] if dirn > 0 else par[par < ent]
            if len(cand):
                alvo_pt = float(cand.min() if dirn > 0 else cand.max())
        if alvo_pt is None:
            alvo_pt = ent + dirn * 3.0 * a
        dist = abs(alvo_pt - ent) * frac
        dist = min(dist, 8 * a)
        if dist < 0.3 * a:
            continue

        pnl, saida, k_sai = None, None, None
        for k in range(i0 + 1, len(mid)):
            d = (mid[k] - ent) * dirn
            if d >= dist:
                pnl, saida, k_sai = dist, 'alvo', k
                break
            if d <= -stop:
                pnl, saida, k_sai = -stop, 'stop', k
                break

            # ---- evento contrario
            if usar_evento and k % 3 == 0:          # checa a cada ~3 snapshots
                t_k = pd.Timestamp(mts[k])
                j0 = it(t_k - pd.Timedelta(seconds=SEG_JAN))
                j1 = it(t_k)
                comp, vend = agressao_janela(tk_t, tk_lado, tk_vol, j0, j1)
                if comp + vend > 30:
                    # agressao NA DIRECAO CONTRARIA a nossa
                    cont = vend if dirn > 0 else comp
                    fav = comp if dirn > 0 else vend
                    j_ant = max(0, k - int(SEG_JAN / 0.12))
                    mov = abs(mid[k] - mid[j_ant])
                    if cont > lim_ratio * max(fav, 1) and mov < lim_move * a:
                        pnl = (mid[k] - ent) * dirn
                        saida, k_sai = 'evento', k
                        break

        if pnl is None:
            pnl, saida = (mid[-1] - ent) * dirn, 'fim'
            t_sai = snaps.t.iloc[-1]
        else:
            t_sai = pd.Timestamp(mts[k_sai])

        trades.append(dict(t=r.t_fim, pnl=pnl - CUSTO, saida=saida,
                           alvo=dist, stop=stop))
        livre = t_sai
    return pd.DataFrame(trades)


def main(dia, contra=False):
    tk, snaps, ev = carrega(dia)
    atr = atr_series(snaps)
    perfis = perfil_volume(tk, snaps)
    print(f"{dia} | {'CONTRA' if contra else 'A FAVOR'} | {len(ev)} episodios | custo {CUSTO}")
    print(f"ATR mediano {atr.median():.1f} pts | janela de evento {SEG_JAN}s\n")

    for rot, ev_flag in [('SEM evento contrario (baseline)', False),
                         ('COM evento contrario (saida antecipada)', True)]:
        print(f"=== {rot} ===")
        print(f"{'':>6s}" + "".join(f"f={f:<6.2f}" for f in FRACAO_ALVO))
        print(f"{'stop':>6s}" + "".join("─" * 9 for _ in FRACAO_ALVO))
        for s in MULT_STOP:
            linha = f"{s:6.2f}"
            for f in FRACAO_ALVO:
                df = simula(snaps, tk, ev, atr, perfis, s, f, usar_evento=ev_flag, contra=contra)
                linha += f"{df.pnl.sum():+9.0f}" if len(df) else f"{'--':>9s}"
            print(linha)
        print()

    # detalhe comparativo
    print("=== DETALHE: stop 1.0 / frac 0.5 ===")
    for rot, ev_flag in [('sem evento', False), ('com evento', True)]:
        df = simula(snaps, tk, ev, atr, perfis, 1.0, 0.5, usar_evento=ev_flag, contra=contra)
        if not len(df):
            continue
        p = df.pnl.values
        s = df.saida.value_counts().to_dict()
        print(f"{rot:12s}: n={len(df):3d} | total {p.sum():+7.0f} | mediana {np.median(p):+6.1f} "
              f"| acerto {(p>0).mean()*100:3.0f}% | {s}")


if __name__ == '__main__':
    dia = sys.argv[1] if len(sys.argv) > 1 else '2026-11-16'
    main(dia, contra='--contra' in sys.argv)
