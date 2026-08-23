---
titulo: Protocolo de conjuntivitis bacteriana
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  Ojo rojo con secreción, sin trauma ni cuerpo extraño, en paciente con
  sospecha de conjuntivitis infecciosa.
version: 1.0.0

condicion:
  nombre: Conjuntivitis bacteriana
  codigos:
    holonmed: HM:6017

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0600   # Signo de exploración

modelo_bayesiano:
  # El índice no publica prevalencia para esta condición. Sin probabilidad
  # base el motor no arranca: pon la de tu población.
  probabilidad_base: 0.0

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Secreción ocular mucopurulenta
    codigos: { holonmed: "HM:3070" }
    rol: apoyo
    lr: 2.1
    fuente: >-
      Johnson D et al. JAMA 2022;327:2231-2237. PMID 35699701.
      doi:10.1001/jama.2022.7687. IC95% [1.7, 2.6]. El hallazgo más
      sensible de la revisión para causa bacteriana, pero su cociente es
      modesto: no basta por sí solo para decidir antibiótico.

  - nombre: Otitis media concomitante
    codigos: { holonmed: "HM:3071" }
    rol: apoyo
    lr: 2.5
    fuente: >-
      Johnson D et al. JAMA 2022;327:2231-2237. PMID 35699701.
      doi:10.1001/jama.2022.7687. IC95% [1.5, 4.4]. El síndrome otitis-
      conjuntivitis favorece origen bacteriano, aunque su sensibilidad es
      baja: su ausencia no descarta nada.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6017
  commit: 22f8b9c
  generado: 2026-08-23
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE CONJUNTIVITIS BACTERIANA

ROL: médico de atención primaria experto, basado en evidencia.

## Contexto fisiopatológico

- **Dónde**: conjuntiva bulbar y palpebral.
- **Cómo**: infección de la conjuntiva, con inflamación vascular y
  exudado. La causa bacteriana produce secreción más espesa y purulenta;
  la viral, más serosa, y suele acompañarse de síntomas de vía
  respiratoria alta.
- **Por qué**: *Streptococcus pneumoniae*, *Haemophilus influenzae* y
  *Staphylococcus aureus* son los agentes bacterianos más frecuentes;
  contacto con secreciones infectadas, extensión desde una otitis media
  en niños, uso de lentes de contacto.

## Instrucciones de extracción

1. Analiza los signos vitales, la exploración y el texto libre.
2. Extrae el hallazgo clínico, nunca la cifra suelta.
3. **Este modelo solo reconoce hallazgos a favor de causa bacteriana**
   (secreción mucopurulenta, otitis media concomitante). Si el texto
   describe faringitis, adenopatía preauricular o contacto con otra
   persona con ojo rojo, regístralo como dato — apuntan a causa viral,
   pero este protocolo no calcula su cociente.
4. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.

## Lo que la fuente concluye

Ningún síntoma o signo aislado distingue con certeza la conjuntivitis
bacteriana de la viral. La secreción mucopurulenta y la otitis media
concomitante se asocian a causa bacteriana; la faringitis, la adenopatía
preauricular y el contacto con otra persona con ojo rojo se asocian a
causa viral.

## Banderas rojas

No son conjuntivitis simple: sugieren un cuadro que requiere evaluación
oftalmológica urgente.

- Dolor ocular intenso o disminución de la agudeza visual
- Fotofobia marcada u opacidad corneal
- Proptosis o limitación de los movimientos oculares
- Uso de lentes de contacto con dolor (riesgo de queratitis)
- Recién nacido con secreción purulenta (oftalmía neonatal)
