import pandas as pd
import numpy as np

# --- DATOS DE EJEMPLO ---
# En un caso real, estos datos se cargarían desde archivos CSV, Excel o una base de datos.
# pd.read_csv('anticipos.csv'), pd.read_excel('gastos.xlsx'), etc.

datos_anticipos = {
    'ID_Empleado': ['E01', 'E02', 'E03', 'E04', 'E01'],
    'Fecha_Anticipo': pd.to_datetime(['2023-10-01', '2023-10-05', '2023-10-10', '2023-11-01', '2023-11-15']),
    'Monto_Anticipado': [500, 300, 700, 450, 600]
}
df_anticipos = pd.DataFrame(datos_anticipos)

datos_gastos = {
    'ID_Empleado': ['E01', 'E01', 'E02', 'E03', 'E03', 'E03', 'E04', 'E05', 'E01', 'E02'],
    'ID_Reporte_Gasto': ['RG01', 'RG01', 'RG02', 'RG03', 'RG03', 'RG04', 'RG05', 'RG06', 'RG07', 'RG02'],
    'Fecha_Gasto': pd.to_datetime(['2023-10-03', '2023-10-04', '2023-10-08', '2023-10-12', '2023-10-12', '2023-10-15',
                                    '2023-11-05', '2023-11-10', '2023-11-18', '2023-10-09']),
    'Categoria': ['Hospedaje', 'Alimentacion', 'Transporte', 'Hospedaje', 'Alimentacion', 'Varios', 'Alimentacion',
                  'Transporte', 'Hospedaje', 'Alimentacion'],
    'Monto_Gasto': [350, 80, 50, 400, 150, 200, 250, 100, 550, 65],
    'Numero_Factura': ['F001', 'F002', 'F003', 'F004', 'F004', 'F005', np.nan, 'F006', 'F007', 'F008'], # Factura duplicada y una sin soporte
    'Proveedor': ['Hotel Central', 'Restaurante Sol', 'Taxi Express', 'Hotel Plaza', 'Restaurante Luna',
                  'Tienda Local', 'Super Gasto', 'Bus Linea', 'Hotel Confort', 'Cafe del Viajero']
}
df_gastos = pd.DataFrame(datos_gastos)

# Política interna de viáticos
politica_viaticos = {
    'Categoria': ['Hospedaje', 'Alimentacion', 'Transporte'],
    'Limite_Diario': [300, 75, 60]
}
df_politicas = pd.DataFrame(politica_viaticos)

# --- INICIO DE LA CAAT ---
def ejecutar_caat(df_anticipos, df_gastos, df_politicas):
    """
    Función principal que ejecuta todas las validaciones de la CAAT.
    """
    print("=====================================================")
    print("==  INICIO DE LA CAAT - AUDITORÍA DE GASTOS DE VIAJE ==")
    print("=====================================================\n")

    # (1) Cruce y Conciliación Anticipo vs. Reporte de Gastos
    evidencia_conciliacion = validar_conciliacion_anticipo_reporte(df_anticipos, df_gastos)
    print("\n--- (1) EVIDENCIA: Conciliación Anticipo vs. Gastos Justificados ---")
    if not evidencia_conciliacion.empty:
        print(evidencia_conciliacion.to_string())
    else:
        print("No se encontraron anticipos para conciliar.")

    # (2) Detección de Duplicidad de Comprobantes
    evidencia_duplicados = detectar_duplicidad_comprobantes(df_gastos)
    print("\n\n--- (2) EVIDENCIA: Detección de Comprobantes Duplicados ---")
    if not evidencia_duplicados.empty:
        print("Se detectaron los siguientes comprobantes duplicados:")
        print(evidencia_duplicados.to_string())
    else:
        print("No se encontraron comprobantes duplicados en la revisión.")

    # (3) Verificación de Soporte Documental
    evidencia_sin_soporte = verificar_soporte_documental(df_gastos)
    print("\n\n--- (3) EVIDENCIA: Gastos Sin Soporte Documental (Factura) ---")
    if not evidencia_sin_soporte.empty:
        print("Se detectaron los siguientes gastos sin número de factura:")
        print(evidencia_sin_soporte.to_string())
    else:
        print("Todos los gastos cuentan con un número de factura registrado.")

    # (4) Validación contra Política de Viáticos
    evidencia_excesos_politica = validar_politica_viaticos(df_gastos, df_politicas)
    print("\n\n--- (4) EVIDENCIA: Incumplimiento de Política de Viáticos (Excesos) ---")
    if not evidencia_excesos_politica.empty:
        print("Se detectaron los siguientes gastos que exceden los límites de la política:")
        print(evidencia_excesos_politica.to_string())
    else:
        print("No se encontraron gastos que excedan la política de viáticos.")

    print("\n\n=====================================================")
    print("==                FIN DE LA CAAT                  ==")
    print("=====================================================")


