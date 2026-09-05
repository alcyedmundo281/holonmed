---
titulo: Base mínima para atención episódica
version: "1.0.0"
alcance: episodica

# La excepción de Weed, DECLARADA. Para un clavo en el pie, un brazo roto o
# algo en el ojo no se hace la historia entera —él lo dice explícitamente—
# pero el mínimo tampoco se deja al criterio del momento.
#
# El punto entero de declararla es que exista la diferencia: un episodio
# atendido con esta base NO puede presentarse como si se hubiera hecho la
# comprehensiva. En cuanto la excepción es informal, se convierte en la
# regla los días de mucha carga, que son justo los días en que más se pasa
# algo por alto.

secciones:
  - nombre: Filiación
    items:
      - { nombre: Edad, quien: paciente }
      - { nombre: Sexo, quien: paciente }

  - nombre: Antecedentes que cambian la conducta hoy
    items:
      - { nombre: Alergias medicamentosas, quien: paciente }
      - { nombre: Medicación habitual, quien: paciente }
      - { nombre: Enfermedades previas, quien: paciente }

  - nombre: Signos vitales
    items:
      - { nombre: Presión arterial, quien: enfermeria }
      - { nombre: Frecuencia cardíaca, quien: enfermeria }
      - { nombre: Temperatura, quien: enfermeria }

  - nombre: Motivo
    items:
      - { nombre: Motivo de consulta, quien: paciente }
      - { nombre: Exploración dirigida al motivo, quien: medico }
---

# Base mínima para atención episódica

Cuatro secciones y trece ítems. No es la historia completa y **no debe
poder confundirse con ella**: el `alcance` la declara `episodica`, y un
episodio atendido bajo esta base lo dice.

Las alergias y la medicación habitual están aquí aunque el episodio sea
menor, porque son las dos que cambian la conducta de hoy y las dos cuyo
olvido tiene consecuencias inmediatas.
