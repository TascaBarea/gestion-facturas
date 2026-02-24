"""
Router de Clasificadores - Versión 2.0
Fecha: 26/01/2026

ORDEN DE CLASIFICACIÓN:
1. Suscripciones extranjeras (MAKE, OPENAI, LOYVERSE, SPOTIFY)
2. AY MADRE LA FRUTA → GARCIA VIVAS JULIO
3. Resto de compras con tarjeta
4. TPV (ABONO TPV, COMISIONES)
5. ALQUILER (BENJAMIN ORTEGA Y JAIME)
6. Resto de transferencias
7. YOIGO (TELEFONOS YOIGO)
8. SOM ENERGIA
9. COMUNIDAD DE VECINOS + ISTA
10. Resto de adeudos/recibos
11. Casos simples (TRASPASO, IMPUESTOS, NÓMINA, INGRESO)
"""

# Importar clasificadores
from clasificadores_mejorados.suscripciones import clasificar_suscripcion
from clasificadores_mejorados.ay_madre import clasificar_ay_madre
from clasificadores_mejorados.alquiler import clasificar_alquiler
from clasificadores_mejorados.telefono_yoigo import clasificar_yoigo
from clasificadores_mejorados.comunidad_ista import clasificar_comunidad_ista

# Clasificadores originales (si existen)
try:
    from banco.clasificadores.tpv import clasificar_tpv
    from banco.clasificadores.transferencia import clasificar_transferencia
    from banco.clasificadores.adeudo_recibo import clasificar_adeudo
    from banco.clasificadores.casos_simples import clasificar_simples
    from banco.clasificadores.energia_som import clasificar_somenergia
    from banco.clasificadores.compra_tarjeta import clasificar_compra_tarjeta
except ImportError:
    # Fallback si no están disponibles
    clasificar_tpv = None
    clasificar_transferencia = None
    clasificar_adeudo = None
    clasificar_simples = None
    clasificar_somenergia = None
    clasificar_compra_tarjeta = None


