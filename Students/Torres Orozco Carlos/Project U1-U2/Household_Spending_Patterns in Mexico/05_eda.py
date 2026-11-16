import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path

BASE = Path(__file__).parent
RUTA = BASE / 'data' / 'processed' / 'hogares_2016_2024.csv'
FIG = BASE / 'figuras'
TAB = BASE / 'tablas'

ANIO_CORTE = 2024                 
TRANSPORTE_SIN_VEHICULOS = False  

RUBROS = {
    'Food': 'alimentos',
    'Clothing and footwear': 'vesti_calz',
    'Health': 'salud',
    'Transport': 'transporte_sin_veh' if TRANSPORTE_SIN_VEHICULOS else 'transporte',
    'Education': 'educacion',
    'Leisure': 'ocio',
}
COLORES = {'Food': '#d95f02', 'Clothing and footwear': '#7570b3', 'Health': '#e7298a',
           'Transport': '#1b9e77', 'Education': '#386cb0', 'Leisure': '#e6ab02', 'Other': '#bdbdbd'}
COLOR_ESTADO = {'Colima': '#1b9e77', 'Jalisco': '#386cb0', 'Michoacán': '#d95f02', 'Nayarit': '#e7298a'}
ORDEN_ESCOLARIDAD = ['Less than primary', 'Primary', 'Lower secondary', 'Upper secondary', 'Tertiary']
ORDEN_CLASE = ['Single-person', 'Nuclear', 'Extended', 'Composite/co-resident']
TRAD_ESCOLARIDAD = {'Sin primaria completa': 'Less than primary', 'Primaria completa': 'Primary',
                    'Secundaria completa': 'Lower secondary', 'Media superior completa': 'Upper secondary',
                    'Superior completa': 'Tertiary'}
TRAD_CLASE = {'Unipersonal': 'Single-person', 'Nuclear': 'Nuclear', 'Ampliado': 'Extended',
              'Compuesto/corresidente': 'Composite/co-resident'}

plt.rcParams.update({'figure.dpi': 110, 'axes.spines.top': False, 'axes.spines.right': False,
                     'font.size': 10})

h = pd.read_csv(RUTA, dtype={'folioviv': str, 'ubica_geo': str})
h = h[h['gasto_mon'] > 0].copy()
h['escolaridad_jefe'] = h['escolaridad_jefe'].map(TRAD_ESCOLARIDAD)
h['clase_hogar_agr'] = h['clase_hogar_agr'].map(TRAD_CLASE)
ANIOS = sorted(h['anio'].unique())


def tabla_pct(df, por):
    cols = list(RUBROS.values()) + ['gasto_mon']
    w = df[cols].multiply(df['factor'], axis=0)
    s = w.groupby(df[por]).sum()
    out = pd.DataFrame({lab: 100 * s[col] / s['gasto_mon'] for lab, col in RUBROS.items()})
    out['Other'] = 100 - out.sum(axis=1)
    out['n'] = df.groupby(por).size()
    return out


def pct_con_gasto(df):
    return pd.Series({lab: 100 * (df['factor'] * (df[col] > 0)).sum() / df['factor'].sum()
                      for lab, col in RUBROS.items()})


