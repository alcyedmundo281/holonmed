# Aviso de uso clínico

## Esto no es un dispositivo médico

HolonMed **no está certificado** como producto sanitario. No tiene marcado
CE bajo el Reglamento (UE) 2017/745 (MDR), ni autorización de la FDA, ni
registro ante ninguna agencia reguladora.

No debe usarse como única base para ninguna decisión sobre un paciente.

## Qué hace y qué no hace

**Hace:**

- Estructurar texto clínico en hallazgos codificados con SNOMED CT.
- Señalar qué hallazgos pudo confirmar y cuáles no, con el motivo.
- Calcular una probabilidad a partir de un protocolo declarado, mostrando
  el razonamiento completo.

**No hace:**

- Diagnosticar. Las probabilidades que calcula son estimaciones
  estadísticas condicionadas a un protocolo y a la calidad de la
  extracción, no diagnósticos.
- Prescribir. El generador de recetas estructura lo que un profesional ya
  ha decidido; los PDF que emite carecen de validez sin firma.
- Sustituir la exploración física, la anamnesis o el criterio clínico.

## Limitaciones conocidas

1. **La extracción depende del modelo de lenguaje.** Modelos locales
   pequeños omiten hallazgos y ocasionalmente inventan. Las tres capas de
   validación reducen los falsos positivos, no los eliminan, y no pueden
   hacer nada contra lo que el modelo simplemente no extrajo.

2. **Los falsos negativos no se ven.** El sistema muestra lo que descartó,
   pero no puede mostrar lo que nunca llegó a extraer. Un hallazgo ausente
   del resultado no significa que no esté en el texto.

3. **Los likelihood ratios vienen del protocolo, no de tu población.** Un
   LR publicado en una cohorte hospitalaria terciaria no se traslada a
   atención primaria. Revisa las fuentes de cada skill antes de confiar en
   sus números.

4. **El razonamiento bayesiano asume independencia condicional** entre
   hallazgos, y eso rara vez es cierto en clínica. Hallazgos correlacionados
   inflan la probabilidad posterior.

5. **La cobertura de SNOMED CT en español es desigual.** Algunos conceptos
   frecuentes no tienen término preferente en la extensión española y
   quedarán marcados como ruido aunque sean correctos.

6. **Sin trazabilidad reglamentaria.** No hay registro de auditoría
   inmutable, firma electrónica cualificada ni control de versiones de
   modelo con la formalidad que exige un entorno regulado.

## Datos de paciente

El procesamiento es local: las narrativas no salen de tu máquina. Eso
elimina un riesgo, no todos.

Antes de introducir datos reales:

- Verifica la base legal del tratamiento (RGPD art. 6 y 9, o la normativa
  que te aplique).
- Cifra el disco donde se almacene la base de datos.
- Cambia la contraseña por defecto de ArangoDB y no lo expongas fuera de
  `localhost`.
- Recuerda que los PDF generados en `generated_docs/` contienen datos
  identificables.

## Responsabilidad

El software se distribuye **sin garantía de ningún tipo**, según los
términos de la [licencia AGPL-3.0](LICENSE). Quien lo use en un contexto
asistencial asume la responsabilidad clínica y legal de las decisiones que
tome.

Si eres un profesional sanitario: este sistema es un ayudante que puede
equivocarse, y está diseñado para decírtelo cuando no está seguro. Trátalo
como tal.