def clasificar_movimiento(concepto, importe, fecha_valor, fecha_operativa,
                          df_fact, df_fuzzy, df_aux, df_mov, duplicados_control):
    """
    Clasifica un movimiento bancario.
    
    Args:
        concepto: Texto del concepto
        importe: Importe del movimiento
        fecha_valor: Fecha valor
        fecha_operativa: Fecha operativa
        df_fact: DataFrame de facturas
        df_fuzzy: DataFrame de alias proveedores
        df_aux: DataFrame auxiliar
        df_mov: DataFrame de movimientos
        duplicados_control: Control de duplicados
    
    Returns:
        (tipo, detalle, protocolo)
    """
    concepto = str(concepto).strip()
    concepto_upper = concepto.upper()
    
    # ==========================================================================
    # 1. SUSCRIPCIONES EXTRANJERAS (MAKE, OPENAI, LOYVERSE, SPOTIFY)
    # ==========================================================================
    if "COMPRA TARJ" in concepto_upper:
        tipo, detalle, protocolo = clasificar_suscripcion(
            concepto, importe, fecha_valor, df_fact
        )
        if tipo is not None:
            return tipo, detalle, protocolo
    
    # ==========================================================================
    # 2. AY MADRE LA FRUTA → GARCIA VIVAS JULIO
    # ==========================================================================
    if "AY MADRE LA FRUTA" in concepto_upper:
        tipo, detalle, protocolo = clasificar_ay_madre(
            concepto, importe, fecha_valor, df_fact
        )
        if tipo is not None:
            return tipo, detalle, protocolo
    
    # ==========================================================================
    # 3. RESTO DE COMPRAS CON TARJETA
    # ==========================================================================
    if concepto_upper.startswith("COMPRA TARJ") and clasificar_compra_tarjeta:
        tipo, detalle, protocolo = clasificar_compra_tarjeta(
            concepto, importe, fecha_valor, fecha_operativa,
            df_fact, df_fuzzy, df_aux, df_mov
        )
        if tipo is not None:
            return tipo, detalle, protocolo
    
    # ==========================================================================
    # 4. TPV (ABONO TPV, COMISIONES)
    # ==========================================================================
    if (concepto_upper.startswith("ABONO TPV") or 
        concepto_upper.startswith("COMISIONES")) and clasificar_tpv:
        tipo, detalle, protocolo = clasificar_tpv(concepto, fecha_valor, df_mov)
        if tipo is not None:
            return tipo, detalle, protocolo
    
    # ==========================================================================
    # 5. ALQUILER (BENJAMIN ORTEGA Y JAIME)
    # ==========================================================================
    if "BENJAMIN ORTEGA Y JAIME" in concepto_upper:
        tipo, detalle, protocolo = clasificar_alquiler(
            concepto, importe, fecha_valor, df_fact
        )
        if tipo is not None:
            return tipo, detalle, protocolo
    
    # ==========================================================================
    # 6. RESTO DE TRANSFERENCIAS
    # ==========================================================================
    if concepto_upper.startswith("TRANSFERENCIA A") and clasificar_transferencia:
        tipo, detalle, protocolo = clasificar_transferencia(
            concepto, importe, fecha_valor, fecha_operativa,
            df_fact, df_fuzzy, df_aux, df_mov, duplicados_control
        )
        if tipo is not None:
            return tipo, detalle, protocolo
    
    # ==========================================================================
    # 7. YOIGO (TELEFONOS YOIGO)
    # ==========================================================================
    if "YOIGO" in concepto_upper:
        tipo, detalle, protocolo = clasificar_yoigo(concepto, df_fact)
        if tipo is not None:
            return tipo, detalle, protocolo
    
    # ==========================================================================
    # 8. SOM ENERGIA
    # ==========================================================================
    if "SOM ENERGIA" in concepto_upper and clasificar_somenergia:
        tipo, detalle, protocolo = clasificar_somenergia(concepto, importe, df_fact)
        if tipo is not None:
            return tipo, detalle, protocolo
    
    # ==========================================================================
    # 9. COMUNIDAD DE VECINOS + ISTA
    # ==========================================================================
    if "COM PROP" in concepto_upper or "COMUNIDAD PROP" in concepto_upper:
        tipo, detalle, protocolo = clasificar_comunidad_ista(
            concepto, importe, fecha_valor, df_fact
        )
        if tipo is not None:
            return tipo, detalle, protocolo
    
    # ==========================================================================
    # 10. RESTO DE ADEUDOS/RECIBOS
    # ==========================================================================
    if concepto_upper.startswith("ADEUDO RECIBO") and clasificar_adeudo:
        tipo, detalle, protocolo = clasificar_adeudo(
            concepto, importe, fecha_valor, df_fact, df_fuzzy
        )
        if tipo is not None:
            return tipo, detalle, protocolo
    
    # ==========================================================================
    # 11. CASOS SIMPLES (TRASPASO, IMPUESTOS, NÓMINA, INGRESO)
    # ==========================================================================
    if clasificar_simples:
        tipo, detalle, protocolo = clasificar_simples(concepto)
        if tipo is not None:
            return tipo, detalle, protocolo
    
    # ==========================================================================
    # NO CLASIFICADO
    # ==========================================================================
    return "REVISAR", "No clasificado", "NINGUNO"


def reset_todos_clasificadores():
    """Reinicia el estado de todos los clasificadores."""
    from clasificadores_mejorados.suscripciones import reset_facturas_usadas as reset_suscripciones
    from clasificadores_mejorados.ay_madre import reset_facturas_usadas as reset_ay_madre
    from clasificadores_mejorados.alquiler import reset_facturas_usadas as reset_alquiler
    from clasificadores_mejorados.telefono_yoigo import reset_facturas_usadas as reset_yoigo
    from clasificadores_mejorados.comunidad_ista import reset_facturas_usadas as reset_comunidad
    
    reset_suscripciones()
    reset_ay_madre()
    reset_alquiler()
    reset_yoigo()
    reset_comunidad()
