"""Validación del identificador de un cliente: cédula ecuatoriana o RUC de persona natural
(User Story 4 de 002-clientes-fidelizacion, FR-017). Funciones puras: sin acceso a base de
datos ni a infraestructura, mismo estilo que `censura.py` y `fuga_cliente.py`.

El identificador es SIEMPRE opcional (FR-003, Principio II): sirve para no duplicar al mismo
cliente entre visitas cuando el cajero lo tiene a mano, nunca para bloquear una venta. Estas
funciones sólo responden "¿este texto es un identificador bien formado?"; la unicidad y el
rechazo 409 viven en el servicio/endpoint, no aquí.

Alcance deliberadamente acotado (un cliente individual de un minimarket):

  * Cédula: 10 dígitos. Los dos primeros son código de provincia. Se aceptan 01–24 (las 24
    provincias) y además el 30, asignado por el Registro Civil a ecuatorianos registrados en
    el exterior y a extranjeros residentes — negarlo excluiría a clientes reales con cédula
    válida. Tercer dígito 0–5 (persona natural). Décimo dígito verificador por módulo 10 con
    coeficientes 2,1,2,1,2,1,2,1,2 sobre los primeros 9 (cada producto > 9 se reduce restándole
    9; el verificador es el complemento a la decena de la suma módulo 10).
  * RUC de persona natural: 13 dígitos = una cédula válida (mismos 10 dígitos, mismo algoritmo)
    + sufijo literal "001".

NO se implementa el RUC de sociedad/empresa (tercer dígito 6 o 9, algoritmo módulo 11): no
aplica a un cliente individual. Cualquier texto que no calce con cédula ni con RUC natural es
inválido; no se intenta adivinar.
"""

_PROVINCIAS_VALIDAS = set(range(1, 25)) | {30}
_COEFICIENTES_CEDULA = (2, 1, 2, 1, 2, 1, 2, 1, 2)


def validar_cedula_ecuatoriana(numero: str) -> bool:
    """`True` si `numero` es una cédula ecuatoriana de persona natural bien formada."""
    if not isinstance(numero, str) or not numero.isdigit() or len(numero) != 10:
        return False

    provincia = int(numero[:2])
    if provincia not in _PROVINCIAS_VALIDAS:
        return False

    if int(numero[2]) > 5:  # tercer dígito 0–5: persona natural
        return False

    suma = 0
    for digito, coeficiente in zip(numero[:9], _COEFICIENTES_CEDULA):
        producto = int(digito) * coeficiente
        suma += producto - 9 if producto > 9 else producto

    verificador = (10 - suma % 10) % 10
    return verificador == int(numero[9])


def validar_identificador(numero: str) -> bool:
    """`True` si `numero` es una cédula (10 dígitos) o un RUC de persona natural (13 dígitos
    terminados en "001" cuyos primeros 10 son una cédula válida). Cualquier otro caso: `False`.
    """
    if not isinstance(numero, str) or not numero.isdigit():
        return False
    if len(numero) == 10:
        return validar_cedula_ecuatoriana(numero)
    if len(numero) == 13:
        return numero[10:] == "001" and validar_cedula_ecuatoriana(numero[:10])
    return False
