# Household Spending Patterns in Western Mexico, 2016–2024

Exploratory analysis of how households in Jalisco, Colima, Nayarit, and Michoacán distribute their
spending across six categories (food, clothing and footwear, health, transport, education, leisure),
and how these patterns differ by household composition, income level, indigenous status, and the
education level of the household head.

## Data source

Encuesta Nacional de Ingresos y Gastos de los Hogares (ENIGH), New Series, editions 2016, 2018, 2020,
2022, and 2024. Produced by INEGI (Mexico): https://www.inegi.org.mx/programas/enigh/

The ENIGH Seasonal 2020 is a different survey and is **not** used.

Only two tables per edition are used: `concentradohogar` (one row per household) and `poblacion`
(one row per person).

## How to reproduce

1. Install dependencies: `pip install -r requirements.txt`
2. Download the five ENIGH New Series editions from INEGI (CSV format) and place the unzipped folders
   under `data/raw/` (or in the project root; the scripts find them by file name).
3. Run, in order:
   ```
   python 02_limpiar.py
   python 03_unir.py
   python 05_eda.py
   ```

