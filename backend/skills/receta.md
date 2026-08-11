# SKILL: RECETA MÉDICA

Extrae la información de una petición de prescripción y devuélvela
estructurada. **No decides el tratamiento**: sólo estructuras lo que el
profesional ha indicado. Si la petición es ambigua, refleja la ambigüedad
en el campo correspondiente en vez de resolverla por tu cuenta.

## REGLAS

1. Extrae fármaco, concentración, frecuencia y duración de cada ítem.
2. No añadas medicamentos que no aparezcan en la petición.
3. No infieras dosis que no estén indicadas. Si falta la dosis, deja la
   concentración vacía: es mejor un hueco visible que un número inventado.
4. Redacta las indicaciones en lenguaje comprensible para el paciente.
5. Los datos del profesional (nombre, número de colegiado) NO se inventan.
   Los rellena la aplicación desde la configuración del usuario.

## SALIDA JSON

```json
{
  "items": [
    {
      "farmaco": "Nombre del principio activo",
      "concentracion": "500 mg",
      "indicaciones": "Cada 8 horas durante 3 días, con alimentos"
    }
  ],
  "indicaciones_generales": "Dieta, señales de alarma, cuándo volver a consulta",
  "diagnostico_asociado": "Diagnóstico referido en la petición, si lo hay"
}
```
