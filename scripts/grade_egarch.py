"""Alvo e stop em multiplos de sigma do EGARCH (volatilidade condicional).

Substitui o filtro do zigzag (arbitrario) por sigma_t estimado pelo EGARCH.
A vantagem: sigma_t se adapta ao regime SEM parametro escolhido a mao.

Cuidados aplicados:
  - estimacao EXPANDING WINDOW: a cada ponto, ajusta com dados ate ali.
    Estimar com a sessao inteira seria look-ahead.
  - reestima a cada REEST segundos (EGARCH e caro); entre reestimacoes, usa
    o ultimo sigma disponivel (causal).
  - verifica se o parametro gamma (assimetria) e significativo; se nao,
    usa GARCH simetrico.

Uso:
    python grade_egarch.py 2026-11-16
    python grade_egarch.py 2026-11-16 --contra
"""
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

import db
import analise_a7 as a7

CUSTO = 7.5
REEST = 300              # reestima a cada 5 min
MIN_OBS = 120             # 240 retornos de 30s nao bastam para EGARCH
FREQ = '10s'              # 10s da 3x mais pontos que 30s
MULT = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]


def carrega(dia):
    bk = db.carrega_book(dia)
    tk = db.carrega_tick(dia)
    snaps = db.snaps_do_book(bk)
    z = a7.zonas_expansivas(snaps)
    ev = a7.desfechos(snaps, a7.episodios(bk, tk, z)).sort_values('t_fim').reset_index(drop=True)
    return tk, snaps, ev