def validar_conciliacion_anticipo_reporte(df_anticipos, df_gastos):
    """
    Regla 1: Compara el total de gastos justificados por empleado contra el monto
    del anticipo otorgado.
    """
    # Sumar el total de gastos por empleado
    total_gastos_por_empleado = df_gastos.groupby('ID_Empleado')['Monto_Gasto'].sum().reset_index()
    total_gastos_por_empleado.rename(columns={'Monto_Gasto': 'Total_Justificado'}, inplace=True)

    # Sumar el total de anticipos por empleado
    total_anticipos_por_empleado = df_anticipos.groupby('ID_Empleado')['Monto_Anticipado'].sum().reset_index()
    total_anticipos_por_empleado.rename(columns={'Monto_Anticipado': 'Total_Anticipado'}, inplace=True)

    # Unir los dataframes de anticipos y gastos
    df_consolidado = pd.merge(total_anticipos_por_empleado, total_gastos_por_empleado, on='ID_Empleado', how='left')
    df_consolidado['Total_Justificado'].fillna(0, inplace=True) # Rellenar con 0 si un empleado con anticipo no reportó gastos

    # Calcular la diferencia
    df_consolidado['Diferencia'] = df_consolidado['Total_Anticipado'] - df_consolidado['Total_Justificado']

    # Añadir observación
    df_consolidado['Observacion'] = np.where(
        df_consolidado['Diferencia'] < 0,
        'ALERTA: Gasto excede anticipo',
        np.where(
            df_consolidado['Diferencia'] > 0,
            'Pendiente de Reembolso del Empleado',
            'Conciliado'
        )
    )

    return df_consolidado


def detectar_duplicidad_comprobantes(df_gastos):
    """
    Regla 2: Detecta facturas con el mismo número, proveedor y monto.
    """
    # Identificar las filas que son duplicadas basadas en columnas clave
    columnas_clave = ['Numero_Factura', 'Proveedor', 'Monto_Gasto']
    # Se eliminan los NaN para no marcarlos como duplicados
    df_sin_nulos = df_gastos.dropna(subset=columnas_clave)

    duplicados = df_sin_nulos[df_sin_nulos.duplicated(subset=columnas_clave, keep=False)]

    # Ordenar para ver los duplicados juntos
    return duplicados.sort_values(by=columnas_clave)


def verificar_soporte_documental(df_gastos):
    """
    Regla 3: Encuentra todos los gastos que no tienen un número de factura.
    """
    gastos_sin_soporte = df_gastos[df_gastos['Numero_Factura'].isnull()]
    return gastos_sin_soporte


def validar_politica_viaticos(df_gastos, df_politicas):
    """
    Regla 4: Valida que los montos de los gastos no superen los límites
    autorizados en la política interna.
    """
    # Unir gastos con políticas para tener el límite en la misma fila
    df_revision = pd.merge(df_gastos, df_politicas, on='Categoria', how='inner')

    # Filtrar los gastos que exceden el límite
    excesos = df_revision[df_revision['Monto_Gasto'] > df_revision['Limite_Diario']]

    # Calcular por cuánto se excedió
    excesos['Exceso'] = excesos['Monto_Gasto'] - df_revision['Limite_Diario']

    return excesos[['ID_Empleado', 'Fecha_Gasto', 'Categoria', 'Monto_Gasto', 'Limite_Diario', 'Exceso']]


# --- EJECUTAR EL SCRIPT PRINCIPAL ---
if __name__ == "__main__":
    ejecutar_caat(df_anticipos, df_gastos, df_politicas)
