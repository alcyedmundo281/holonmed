---
titulo: Registro de administración de enfermería
descripcion: >-
  Qué debe constar cuando enfermería administra algo que se ordenó.
tipo: operativo
rol: enfermeria
version: "1.0.0"

# Lo que el registro debe contener para ser válido.
#
# Un registro incompleto no se puede facturar, y ésa es una causa real de
# que los procedimientos se queden sin cobrar: no es que no se hagan, es
# que se documentan a medias mientras se está atendiendo.
#
# El sistema no rellena estos campos: los busca en lo que se escribió y
# señala los que faltan, mientras aún se puede corregir.
campos:
  - nombre: paciente
    etiqueta: Nombre del paciente
    requerido: true

  - nombre: diagnostico
    etiqueta: Diagnóstico
    requerido: true
    descripcion: >-
      Motivo por el que se indica. Es lo que justifica la prestación ante
      quien la audite.

  - nombre: medicamento
    etiqueta: Medicamento o procedimiento
    requerido: true

  - nombre: dosis
    etiqueta: Dosis administrada
    requerido: true

  - nombre: via
    etiqueta: Vía de administración
    descripcion: IV, IM, SC, oral…

  - nombre: horario_indicado
    etiqueta: Horario indicado
    requerido: true
    descripcion: A qué hora estaba pautado según la orden.

  - nombre: horario_administrado
    etiqueta: Horario de administración
    requerido: true
    descripcion: >-
      A qué hora se administró de verdad. La diferencia con el indicado es
      un indicador de calidad, no sólo un dato de facturación.

  - nombre: responsable
    etiqueta: Profesional responsable
    requerido: true

  - nombre: incidencias
    etiqueta: Incidencias
    descripcion: Reacciones, extravasación, rechazo del paciente.

procedimientos:
  - nombre: Administración de quimioterapia
    codigos: { holonmed: "HM:2201" }
  - nombre: Administración intravenosa
    codigos: { holonmed: "HM:2202" }
  - nombre: Administración de nutrición parenteral
    codigos: { holonmed: "HM:2203" }
---

# REGISTRO DE ENFERMERÍA

ROL: enfermera o enfermero responsable de la administración.

Extrae del texto los campos declarados. Reglas:

1. **No inventes ningún campo.** Si el horario de administración no
   consta, déjalo vacío. Rellenarlo con una suposición convertiría un
   registro incompleto en uno falso, que es peor: el incompleto se ve, el
   falso no.
2. Horarios en formato de 24 horas cuando el texto lo permita.
3. El diagnóstico es el que justifica esta administración, no la lista
   completa de problemas del paciente.
4. Si el texto menciona una incidencia —extravasación, reacción, rechazo—
   recógela aunque nadie pregunte por ella: cambia la conducta.
