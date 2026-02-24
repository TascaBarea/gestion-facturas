
def clasificar_simples(concepto):
    concepto = concepto.upper()
    if "TRASPASO" in concepto:
        return "REVISAR", "", "CASOS SIMPLES"
    if "IMPUESTOS" in concepto:
        return "IMPUESTOS", "", "CASOS SIMPLES"
    if "NÓMINA" in concepto or "TRANSFERENCIA A ELENA DE MIGUEL" in concepto:
        return "NOMINAS", "", "CASOS SIMPLES"
    if concepto.startswith("INGRESO") or concepto.startswith("ABONO"):
        return "INGRESO", "", "CASOS SIMPLES"
    return None, None, None
