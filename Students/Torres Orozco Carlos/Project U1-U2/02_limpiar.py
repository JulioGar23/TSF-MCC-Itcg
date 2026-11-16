import re
import sys
from pathlib import Path
import pandas as pd

BASE = Path(__file__).parent
SALIDA = BASE / 'data' / 'interim'
ESTADOS = {'06': 'Colima', '14': 'Jalisco', '16': 'Michoacán', '18': 'Nayarit'}

HOGAR_TEXTO = ['folioviv', 'foliohog', 'ubica_geo', 'upm', 'est_dis',
               'clase_hog', 'est_socio', 'tam_loc', 'educa_jefe', 'sexo_jefe']
HOGAR_NUM = ['factor', 'tot_integ', 'hombres', 'mujeres', 'menores', 'mayores', 'p12_64', 'p65mas',
             'ing_cor', 'edad_jefe', 'gasto_mon', 'salud', 'educacion', 'esparci', 'alimentos',
             'transporte', 'vesti_calz', 'adqui_vehi', 'paq_turist', 'educa_espa']
POB_TEXTO = ['folioviv', 'foliohog', 'numren', 'parentesco', 'sexo']
POB_NUM = ['edad', 'hablaind', 'etnia']


def encontrar_archivos():
    hallados = {}
    for p in BASE.rglob('*.csv'):
        s = str(p).lower()
        if any(x in s for x in ('diccionario', 'estacional', 'data' + '\\interim', 'data/interim', 'auditoria')):
            continue
        for tabla in ('concentradohogar', 'poblacion'):
            if tabla in p.name.lower():
                m = re.findall(r'(20\d{2})', p.name)
                if m:
                    hallados.setdefault((tabla, int(m[-1])), p)
    return hallados


def leer(ruta, texto, num):
    for enc in ('utf-8-sig', 'latin-1'):
        try:
            crudas = pd.read_csv(ruta, nrows=0, encoding=enc).columns
            break
        except UnicodeDecodeError:
            continue
    mapa = {c.strip(): c for c in crudas}
    pedidas = texto + num
    faltan = [c for c in pedidas if c not in mapa]
    df = pd.read_csv(ruta, usecols=[mapa[c] for c in pedidas if c in mapa], dtype=str, encoding=enc)
    df.columns = df.columns.str.strip()
    for c in faltan:
        df[c] = pd.NA
    for c in df.columns:
        df[c] = df[c].str.strip().replace('', pd.NA)
    for c in num:
        antes = df[c].notna().sum()
        df[c] = pd.to_numeric(df[c], errors='coerce')
        perdidos = antes - df[c].notna().sum()
    return df[pedidas]


def limpiar_anio(anio, ruta_h, ruta_p):
    h = leer(ruta_h, HOGAR_TEXTO, HOGAR_NUM)
    h['folioviv'] = h['folioviv'].str.zfill(10)
    h['ubica_geo'] = h['ubica_geo'].str.zfill(5)
    h['educa_jefe'] = h['educa_jefe'].str.zfill(2)
    h['entidad'] = h['ubica_geo'].str[:2]
    h = h[h['entidad'].isin(ESTADOS)].copy()
    h.insert(0, 'anio', anio)

    p = leer(ruta_p, POB_TEXTO, POB_NUM)
    p['folioviv'] = p['folioviv'].str.zfill(10)
    llaves = h[['folioviv', 'foliohog', 'entidad']].drop_duplicates()
    p = p.merge(llaves, on=['folioviv', 'foliohog'], how='inner')
    p.insert(0, 'anio', anio)


    n_h = len(h)
    dup_h = h.duplicated(['folioviv', 'foliohog']).sum()
    dup_p = p.duplicated(['folioviv', 'foliohog', 'numren']).sum()
    n_jefes = (p['parentesco'] == '101').sum()
    pareja = p['parentesco'].isin(['201', '202', '203', '204', '205'])
    d1 = (h['educa_espa'] - (h['educacion'] + h['esparci'])).abs() < 1
    d2 = (h['educa_espa'] - (h['educacion'] + h['esparci'] + h['paq_turist'])).abs() < 1

    SALIDA.mkdir(parents=True, exist_ok=True)
    h.to_csv(SALIDA / f'hogar_{anio}.csv', index=False)
    p.to_csv(SALIDA / f'poblacion_{anio}.csv', index=False)
    return h, p


if __name__ == '__main__':
    archivos = encontrar_archivos()
    anios = sorted({a for _, a in archivos})
    if len(sys.argv) > 1:
        anios = [a for a in anios if str(a) in sys.argv[1:]]
    for a in anios:
        if ('concentradohogar', a) not in archivos or ('poblacion', a) not in archivos:
            continue
        limpiar_anio(a, archivos[('concentradohogar', a)], archivos[('poblacion', a)])