def barras_apiladas(tab, titulo, ruta):
    fig, ax = plt.subplots(figsize=(9, 0.65 * len(tab) + 2.2))
    izq = np.zeros(len(tab))
    for lab in list(RUBROS) + ['Other']:
        vals = tab[lab].to_numpy()
        ax.barh(range(len(tab)), vals, left=izq, color=COLORES[lab], label=lab)
        for i, (v, l) in enumerate(zip(vals, izq)):
            if v >= 4:
                ax.text(l + v / 2, i, f'{v:.0f}', ha='center', va='center', fontsize=8, color='white')
        izq += vals
    ax.set_yticks(range(len(tab)))
    ax.set_yticklabels([f'{i}  (n={int(n):,})' for i, n in zip(tab.index, tab['n'])])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel('% of monetary current spending')
    ax.set_title(titulo, loc='left', fontweight='bold')
    ax.legend(ncol=7, loc='upper center', bbox_to_anchor=(0.5, -0.18), frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(ruta, bbox_inches='tight')
    plt.close(fig)


def guardar(tab, nombre, carpeta, imprimir):
    tab.round(1).to_csv(carpeta / f'{nombre}.csv', encoding='utf-8-sig')


def figuras_anio(a):
    hc = h[h['anio'] == a]
    imp = (a == ANIO_CORTE)
    df_ = FIG / str(a)
    dt_ = TAB / str(a)
    df_.mkdir(parents=True, exist_ok=True)
    dt_.mkdir(parents=True, exist_ok=True)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    mensual = hc['gasto_mon'] / 3
    a1.hist(np.log10(mensual), bins=50, weights=hc['factor'] / 1e3, color='#386cb0')
    lo, hi = np.percentile(np.log10(mensual), [0.5, 99.5])
    ticks = list(np.arange(np.floor(lo * 2) / 2, hi + 0.5, 0.5))
    a1.set_xlim(ticks[0], ticks[-1])
    a1.set_xticks(ticks)
    a1.set_xticklabels([f'{10 ** t:,.0f}' for t in ticks])
    a1.set_xlabel(f'Monthly household monetary current spending (pesos of {a}, log scale)')
    a1.set_ylabel('Thousands of households')
    a1.set_title(f'Distribution of total spending, {a}', loc='left', fontweight='bold')
    pg = pct_con_gasto(hc)
    a2.barh(pg.index, pg.values, color=[COLORES[k] for k in pg.index])
    a2.invert_yaxis()
    a2.set_xlim(0, 100)
    a2.set_xlabel('% of households with spending > 0 in the quarter')
    a2.set_title('Households spending in each category', loc='left', fontweight='bold')
    for i, v in enumerate(pg.values):
        a2.text(v + 1, i, f'{v:.0f}%', va='center', fontsize=9)
    fig.tight_layout()
    fig.savefig(df_ / 'fig1_distribucion.png', bbox_inches='tight')
    plt.close(fig)
    guardar(pg.to_frame('% households with spending>0'), 'tabla1_hogares_con_gasto', dt_, imp)

    dec = tabla_pct(hc, 'decil')
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for lab in RUBROS:
        ax.plot(dec.index, dec[lab], marker='o', color=COLORES[lab], label=lab)
    ax.set_xticks(dec.index)
    ax.set_xlabel('Current income decile (1 = lowest)')
    ax.set_ylabel('% of monetary current spending')
    ax.set_title(f'Spending structure by income decile, {a}', loc='left', fontweight='bold')
    ax.legend(ncol=6, loc='upper center', bbox_to_anchor=(0.5, -0.15), frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(df_ / 'fig3_decil.png', bbox_inches='tight')
    plt.close(fig)
    guardar(dec, 'tabla3_decil', dt_, imp)

    comp = tabla_pct(hc, 'clase_hogar_agr').loc[ORDEN_CLASE]
    barras_apiladas(comp, f'Spending structure by household composition, {a}', df_ / 'fig4_composicion.png')
    guardar(comp, 'tabla4_composicion', dt_, imp)
    if imp:
        g = hc.assign(x=hc['gasto_pc'] / 3 * hc['factor']).groupby('clase_hogar_agr')[['x', 'factor']].sum()

    esc = tabla_pct(hc, 'escolaridad_jefe').loc[ORDEN_ESCOLARIDAD]
    barras_apiladas(esc, f'Spending structure by education of the household head, {a}', df_ / 'fig5_escolaridad.png')
    guardar(esc, 'tabla5_escolaridad', dt_, imp)
    if imp:
        e = hc.assign(x=hc['edad_jefe'] * hc['factor']).groupby('escolaridad_jefe')[['x', 'factor']].sum()

    ind = tabla_pct(hc, 'hogar_indigena')
    ind.index = ['Indigenous household' if i else 'Non-indigenous' for i in ind.index]
    barras_apiladas(ind, f'Indigenous vs. non-indigenous households, {a} (compare within year only)',
                    df_ / 'fig6_indigena.png')
    guardar(ind, 'tabla6_indigena', dt_, imp)

    est = tabla_pct(hc, 'estado')
    barras_apiladas(est, f'Spending structure by state, {a}', df_ / 'fig7_estado.png')
    guardar(est, 'tabla7_estado', dt_, imp)


def figura_evolucion():
    ev = tabla_pct(h, 'anio')
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for lab in RUBROS:
        ax.plot(ev.index, ev[lab], marker='o', color=COLORES[lab], label=lab)
    ax.axvspan(2019.5, 2020.5, color='grey', alpha=0.15)
    ax.text(2020, ax.get_ylim()[1] * 0.97, '2020\npandemic', ha='center', va='top', fontsize=8, color='grey')
    ax.set_xticks(ev.index)
    ax.set_ylabel('% of monetary current spending')
    ax.set_title('Spending structure, 2016–2024 (four states)', loc='left', fontweight='bold')
    ax.legend(ncol=6, loc='upper center', bbox_to_anchor=(0.5, -0.1), frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / 'fig2_evolucion.png', bbox_inches='tight')
    plt.close(fig)
    guardar(ev, 'tabla2_evolucion', TAB, True)


def figura_lag():
    L = []
    for a in ANIOS:
        t = tabla_pct(h[h['anio'] == a], 'estado')
        for est, lab in itertools.product(t.index, RUBROS):
            L.append({'anio': a, 'estado': est, 'rubro': lab, 'pct': t.loc[est, lab]})
    L = pd.DataFrame(L)
    P = []
    for (est, lab), g in L.groupby(['estado', 'rubro']):
        s = g.set_index('anio')['pct']
        for ant, act in zip(ANIOS[:-1], ANIOS[1:]):
            P.append({'estado': est, 'rubro': lab, 'de': ant, 'a': act, 'x': s[ant], 'y': s[act]})
    P = pd.DataFrame(P)
    P['cambio_pp'] = P['y'] - P['x']

    fig, axs = plt.subplots(2, 3, figsize=(12, 7.5))
    for ax, lab in zip(axs.ravel(), RUBROS):
        d = P[P['rubro'] == lab]
        lim = (min(d['x'].min(), d['y'].min()) * 0.93, max(d['x'].max(), d['y'].max()) * 1.07)
        ax.plot(lim, lim, color='grey', lw=1, ls='--')
        for est, g in d.groupby('estado'):
            con2020 = (g['de'] == 2020) | (g['a'] == 2020)
            ax.scatter(g.loc[~con2020, 'x'], g.loc[~con2020, 'y'], color=COLOR_ESTADO[est], s=38)
            ax.scatter(g.loc[con2020, 'x'], g.loc[con2020, 'y'], facecolors='none',
                       edgecolors=COLOR_ESTADO[est], s=38, linewidths=1.6)
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        ax.set_title(lab, loc='left', fontweight='bold')
        ax.set_xlabel('% in previous edition (t-2 years)')
        ax.set_ylabel('% in current edition (t)')
    asa = [Line2D([], [], marker='o', ls='', color=c, label=e) for e, c in COLOR_ESTADO.items()]
    asa.append(Line2D([], [], marker='o', ls='', markerfacecolor='none', color='black',
                      label='pair including 2020'))
    fig.legend(handles=asa, ncol=5, loc='lower center', frameon=False)
    fig.suptitle('Lag plots: persistence of the spending structure between consecutive editions',
                 x=0.01, ha='left', fontweight='bold')
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    fig.savefig(FIG / 'fig8_lag_plots.png', bbox_inches='tight')
    plt.close(fig)

    resumen = (P.assign(abs_pp=P['cambio_pp'].abs())
                 .groupby('rubro')['abs_pp'].agg(['mean', 'max']).round(2)
                 .rename(columns={'mean': 'mean abs. change (pp)', 'max': 'max abs. change (pp)'}))
    resumen = resumen.loc[list(RUBROS)]
    P.round(2).to_csv(TAB / 'tabla8_lag_pares.csv', index=False, encoding='utf-8-sig')
    guardar(resumen, 'tabla8_lag_resumen', TAB, True)


FIG.mkdir(exist_ok=True)
TAB.mkdir(exist_ok=True)
for a in ANIOS:
    figuras_anio(a)
figura_evolucion()
figura_lag()
