import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent
INTERIM = BASE / 'data' / 'interim'
PROCESSED = BASE / 'data' / 'processed'
EXTERNAL = BASE / 'data' / 'external'

ANIO_BASE = 2024
DEFINICION_PRINCIPAL = 'D_jefe_o_conyuge_autoads'  
JEFE = '101'
PAREJA = ['201', '202', '205']                    
LLAVES = ['anio', 'folioviv', 'foliohog']

ESTADO_NOM = {'06': 'Colima', '14': 'Jalisco', '16': 'Michoacán', '18': 'Nayarit'}
CLASE_HOG = {'1': 'Unipersonal', '2': 'Nuclear', '3': 'Ampliado', '4': 'Compuesto', '5': 'Corresidente'}
EST_SOCIO = {'1': 'Bajo', '2': 'Medio bajo', '3': 'Medio alto', '4': 'Alto'}
TAM_LOC = {'1': '100 mil y más hab.', '2': '15 mil a 99,999 hab.',
           '3': '2,500 a 14,999 hab.', '4': 'Menos de 2,500 hab.'}
EDUCA_JEFE = {
    '01': 'Sin primaria completa', '02': 'Sin primaria completa', '03': 'Sin primaria completa',
    '04': 'Primaria completa', '05': 'Primaria completa',
    '06': 'Secundaria completa', '07': 'Secundaria completa',
    '08': 'Media superior completa', '09': 'Media superior completa',
    '10': 'Superior completa', '11': 'Superior completa',
}


def cargar(prefijo, texto):
    archivos = sorted(INTERIM.glob(f'{prefijo}_*.csv'))
    if not archivos:
        raise SystemExit(f'No hay archivos {prefijo}_*.csv en {INTERIM}. Corre primero 02_limpiar.py')
    return pd.concat([pd.read_csv(a, dtype={c: str for c in texto}) for a in archivos], ignore_index=True)


def decil_ponderado(valores, pesos):
    v, w = valores.to_numpy(), pesos.to_numpy()
    orden = np.argsort(v, kind='mergesort')
    acum = np.cumsum(w[orden]) / w.sum()
    dec = np.clip(np.ceil(acum * 10), 1, 10).astype(int)
    out = np.empty(len(v), dtype=int)
    out[orden] = dec
    return pd.Series(out, index=valores.index)


h = cargar('hogar', ['folioviv', 'foliohog', 'ubica_geo', 'upm', 'est_dis', 'clase_hog',
                     'est_socio', 'tam_loc', 'educa_jefe', 'sexo_jefe', 'entidad'])
p = cargar('poblacion', ['folioviv', 'foliohog', 'numren', 'parentesco', 'sexo', 'entidad'])
h['folioviv'] = h['folioviv'].str.zfill(10)
p['folioviv'] = p['folioviv'].str.zfill(10)

h['estado'] = h['entidad'].map(ESTADO_NOM)
h['clase_hogar'] = h['clase_hog'].map(CLASE_HOG)
h['clase_hogar_agr'] = h['clase_hogar'].replace({'Compuesto': 'Compuesto/corresidente',
                                                 'Corresidente': 'Compuesto/corresidente'})
h['estrato'] = h['est_socio'].map(EST_SOCIO)
h['tam_localidad'] = h['tam_loc'].map(TAM_LOC)
h['escolaridad_jefe'] = h['educa_jefe'].map(EDUCA_JEFE)

h['ocio'] = h['esparci'] + h['paq_turist']
h['transporte_sin_veh'] = h['transporte'] - h['adqui_vehi']
h['gasto_pc'] = h['gasto_mon'] / h['tot_integ']
h['ingreso_pc'] = h['ing_cor'] / h['tot_integ']

h['decil'] = 0
for anio, idx in h.groupby('anio').groups.items():
    g = h.loc[idx]
    h.loc[idx, 'decil'] = decil_ponderado(g['ing_cor'], g['factor'])

p['es_jefe'] = p['parentesco'] == JEFE
p['es_jefe_pareja'] = p['parentesco'].isin([JEFE] + PAREJA)
p['hab'] = p['hablaind'] == 1
p['aut'] = p['etnia'] == 1
DEFS = {
    'A_jefe_habla':             p['es_jefe'] & p['hab'],
    'B_jefe_o_conyuge_habla':   p['es_jefe_pareja'] & p['hab'],
    'C_jefe_autoads':           p['es_jefe'] & p['aut'],
    'D_jefe_o_conyuge_autoads': p['es_jefe_pareja'] & p['aut'],
    'E_cualquiera_habla':       p['hab'],
    'F_cualquiera_autoads':     p['aut'],
}
idx_h = pd.MultiIndex.from_frame(h[LLAVES])
for nombre, mask in DEFS.items():
    ll = pd.MultiIndex.from_frame(p.loc[mask, LLAVES].drop_duplicates())
    h[nombre] = idx_h.isin(ll)
h['hogar_indigena'] = h[DEFINICION_PRINCIPAL]

MONETARIAS = ['ing_cor', 'gasto_mon', 'alimentos', 'vesti_calz', 'salud', 'transporte', 'educacion',
              'esparci', 'paq_turist', 'adqui_vehi', 'ocio', 'transporte_sin_veh', 'gasto_pc', 'ingreso_pc']
ruta_inpc = EXTERNAL / 'inpc_anual.csv'
EXTERNAL.mkdir(parents=True, exist_ok=True)
anios = sorted(h['anio'].unique())
deflactado = False
if ruta_inpc.exists():
    inpc = pd.read_csv(ruta_inpc).set_index('anio')['inpc']
    if all(a in inpc.index and pd.notna(inpc[a]) for a in anios):
        factor_def = (inpc[ANIO_BASE] / inpc).to_dict()
        h['factor_deflactor'] = h['anio'].map(factor_def)
        for c in MONETARIAS:
            h[f'{c}_real'] = h[c] * h['factor_deflactor']
        deflactado = True
if not deflactado:
    if not ruta_inpc.exists():
        pd.DataFrame({'anio': anios, 'inpc': np.nan}).to_csv(ruta_inpc, index=False)

for col in ['estado', 'clase_hogar', 'estrato', 'tam_localidad', 'escolaridad_jefe']:
    n = h[col].isna().sum()

filas = []
for nombre in DEFS:
    for anio, g in h.groupby('anio'):
        s = g[g[nombre]]
        filas.append({'definicion': nombre, 'anio': anio, 'n': len(s),
                      '%pond': round(100 * s['factor'].sum() / g['factor'].sum(), 1)})
res = pd.DataFrame(filas).pivot(index='definicion', columns='anio', values=['n', '%pond'])
pd.set_option('display.width', 250, 'display.max_columns', 40)

PROCESSED.mkdir(parents=True, exist_ok=True)
salida = PROCESSED / 'hogares_2016_2024.csv'
h.to_csv(salida, index=False, encoding='utf-8-sig')
