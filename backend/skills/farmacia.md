---
titulo: Registro de preparación de farmacia
descripcion: >-
  Qué debe constar cuando farmacia prepara o dispensa lo que se ordenó.
tipo: operativo
rol: farmacia
version: "1.0.0"

campos:
  - nombre: paciente
    etiqueta: Nombre del paciente
    requerido: true

  - nombre: diagnostico
    etiqueta: Diagnóstico
    requerido: true

  - nombre: preparacion
    etiqueta: Preparación realizada
    requerido: true

  - nombre: componentes
    etiqueta: Principios activos y cantidades
    requerido: true
    descripcion: Qué se mezcló y en qué cantidad.

  - nombre: lote
    etiqueta: Lote
    descripcion: >-
      Trazabilidad del producto. En citostáticos suele ser exigible por
      normativa; declara aquí lo que exija la tuya.

  - nombre: caducidad
    etiqueta: Caducidad de la preparación

  - nombre: horario_preparacion
    etiqueta: Hora de preparación
    requerido: true

  - nombre: responsable
    etiqueta: Farmacéutico responsable
    requerido: true

  - nombre: condiciones
    etiqueta: Condiciones de elaboración
    descripcion: Cabina de seguridad biológica, campana de flujo laminar.

procedimientos:
  - nombre: Preparación de citostáticos
    codigos: { holonmed: "HM:2101" }
  - nombre: Preparación de nutrición parenteral
    codigos: { holonmed: "HM:2102" }
  - nombre: Preparación de mezcla intravenosa
    codigos: { holonmed: "HM:2103" }
---

# REGISTRO DE FARMACIA

ROL: farmacéutico responsable de la preparación.

Extrae del texto los campos declarados. Reglas:

1. **No inventes ningún campo.** Un lote inventado es peor que un lote
   ausente: rompe la trazabilidad sin que nadie lo note.
2. Los componentes van con su cantidad. «Oxaliplatino» sin dosis es un
   registro incompleto.
3. Si el texto describe las condiciones de elaboración, recógelas: en
   preparaciones estériles y citostáticos suelen ser parte del registro
   exigible.
