from tpv import clasificar_tpv
from transferencia import clasificar_transferencia
from adeudo_recibo import clasificar_adeudo
from casos_simples import clasificar_simples
from telefono_yoigo import clasificar_yoigo
from energia_som import clasificar_somenergia
from compra_tarjeta import clasificar_compra_tarjeta


def clasificar_movimiento(concepto, importe, fecha_valor, fecha_operativa,
                          df_fact, df_fuzzy, df_aux, df_mov, duplicados_control):

    concepto = str(concepto).strip()

    if concepto.upper().startswith("COMPRA TARJ."):
        tipo, detalle, protocolo = clasificar_compra_tarjeta(concepto, importe, fecha_valor, fecha_operativa,
                                                             df_fact, df_fuzzy, df_aux, df_mov)
        if tipo is not None:
            return tipo, detalle, protocolo

    if concepto.upper().startswith("ABONO TPV") or concepto.upper().startswith("COMISIONES"):
        tipo, detalle, protocolo = clasificar_tpv(concepto, fecha_valor, df_mov)
        if tipo is not None:
            return tipo, detalle, protocolo

    if concepto.upper().startswith("ABONO TPV") or concepto.upper().startswith("COMISIONES"):
        tipo, detalle, protocolo = clasificar_tpv(concepto, fecha_valor, df_mov)
        if tipo is not None:
            return tipo, detalle, protocolo

    if concepto.upper().startswith("TRANSFERENCIA A"):
        tipo, detalle, protocolo = clasificar_transferencia(concepto, importe, fecha_valor, fecha_operativa,
                                                             df_fact, df_fuzzy, df_mov, duplicados_control)
        if tipo is not None:
            return tipo, detalle, protocolo

    if concepto.upper().startswith("ADEUDO RECIBO"):
        tipo, detalle, protocolo = clasificar_yoigo(concepto, df_fact)
        if tipo is not None:
            return tipo, detalle, protocolo

        tipo, detalle, protocolo = clasificar_somenergia(concepto, importe, df_fact)
        if tipo is not None:
            return tipo, detalle, protocolo

        tipo, detalle, protocolo = clasificar_adeudo(concepto, importe, fecha_valor, df_fact, df_fuzzy)
        if tipo is not None:
            return tipo, detalle, protocolo

    tipo, detalle, protocolo = clasificar_simples(concepto)
    if tipo is not None:
        return tipo, detalle, protocolo

    return "REVISAR", "No clasificado (sin protocolo)", "NINGUNO"