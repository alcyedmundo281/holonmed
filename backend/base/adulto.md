---
titulo: Base definida del adulto
version: "1.0.0"
alcance: comprehensiva

# La base de datos DEFINIDA, en el sentido de Weed: lo que se averigua
# siempre, no lo que se le ocurra preguntar a quien pasa visita.
#
# Que el contenido sea arbitrario no es una objeción. Un campo de fútbol
# también lo es; sin la línea no hay forma de saber si alguien anotó. Lo que
# no es arbitrario es que esté DECLARADO, porque la lista de problemas es un
# artefacto de la base: sin definirla, la lista depende de dónde se formó
# quien preguntó y de cuántos ingresos hubo anoche.
#
# `quien` no es una etiqueta descriptiva: es la asignación del trabajo, y
# decide qué interfaz tiene que existir. Que la mayoría no sea `medico` es
# deliberado y es la solución del propio Weed para esta fase.
#
# Esta base es un PUNTO DE PARTIDA razonable, no una recomendación clínica.
# Cada servicio declara la suya; el mecanismo es lo que aporta el sistema.

secciones:
  - nombre: Filiación
    items:
      - { nombre: Edad, quien: paciente }
      - { nombre: Sexo, quien: paciente }
      - { nombre: Con quién vive, quien: paciente }
      - { nombre: Ocupación, quien: paciente }

  - nombre: Antecedentes
    items:
      - { nombre: Enfermedades previas, quien: paciente }
      - { nombre: Cirugías previas, quien: paciente }
      - { nombre: Medicación habitual, quien: paciente }
      - { nombre: Alergias medicamentosas, quien: paciente }
      - { nombre: Consumo de tabaco, quien: paciente }
      - { nombre: Consumo de alcohol, quien: paciente }
      - { nombre: Antecedentes familiares, quien: paciente }

  - nombre: Signos vitales
    items:
      - { nombre: Presión arterial, quien: enfermeria }
      - { nombre: Frecuencia cardíaca, quien: enfermeria }
      - { nombre: Frecuencia respiratoria, quien: enfermeria }
      - { nombre: Temperatura, quien: enfermeria }
      - { nombre: Saturación de oxígeno, quien: enfermeria }
      - { nombre: Peso, quien: enfermeria }
      - { nombre: Talla, quien: enfermeria }

  - nombre: Exploración
    items:
      - { nombre: Exploración cardiopulmonar, quien: medico }
      - { nombre: Exploración abdominal, quien: medico }
      - { nombre: Exploración neurológica básica, quien: medico }
      # Weed sacó esta exploración de la consulta médica y se la dio a
      # enfermería entrenada y verificada, porque encontraban más.
      - { nombre: Exploración ginecológica, quien: enfermeria, desde_edad: 18 }

  - nombre: Laboratorio
    items:
      - { nombre: Hemograma, quien: laboratorio }
      - { nombre: Glucemia, quien: laboratorio }
      - { nombre: Creatinina, quien: laboratorio }
      - { nombre: Perfil lipídico, quien: laboratorio, desde_edad: 40 }
---

# Base definida del adulto

Lo que se averigua **siempre** en atención comprehensiva. No es una guía de
qué hacer con lo que se encuentre: es la línea del campo.

Para atención episódica —un clavo en el pie, un ojo rojo— existe
[`episodica.md`](episodica.md), declarada aparte y con su nombre. Weed
admite la excepción y la quiere explícita: en cuanto es informal, se
convierte en la regla los días de mucha carga.
