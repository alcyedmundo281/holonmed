# Propuesta: bandas de likelihood ratio en `medsemiotics-db`

**Para**: quien mantiene el índice.
**De**: HolonMed, que lo consume.
**Estado**: propuesta. Nada de esto está implementado en el consumidor
todavía; se implementa cuando el formato esté acordado.

---

## El problema, en una línea

Hoy el umbral está congelado dentro del **nombre** del signo:

```yaml
- nombre: Hiperlipasemia (>3x)
  rol: prueba_especifica
  lr: 26.6
  lr_negativo: 0.1
```

Así, una lipasa de **3.1×** y una de **20×** son el mismo signo y el mismo
cociente. Eso no es cierto, y no es un detalle de precisión: es la
diferencia entre una pancreatitis probable y una casi segura.

El valor no es binario, y el formato lo obliga a serlo.

## Lo que **no** proponemos, y por qué importa

No proponemos rangos de referencia por analito —un «potasio normal: 3.5–5.1»
guardado junto al concepto—. Parece la solución obvia y es la equivocada.

Un número no significa nada fuera de una hipótesis. Un potasio de 6.2 empuja
hacia una acidosis y aleja de una alcalosis: **el mismo valor, dos
hipótesis, direcciones opuestas**. Un rango de referencia único no puede
expresar eso, y guardarlo invitaría a interpretar el número sin hipótesis,
que es exactamente lo que el consumidor tiene prohibido: su extractor
descarta toda interpretación numérica que ningún corte declarado respalde,
porque en una auditoría el modelo inventó el corte 9 de 15 veces.

**El umbral es propiedad del par (analito, hipótesis), y es graduado.**

## El formato propuesto

```yaml
signos:
  - analito: Lipasa sérica
    codigos: { holonmed: "HM:0732", snomed: "10443000" }
    rol: prueba_especifica
    unidad: "xLSN"          # veces el límite superior de normalidad
    bandas:
      - { desde: 3,  hasta: 10, lr: 12.0, fuente: "…" }
      - { desde: 10,            lr: 26.6, fuente: "…" }
    lr_negativo: 0.1
    fuente: >-
      Fuente del comportamiento global del signo. Cada banda cita además
      la suya.
```

Y el mismo analito, en otro protocolo, con bandas por abajo:

```yaml
  - analito: Potasio sérico
    rol: prueba_especifica
    unidad: "mmol/L"
    bandas:
      - { hasta: 3.0, lr: 8.0, fuente: "…" }
      - { desde: 3.0, hasta: 3.5, lr: 2.4, fuente: "…" }
```

### Las cinco reglas

**1. Los intervalos son semiabiertos: `[desde, hasta)`.** Un valor cae en
una banda y sólo en una. Sin esta regla, un potasio de exactamente 3.5
pertenecería a dos y el consumidor tendría que elegir en silencio.

**2. Omitir un extremo lo abre.** Sin `desde`, la banda llega hasta −∞; sin
`hasta`, hasta +∞. Es más honesto que escribir `desde: 0`, que afirma un
límite inferior que nadie midió.

**3. `unidad` es obligatoria en cuanto haya una banda numérica.** Un número
sin unidad no es un dato: 3.5 de potasio en mmol/L y en mg/dL son cuadros
distintos. Sin `unidad`, el consumidor **rechaza el protocolo entero** en
vez de suponer la unidad más común.

**4. Cada banda cita su fuente.** Es la regla que el índice ya aplica a los
LR, aplicada a cada tramo: *un likelihood ratio sin procedencia es un número
inventado con formato científico*. Un LR por banda es un LR nuevo, no una
interpolación del anterior.

**5. Las bandas no tienen que cubrir toda la recta.** Un valor fuera de
todas las bandas significa que **esta hipótesis no sabe leerlo**, y el
consumidor lo dirá en voz alta en vez de callarlo. Obligar a cubrir todo
forzaría a inventar cocientes para tramos que nadie estudió.

### Lo que NO se exige

**Monotonía.** Los LR de un analito pueden subir, bajar o hacer una U —los
dos extremos anormales y el centro no informativo son un caso real, no una
patología del formato—. Exigir monotonía descartaría signos legítimos.

## Compatibilidad hacia atrás

Un signo con `lr` y sin `bandas` sigue siendo válido y significa **una banda
única** que cubre lo que su nombre decía. Los nueve protocolos actuales no
se tocan, y migrar es opcional y por signo.

Se propone que `analito` conviva con `nombre`: `nombre` sigue valiendo para
signos binarios de verdad —«signo de Cullen», que se tiene o no—, y
`analito` marca los que llevan valor. Un signo con `bandas` y sin `analito`
es un error, no una abreviatura.

## Lo que validará el consumidor

Estas comprobaciones correrán en CI de HolonMed contra el índice clonado, en
el mismo paso que hoy comprueba que los protocolos anclan lo que acuñan:

- Dos bandas del mismo signo no se solapan.
- `desde < hasta` cuando ambos están.
- Cada banda trae `lr` y `fuente`.
- Hay `unidad` si hay bandas numéricas.
- `bandas` implica `analito`.

Ninguna de ellas es de estilo: cada una impide una lectura silenciosamente
equivocada de un valor de laboratorio.

## Preguntas abiertas

Son decisiones del índice, no del consumidor, y bloquean la implementación:

1. **¿Unidades canónicas por analito?** Si el índice declarara la unidad
   canónica junto al concepto, `unidad` en el signo sería una comprobación
   en vez de una declaración, y una discrepancia se cazaría en CI. Es mejor,
   pero es trabajo en el índice.

2. **¿`xLSN` o valor absoluto?** Los múltiplos del límite superior de
   normalidad viajan bien entre laboratorios; los absolutos son lo que
   informa el analizador. Probablemente hagan falta los dos, y entonces
   `unidad` distingue cuál es.

3. **¿Bandas condicionadas por edad o sexo?** Creatinina y hemoglobina las
   necesitan. La propuesta **no** las incluye para no retrasar el resto, y
   el formato no las impide: cabrían como una clave más dentro de la banda.
   Conviene decidir si se dejan para una v2 declarada o se meten ya.

## Lo que esto desbloquea

- **Ciclo 11** de HolonMed: el valor deja de ser binario.
- **Ciclo 12**: la tupla como control de flujo, que depende del 11 —una
  prueba sensible negativa sólo descarta si «negativa» está definido con
  precisión.
- Y la **serendipia** del ciclo 10 gana lectura: un potasio no solicitado ya
  entra como problema nuevo, y con bandas podrá además competir por
  hipótesis en vez de sólo aparecer.