def sigma_egarch(snaps, reest=REEST, min_obs=MIN_OBS, freq=FREQ, horizonte=180):
    """sigma_t condicional, expanding window, causal, ESCALADO PELO HORIZONTE.

    CORRECAO IMPORTANTE: o sigma do EGARCH e de 1 passo (freq). Um stop de 1
    sigma de 10s = ~35 pts, e o preco atravessa isso por ruido. Para um trade
    que pode durar `horizonte` segundos, o desvio esperado e
    sigma_1passo * sqrt(horizonte / freq_seg)  — lei da raiz do tempo.

    Com freq=10s e horizonte=180s: fator sqrt(18) = 4.24.
    """
    from arch import arch_model

    m = snaps.set_index('t').mid
    r = m.resample(freq).last().dropna()
    ret = r.pct_change().dropna() * 100          # em %

    sigma_pts = np.full(len(snaps), np.nan)
    info = {'ajustes': 0, 'falhas': 0, 'gamma_sig': 0, 'usou_garch': 0,
            'params': None, 'obs': len(ret), 'sanidade_ruim': 0}

    step = max(1, reest // 10)      # ~50 obs de 10s por bloco de 5 min
    ultimo_sigma = None
    ultimo_i = -step

    for i in range(len(r)):
        if i - ultimo_i >= step and i >= min_obs:
            hist = ret.iloc[:i]
            try:
                am = arch_model(hist, vol='EGARCH', p=1, o=1, q=1, dist='skewt')
                res = am.fit(disp='off', show_warning=False)
                pr = res.params.to_dict()
                gam = pr.get('gamma[1]', np.nan)
                pv = res.pvalues.to_dict().get('gamma[1]', 1.0)
                # sanidade: EGARCH instavel da alpha enorme ou beta ~0
                alpha = pr.get('alpha[1]', 0)
                beta = pr.get('beta[1]', 1)
                instavel = (not np.isfinite(alpha) or abs(alpha) > 3
                            or not np.isfinite(beta) or beta < 0.1)
                if instavel:
                    am = arch_model(hist, vol='GARCH', p=1, q=1, dist='skewt')
                    res = am.fit(disp='off', show_warning=False)
                    info['usou_garch'] += 1
                    info['sanidade_ruim'] += 1
                elif np.isfinite(gam) and pv < 0.10:
                    info['gamma_sig'] += 1

                fc = res.forecast(horizon=1, reindex=False)
                var = float(fc.variance.values[-1, 0])
                if np.isfinite(var) and var > 0:
                    sigma_1p = np.sqrt(var) / 100 * r.iloc[i - 1]
                    # lei da raiz do tempo: sigma do horizonte de trade
                    fator = np.sqrt(horizonte / float(freq.rstrip('smh')))
                    ultimo_sigma = sigma_1p * fator
                    info['ajustes'] += 1
                    info['sigma_1passo'] = round(float(sigma_1p), 2)
                    info['fator_horizonte'] = round(float(fator), 2)
                    info['params'] = {k: round(float(v), 4) for k, v in res.params.items()}
                    info['dist'] = res.model.distribution.__class__.__name__
            except Exception:
                info['falhas'] += 1
            ultimo_i = i

        if ultimo_sigma is not None:
            t0 = r.index[i]
            t1 = t0 + pd.Timedelta(freq)
            mask = ((snaps.t >= t0) & (snaps.t < t1)).values
            sigma_pts[mask] = ultimo_sigma

    validos = np.where(~np.isnan(sigma_pts))[0]
    if len(validos):
        sigma_pts[:validos[0]] = sigma_pts[validos[0]]
        sigma_pts = pd.Series(sigma_pts).ffill().bfill().values
    return sigma_pts, info


def simula(snaps, ev, sigma, m_alvo, m_stop, contra=False):
    mts = snaps.t.values.astype('datetime64[ns]')
    mid = snaps.mid.values

    def i_de(t):
        return int(np.searchsorted(mts, np.datetime64(pd.Timestamp(t)), side='right')) - 1

    trades, livre = [], None
    for r in ev.itertuples():
        if livre is not None and r.t_fim < livre:
            continue
        i0 = i_de(r.t_fim)
        if i0 < 0 or i0 >= len(mid):
            continue
        ent = mid[i0]
        s = sigma[i0]
        if not np.isfinite(s) or s <= 0:
            continue
        dirn = r.ataque if not contra else -r.ataque
        alvo = m_alvo * s
        stop = m_stop * s
        if alvo < 10 or stop < 8:
            continue

        pnl, saida, k = None, None, None
        for k in range(i0 + 1, len(mid)):
            d = (mid[k] - ent) * dirn
            if d >= alvo:
                pnl, saida = alvo, 'alvo'
                break
            if d <= -stop:
                pnl, saida = -stop, 'stop'
                break
        if pnl is None:
            pnl, saida = (mid[-1] - ent) * dirn, 'fim'
            t_sai = snaps.t.iloc[-1]
        else:
            t_sai = pd.Timestamp(mts[k])
        trades.append(dict(t=r.t_fim, pnl=pnl - CUSTO, saida=saida,
                           alvo=alvo, stop=stop, sigma=s))
        livre = t_sai
    return pd.DataFrame(trades)


def main(dia, contra=False):
    tk, snaps, ev = carrega(dia)
    print(f"{dia} | {'CONTRA' if contra else 'A FAVOR'} | {len(ev)} episodios | custo {CUSTO}")
    print("estimando EGARCH expanding window (a cada 5 min)...")

    sigma, info = sigma_egarch(snaps)
    print(f"  ajustes: {info['ajustes']} | falhas: {info['falhas']}")
    print(f"  gamma significativo em {info['gamma_sig']} | GARCH simetrico em {info['usou_garch']}")
    if 'sigma_1passo' in info:
        print(f"  sigma 1 passo (10s): {info['sigma_1passo']} pts | "
              f"fator horizonte: {info['fator_horizonte']}x")
    if info['params']:
        print(f"  ultimos parametros: {info['params']} | dist: {info.get('dist', '?')}")
    print(f"  sigma em pontos: mediana {np.median(sigma):.1f} | "
          f"p10 {np.percentile(sigma, 10):.1f} | p90 {np.percentile(sigma, 90):.1f}\n")

    print(f"{'':>6s}" + "".join(f"a={m:<6.1f}" for m in MULT))
    print(f"{'stop':>6s}" + "".join("─" * 8 for _ in MULT))
    res = []
    for ms in MULT:
        linha = f"{ms:6.1f}"
        for ma in MULT:
            df = simula(snaps, ev, sigma, ma, ms, contra)
            tot = df.pnl.sum() if len(df) else 0
            linha += f"{tot:+8.0f}"
            if len(df):
                res.append(dict(alvo=ma, stop=ms, total=tot,
                                acerto=(df.pnl > 0).mean() * 100,
                                n=len(df), mediana=df.pnl.median(),
                                alvo_pts=df.alvo.median(), stop_pts=df.stop.median()))
        print(linha)

    r = pd.DataFrame(res)
    if not len(r):
        return
    print(f"\n=== TOP 5 POR P&L ===")
    for _, x in r.sort_values('total', ascending=False).head(5).iterrows():
        print(f"  alvo {x.alvo:.1f}s / stop {x.stop:.1f}s → {x.total:+8.0f} "
              f"| acerto {x.acerto:4.0f}% | n={x.n:3.0f} | mediana {x.mediana:+6.1f} "
              f"| {x.alvo_pts:.0f}/{x.stop_pts:.0f} pts")

    print(f"\n=== TOP 5 POR ACERTO (positivo) ===")
    pos = r[r.total > 0].sort_values('acerto', ascending=False).head(5)
    for _, x in pos.iterrows():
        print(f"  alvo {x.alvo:.1f}s / stop {x.stop:.1f}s → acerto {x.acerto:4.0f}% "
              f"| {x.total:+8.0f} | mediana {x.mediana:+6.1f}")

    m = r.sort_values('total', ascending=False).iloc[0]
    df = simula(snaps, ev, sigma, m.alvo, m.stop, contra)
    p = df.pnl.values
    print(f"\n--- detalhe: alvo {m.alvo:.1f}sigma / stop {m.stop:.1f}sigma ---")
    print(f"trades {len(df)} | total {p.sum():+.0f} | mediana {np.median(p):+.1f} "
          f"| acerto {(p>0).sum()}/{len(p)} ({(p>0).mean()*100:.0f}%)")
    print(f"saidas: {df.saida.value_counts().to_dict()}")
    top5 = np.sort(p)[::-1][:5].sum()
    print(f"top5 = {top5/p.sum()*100:.0f}% | sem top5 = {p.sum()-top5:+.0f}")
    print(f"\n{len(r)} celulas, 1 sessao — o maximo e overfit.")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '2026-11-16',
         contra='--contra' in sys.argv)
