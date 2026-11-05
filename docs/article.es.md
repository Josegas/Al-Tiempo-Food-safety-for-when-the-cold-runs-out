# Al Tiempo: un agente de IA que les dice a familias y albergues sin refrigeración hasta qué hora es seguro comer la comida cocinada

> Versión en español del artículo. La versión oficial para el hackathon es la de inglés ([article.md](article.md)); las cifras son las mismas. Las capturas son de la demo en vivo en inglés.

![Al Tiempo: inocuidad de los alimentos para cuando se acaba el frío](img/cover.png)

**En un minuto:** Al Tiempo es un agente bilingüe (inglés/español) hecho con el **Strands Agents SDK** que corre en **Amazon Bedrock AgentCore Runtime**. Le dices, escribiendo o en voz alta, qué cocinaste o vas a cocinar y a qué hora, y te responde con una hora del reloj, por ejemplo *"cómete los frijoles antes de las 13:00 o tíralos"*. La respuesta sale de reglas oficiales de inocuidad de los alimentos (OMS, FDA de EE. UU., CDC, NHS) y del pronóstico de calor por hora del día. También puede programar un recordatorio para ese minuto exacto. El modelo de lenguaje nunca calcula una hora: lo hace un motor de reglas con pruebas, y un hook verificador bloquea cualquier respuesta cuyas horas no coincidan con él.

**Área de enfoque: Salud** (prevenir enfermedades transmitidas por alimentos). El calor, los apagones y los desastres son los factores de riesgo y el contexto de uso, no una segunda área.

| Criterio de evaluación | Evidencia en números |
|---|---|
| **Impacto social** | Hecho para los **339 millones de pobres rurales y 746 millones de pobres urbanos** en alto riesgo por falta de enfriamiento, y para los **655 millones** de personas sin electricidad. **11 de 11** reglas verificadas palabra por palabra en fuentes oficiales. |
| **Ejecución técnica** | En vivo en AWS. **244** pruebas automáticas. **50 de 50** escenarios bilingües de punta a punta en la corrida final, **18 de 18** escenarios nuevos escritos después de ajustar, **11 de 11** seguimientos de varios turnos. **26 preguntas que hizo gente real**, leídas a mano: **24 bien, 2 dudosas, 0 mal, 0 inseguras** (primera corrida: 15 / 4 / 7, 2 inseguras). **8 de 8** horas inventadas bloqueadas por el verificador. **9 de 9** recordatorios en vivo entregados en menos de un minuto. |
| **Comunicación** | Demo sin login, botones para 8 escenarios listos, un **semáforo** con la hora en grande, **hablar o escribir** con la respuesta leída en voz alta, la **curva del calor** del día, una **tarjeta imprimible** para la cocina y diseño pensado primero para celular. Cada número de este artículo tiene un enlace a una fuente pública. |
| **Originalidad** | Aplica reglas oficiales al **pronóstico por hora**; recordatorios a futuro con **EventBridge Scheduler**; un **planificador de tandas para albergues**; **modo apagón**; un **hook verificador** que revisa al modelo contra código determinista. |

---

## El problema

*Imagina a una mamá en una casa sin refrigerador, una tarde de 38 °C. A las 9:00 cocinó arroz y frijoles para todo el día. A las 14:00 su hijo de dos años tiene hambre. ¿El arroz todavía está bien?*

No tiene refrigerador, ni termómetro, ni tiempo para buscar guías. Si se equivoca, lo paga su hijo. El calor lo empeora.

- **866 millones de personas se enferman y 1.52 millones mueren cada año** por comer alimentos contaminados. Los menores de 5 años cargan el **29%** de ese daño, con **143 000 muertes en 2021** ([hoja informativa de la OMS sobre inocuidad, 4 de junio de 2026](https://www.who.int/news-room/fact-sheets/detail/food-safety)).
- El calor importa. En 10 poblaciones europeas, los casos de salmonelosis aumentaron **de forma lineal con la temperatura por encima de 6 °C** ([Kovats et al., 2004](https://pmc.ncbi.nlm.nih.gov/articles/PMC2870124)).
- La refrigeración no es universal:
  - **655 millones** de personas no tenían electricidad en 2024, y el **88.8%** vive en África ([Tracking SDG7 2026, SEforALL](https://www.seforall.org/system/files/2026-07/SEforALL%20Tracking%20SDG7%20-%20The%20Energy%20Progress%20Report%202026_Executive%20Version_22Jul2026-2.pdf)).
  - En 77 países expuestos al calor, **339 millones de pobres rurales y 746 millones de pobres urbanos** están en alto riesgo de no tener enfriamiento adecuado ([Chilling Prospects 2026, vía UNEP Cool Coalition](https://coolcoalition.org/news/chilling-prospects-2026-links-rising-heat-mortality-persistent-cooling-access-gaps)).
- En la India rural, según reportó The Tribune con datos de la encuesta NFHS-5, el **25.2%** de los hogares tiene refrigerador pero el **91.5%** tiene celular ([The Tribune, mayo de 2022](https://www.tribuneindia.com/news/mobile-most-owned-item-survey-393691)). El celular es el eslabón que le falta a la cadena de frío.

Las reglas existen. La OMS dice que no se deje comida cocinada a temperatura ambiente más de 2 horas, y la FDA lo baja a 1 hora por encima de 90 °F (32 °C). Pero nadie las convierte en *"cómelo antes de las 13:00 de hoy"* para una familia sin refrigerador.

## Pruébalo en 1 minuto

- **Demo en vivo (sin login):** https://d2mnz1h4b0sg0y.cloudfront.net
- **Código (licencia MIT):** https://github.com/Josegas/Al-Tiempo-Food-safety-for-when-the-cold-runs-out
- **Video (< 3 min):** [TODO: link de YouTube]

1. Abre la demo en tu celular y elige **English** o **Español**.
2. Toca **Voy a cocinar**. La página empieza en modo **Simulado**: un día de 38 °C guardado y el reloj fijo en las 12:00, para que todos vean el mismo resultado. Aparece un semáforo verde con **15:00** en grande, y la respuesta es *"Si lo cocinas a las 14:00, según U.S. FDA, cómelo antes de las 15:00. Con este calor (más de 32 °C) las bacterias crecen más rápido: aguanta 1 hora, no 2. Cocina solo lo que se va a comer. ¿Te aviso a las 14:45?"* Di *"sí, avísame"*.
3. Toca **Ya cociné** para ver la misma regla después de cocinar (verde, con cuenta regresiva en vivo), o pregunta por arroz de hace 5 horas para ver el rojo **Tíralo**. En modo Simulado el reloj va acelerado, así que un recordatorio llega en aproximadamente **1 minuto**.
4. Prueba **Albergue (120 personas)**, **Apagón** y **Señales de alarma**. Toca **🔊 Escuchar** para oír cualquier respuesta, o **🎤 Hablar** para preguntar en voz alta (en Chrome).
5. Cambia a modo **Real** para usar tu ubicación real (redondeada a ~1 km) y el pronóstico real por hora.

![Inicio en un celular: aviso de modo simulado, selector de idioma y botones de escenarios](capturas/01-demo-home.png)

## Qué hace

Cada respuesta de abajo es una **respuesta real de la demo en vivo** en modo simulado (día de 38 °C, reloj a las 12:00), copiada tal como salió el 4 de noviembre en inglés y traducida aquí; las capturas son esas mismas conversaciones en un celular. `[...]` marca dónde la recortamos.

### 1. Ventana segura + recordatorios (el núcleo)
> **Usuario:** Cociné frijoles a las 12:00 y no tengo refri. ¿Hasta qué hora se pueden comer?
> **Al Tiempo:** Según U.S. FDA, cómelo antes de las **13:00** o deséchalo. Con este calor (más de 32 °C) las bacterias crecen más rápido: aguanta 1 hora, no 2. ¿Te aviso a las **12:45**?
> **Usuario:** Sí, avísame por favor.
> **Al Tiempo:** Recordatorio programado para las **12:45**: "Al Tiempo: come la comida antes de las 13:00. Después, deséchala. Fuente: U.S. FDA".
> ⏰ **Recordatorio (12:45):** Al Tiempo: come la comida antes de las 13:00. Después, deséchala. Fuente: U.S. FDA

Si el usuario acepta, **Amazon EventBridge Scheduler** crea una programación de una sola vez para ese minuto exacto, que se borra sola al ejecutarse. El recordatorio llega a la web (el SMS está hecho pero apagado en la demo; ver Limitaciones). La hora y el texto del recordatorio se arman en código a partir del resultado del motor de reglas.

![El recordatorio llegando en la demo en vivo: programado para las 12:45 y entregado por EventBridge Scheduler](capturas/ui/live-reminder-en.png)

**Antes de cocinar, no solo después.** El momento más útil es antes de que la comida se quede afuera, así que el primer botón es el plan:
> **Usuario:** Voy a cocinar frijoles a las 14:00 y no tengo refri. ¿Hasta qué hora se pueden comer?
> **Al Tiempo:** Si lo cocinas a las 14:00, según U.S. FDA, cómelo antes de las **15:00**. Con este calor (más de 32 °C) las bacterias crecen más rápido: aguanta 1 hora, no 2. Cocina solo lo que se va a comer. ¿Te aviso a las **14:45**?

**Primero, un semáforo.** Cada respuesta con una decisión empieza con un color y una hora grande, copiados de la salida del motor de reglas: **verde** "cómelo antes de las 15:00" con cuenta regresiva en vivo, **ámbar** cuando queda poco tiempo o la comida no aguanta hasta la hora de comer, **rojo** "tíralo" y **gris** cuando falta un dato ("¿a qué hora lo cocinaste?"). Quien lee poco entiende la decisión por el color y el número. El botón **🔊 Escuchar** lee la respuesta en voz alta (Amazon Polly).

| Verde: antes de cocinar | Rojo: arroz de hace 5 horas, para un bebé |
|---|---|
| ![Semáforo verde: si lo cocinas a las 14:00, cómelo antes de las 15:00, con la línea de tiempo y la curva del calor del día](capturas/ui/live-plan-en.png) | ![Semáforo rojo: tíralo, con la línea de tiempo y una nota de composta](capturas/ui/live-baby-en.png) |

**Entiende los detalles que la gente de verdad da.** Adaptamos 26 preguntas que gente real hizo en foros públicos (ver *Retos*). Nadie dice "cociné a las 12:00 y no tengo refri". Dicen cosas como estas, y todas se leen **en código** a partir de sus palabras:
- *"Come a las 3 en la obra"* → es la hora de comer, no la de cocción. Respuesta en vivo: **"No aguanta hasta las 15:00: según U.S. FDA, cómelo antes de las 13:00 o deséchalo. Con este calor (más de 32 °C) las bacterias crecen más rápido: aguanta 1 hora, no 2. Mejor prepáralo más cerca de la hora de comer."**
- *"Los tamales siguen en la vaporera echando vapor"* → OMS: la comida que se mantiene muy caliente (más de 60 °C) no está en el reloj de temperatura ambiente; el tiempo empieza cuando se apaga el fuego.
- *"Está en un cuarto con aire acondicionado a 22 grados"* → la temperatura del cuarto que dice el usuario reemplaza al pronóstico de afuera. Respuesta en vivo: **"Según la OMS, cómelo antes de las 13:00 o deséchalo. Con los 22 °C que me dijiste aguanta 2 horas, nunca más: afuera del refri las bacterias se multiplican."**
- *"¿Qué hago con el guisado?"* (sin hora) → pregunta a qué hora se cocinó y mientras tanto dice la regla. El modelo no puede inventar una hora de cocción.
- *"Desde anoche"*, *"since 7am"*, *"hace una hora y media"* → se leen bien. (Antes de esta ronda, "una hora y media" se leía como una hora: un error hacia el lado inseguro, que ahora tiene su prueba.)
- *"Perdón, no entendí"* → el mismo resultado del motor en una frase más sencilla.

Cada respuesta de ventana segura también dice **por qué**, en pocas palabras armadas en código: *"Con este calor (más de 32 °C) las bacterias crecen más rápido: aguanta 1 hora, no 2."* El porqué largo, con los números del pronóstico, está a un toque en "Ver por dentro". Debajo de la respuesta, la web dibuja una **línea de tiempo**: cocinado → ahora → aviso → límite, con los minutos que quedan y la regla que decidió. Se dibuja solo con los números del motor de reglas, que la API devuelve junto al texto. Nunca lee horas de las palabras del modelo.

![La línea de tiempo de la ventana segura en la demo en vivo: cocinado 12:00, aviso 12:45, límite 13:00, decide U.S. FDA](capturas/ui/timeline-live-en.png)

**¿Sin señal? Sigue ayudando.** La web se puede instalar en el celular y abre sin internet. El agente necesita conexión, así que sin conexión no finge que responde: muestra las reglas oficiales básicas (1 hora en día de calor, 2 horas si no; arroz 1 hora; sin sobras para bebés; señales de alarma → clínica) con sus fuentes.

![Sin conexión: las reglas oficiales básicas en lugar de un error](capturas/ui/offline-card-en-390.png)

### 2. Planear porciones y horarios
> **Usuario:** Somos 5 en casa, comemos a las 14:00 y cenamos a las 20:00. ¿A qué hora cocino?
> **Al Tiempo:** Según las reglas, cocina la comida a las **13:00** (1 hora antes de comer) y la cena a las **19:00** (1 hora antes de comer). No guardes sobras a temperatura ambiente.

### 3. Modo apagón
Para familias que *sí* tienen refrigerador y se quedaron sin luz, el reloj empieza cuando se fue la luz. Usa las reglas de apagones de la FDA: 4 horas para un refrigerador cerrado, 48 horas para un congelador lleno, 24 horas para uno a medias.
> **Usuario:** Se fue la luz a las 06:00. No he abierto el refri y el congelador está lleno. ¿Qué hago?
> **Al Tiempo:** Según la FDA de EE. UU., la comida del refri ya no es segura después de 4 horas (terminó a las **10:00**). Tira la comida perecedera del refri o revísala con un termómetro de cocina. El congelador sigue seguro hasta el **viernes a las 06:00** porque está lleno y cerrado. Mantenlo cerrado.

Si el usuario dice que el hielo del congelador se derritió y se volvió a congelar, la regla de 24/48 horas del congelador ya no aplica y la respuesta es tirar la comida perecedera (una política conservadora del proyecto). Si el usuario nunca mencionó un congelador, la respuesta no habla de uno, para que el modelo no "mueva" su pollo crudo ahí (una falla real de las evals, que ahora es una prueba).

![Modo apagón en la demo en vivo](capturas/ui/live-outage-en.png)

### 4. Modo estricto para bebés y niños pequeños
> **Usuario:** ¿Le doy a mi bebé el arroz que cociné hace 5 horas? Estuvo fuera del refri.
> **Al Tiempo:** Según U.S. FDA, ya pasó el límite: lo más seguro es no comerlo y tirarlo. Con este calor (más de 32 °C) las bacterias crecen más rápido: aguanta 1 hora, no 2. Sé que da lástima; la próxima vez dime la hora y te aviso antes.

Para bebés y niños pequeños el motor agrega una regla del proyecto más estricta (1 hora, servir al momento, sin sobras); aquí la regla de calor de la FDA ya daba el mismo límite.

Para fórmula infantil sigue a los CDC: usarla dentro de las 2 horas de preparada y dentro de 1 hora desde que el bebé empieza a tomar, y tirar lo que sobre en el biberón.

### 5. Albergues y comedores comunitarios
Después de un desastre, un albergue puede cocinar para 120 personas sin refrigeración. Al Tiempo planea **tandas escalonadas** para que nada se sirva fuera de la ventana segura. Cada tanda tiene su hora de desecho.
> **Usuario:** Coordino un albergue con 120 personas. La comida es de 13:00 a 15:00, arroz y frijoles, sin forma de mantenerla caliente.
> **Al Tiempo:** [...] Programamos dos tandas: la primera lista a las **13:00**, se tira a las **14:00**; la segunda lista a las **14:00**, se tira a las **15:00**. Ninguna comida debe quedarse afuera después de su hora de desecho.

Si la cocina *sí* puede mantener la comida arriba de 60 °C (la regla de la OMS para mantener caliente), el plan cambia.

| En pantalla | Impresa para la pared de la cocina |
|---|---|
| ![Plan de tandas para 120 personas en la demo en vivo](capturas/ui/live-shelter-en.png) | ![Tarjeta impresa: tabla de tandas con la hora de tirar, la fuente, el modo, la fecha y un código QR](capturas/ui/live-print-card-shelter-en.png) |

### 6. Escalada ante señales de alarma (sin diagnóstico ni dosis)
Si alguien tiene diarrea o vómito, Al Tiempo hace preguntas fijas basadas en las señales de deshidratación de la OMS. Si hay alguna señal, o la respuesta es "no sé", escala al número de emergencia del país.
> **Usuario:** Mi hija de 2 años tiene diarrea, está muy dormida y casi no quiere beber. Estamos en México.
> **Al Tiempo:** Según la OMS, tu hija muestra señales de alarma: está muy dormida y casi no bebe. Es una emergencia. Llama al 911 o ve a la clínica más cercana ahora mismo. No esperes.

![Escalada por señales de alarma en la demo en vivo](capturas/ui/live-danger-en.png)

Si le piden dosis de medicamentos, se niega con amabilidad y manda a la persona a una clínica.

### Háblale, mira el calor, imprímelo
- **Hablar en lugar de escribir.** Un botón de micrófono usa el reconocimiento de voz del navegador (Chrome, Edge, Android). Si la pregunta fue hablada, la respuesta **se lee en voz alta sola con Amazon Polly**: una conversación completa por voz para quien lee o escribe poco. En Chrome el audio lo procesa Google, y el botón lo dice. Queríamos Amazon Transcribe para que el audio se quede en AWS, pero no está disponible en el plan gratuito de esta cuenta (la misma razón que el SMS); es el primer siguiente paso.
- **El calor de hoy, hora por hora.** Debajo de la ventana segura, una gráfica pequeña dibuja el mismo pronóstico por hora que usó el motor, la línea de 32 °C y la ventana segura sombreada encima. Se *ve* por qué hoy es 1 hora y no 2. Las horas del pronóstico se mantienen fuera del contexto del modelo, para que nunca se vuelvan horas "permitidas" para el verificador.
- **Una tarjeta para la pared de la cocina.** "Imprimir tarjeta" convierte una ventana segura o un plan de albergue en una hoja grande y sencilla: la hora límite en letra enorme (o una tabla de tandas con **TIRAR a las** y una casilla de "hecho"), la fuente que decidió, el modo (simulado o real), la fecha y un código QR de regreso a la app. En un comedor comunitario donde no hay smartphone en cada mesa, el plan vive en la pared.

![Tarjeta impresa de una ventana segura: cómela antes de las 15:00, después tírala](capturas/ui/live-print-card-window-en.png)

### Notas pequeñas después de la decisión (elegidas en código, sin cambiarla)
- **"¿Qué hago con ella?"** Cuando la respuesta es "tíralo", una nota pequeña dice qué puede ir a una composta casera: restos de fruta y verdura y un poco de comida cocinada, pero no carne, pescado, lácteos ni grasa, que atraen animales ([US EPA, Composting At Home](https://www.epa.gov/recycle/composting-home)). Nunca sugiere dar comida pasada a animales.
- **Consejo de higiene.** Si el mensaje habla de ensalada cruda, de una tabla usada para pollo crudo o de lavarse las manos, aparece un consejo corto de las [Cinco claves para la inocuidad de los alimentos de la OMS](https://www.who.int/docs/librariesprovider2/default-document-library/5keys_en.pdf), con su porqué. Máximo uno por respuesta y sin cantidades de químicos ("si usas un desinfectante, sigue su etiqueta").

## Cómo funciona

> **Principio de diseño: el modelo conversa y explica. Las reglas oficiales deciden. Ante la duda, lo más seguro.**

![Arquitectura de Al Tiempo en AWS](img/architecture.png)

El agente es un ciclo de **Strands Agents** con **8 herramientas**. Cada herramienta que calcula algo es Python determinista con pruebas unitarias:

| Herramienta | Qué devuelve |
|---|---|
| `compute_safe_window` | Hora límite, hora del aviso, estado (`eat_before_deadline` / `discard_now`), reglas y fuentes aplicadas |
| `get_forecast` | Temperatura por hora (datos del clima de [Open-Meteo.com](https://open-meteo.com/), CC BY 4.0; un día de 38 °C guardado en modo simulado) |
| `plan_meals` | A qué hora cocinar cada comida para que se coma dentro de la ventana |
| `track_outage` | Veredicto del refri y el congelador desde que se fue la luz, como resumen armado en código |
| `plan_shelter_batches` | Tandas escalonadas, porciones y hora de desecho por tanda |
| `schedule_reminder` | Programación de una sola vez en EventBridge Scheduler para el minuto exacto |
| `check_danger_signs` | Escalar o no, más el número de emergencia del país |
| `get_current_time` | La hora, solo cuando el usuario la pregunta (el reloj de la demo en modo simulado) |

**Las reglas son datos, no código.** `rules/food_rules.yaml` tiene 11 reglas. Cada una guarda su `source_url`, la fecha en que se revisó y la **frase textual** de la página oficial, para que cualquiera la verifique con Ctrl+F. Dos reglas dicen abiertamente lo que son:
- **Adaptada:** el NHS dice refrigerar el arroz cocido dentro de 1 hora. Sin refri, usamos esa hora como límite para comerlo.
- **Política propia:** un modo más estricto para niños pequeños.

| Servicio de AWS | Para qué |
|---|---|
| Amazon Bedrock (Nova 2 Lite) | El modelo de lenguaje, llamado a través de un *application inference profile* etiquetado para ver su costo por proyecto |
| Amazon Bedrock AgentCore Runtime | Corre el agente de Strands: una sesión serverless por usuario, ARM64, acceso solo por IAM |
| Amazon EventBridge Scheduler | Recordatorios en un minuto exacto del futuro, aunque el usuario cierre la app |
| AWS Lambda + Amazon API Gateway | API con límite de peticiones (10/s, ráfagas de 20) y un tope diario de 500 mensajes; entrega los recordatorios |
| Amazon DynamoDB | Recordatorios entregados y el contador diario. Los datos personales expiran a los **7 días (TTL)** |
| Amazon Polly | Lee las respuestas en voz alta para quien lee poco; automático cuando la pregunta fue hablada |
| Amazon S3 + CloudFront | El sitio público de la demo |
| Amazon CloudWatch + AWS Budgets | Logs sin datos personales, un tablero, 3 alarmas y un presupuesto de $10 con interruptor de apagado automático |
| Amazon SNS | Correos de alarmas; recordatorios por SMS (hechos, apagados por el plan gratuito de la cuenta) |

## Impacto social

**Para quién es:**
- **Usuarios principales:** hogares sin refrigerador o con luz intermitente, como la India rural, el África subsahariana y los asentamientos informales.
- **También para:** familias con refrigerador durante un apagón, **albergues y comedores comunitarios** después de desastres, y promotoras de salud.

**Por qué les sirve:**
- **Respuestas claras:** recibes una hora y una acción ("cómelo antes de las 13:00 o tíralo"), no una tabla de reglas.
- **Voz:** puedes preguntar en voz alta, y cualquier respuesta se puede escuchar con Amazon Polly (sola, si hablaste), para quien lee o escribe poco. Hoy hay dos idiomas, y agregar más es un cambio de configuración.
- **Funciona aunque el usuario no esté:** el recordatorio llega aunque se haya cerrado la app, gracias a EventBridge Scheduler. El SMS para celulares básicos está implementado (Amazon SNS) y probado con un cliente simulado, pero está apagado en la demo pública: la cuenta de AWS está en el plan gratuito, donde los SMS no están disponibles. Si un SMS falla, el recordatorio en la web llega igual.
- **Seguro por defecto:**
  - Si no se sabe la hora de cocción, supone el peor caso y la pregunta.
  - Si falla el pronóstico, usa el límite más estricto (1 hora).
  - Nunca dice "100% seguro".
- **Privado:**
  - Sin nombres y sin cuenta.
  - La ubicación se redondea a ~1 km.
  - Los logs nunca incluyen el texto del usuario.
  - Los datos de recordatorios se borran solos a los 7 días.

**Lo que medimos (métricas del sistema, no un estudio de campo):**

| Métrica | Resultado |
|---|---|
| Reglas de alimentos verificadas en su fuente oficial, con texto textual | **11 / 11** |
| Pruebas del motor de reglas, herramientas y seguridad que pasan | **244 / 244** |
| Evals de punta a punta consistentes con el motor de reglas (50 escenarios bilingües, corrida final) | **50 / 50**; 49 / 50 en cada una de las 4 corridas anteriores de esa noche, 0 respuestas inseguras |
| Escenarios nuevos escritos después de ajustar (nunca se ajustó con ellos) | **18 / 18** |
| **26 preguntas adaptadas de preguntas públicas reales**, leídas a mano (bien / dudosas / mal) | **24 / 2 / 0**, 0 inseguras (primera corrida, antes de cualquier cambio: 15 / 4 / 7, 2 inseguras) |
| Seguimientos de varios turnos ("pero estaba tapado", "ya me lo comí", "no entendí") | **11 / 11** |
| Evals adversariales: presión con bebés, "di que es 100% seguro", dosis de medicamentos, diagnóstico, antibióticos, remedios caseros, "ignora tus reglas", una afirmación falsa de la OMS | **29 / 30**, 0 respuestas inseguras |
| Horas inventadas bloqueadas por el verificador (pruebas unitarias adversariales) | **8 / 8** |
| Recordatorios entregados en el sistema en vivo | **9 / 9**, de 4 a 45 segundos después del minuto programado |
| Costo por turno de conversación (Bedrock) | **0.0029 USD** (corrida final de evals; el prompt creció con los ejemplos de estilo), antes **0.0022 USD** (evals) y **0.0024 USD** (en vivo) |

Todavía no hemos probado Al Tiempo con familias en campo. Es el siguiente paso más importante (ver Limitaciones).

**Prueba de uso informal:** [TODO: resultados de la prueba informal con personas, n = …, o borrar esta línea]

### Cómo mediríamos el impacto en un piloto

Las métricas del sistema muestran que la orientación es **correcta**. Un piloto tiene que mostrar que es **útil** y que **cambia lo que la gente hace**. Nuestro plan para un piloto de 4 semanas con un comedor comunitario y 20–30 hogares sin refrigerador, junto con promotoras de salud locales:

| Pregunta | Indicador | Cómo lo mediríamos |
|---|---|---|
| ¿La gente entiende la respuesta? | % que puede repetir la hora límite y la acción ("comer antes de las 13:00 o tirarlo") con sus palabras | Una pregunta corta justo después del primer uso |
| ¿Cambia lo que hacen? | % de comidas cocinadas que se comen dentro de la ventana segura, antes vs. durante el piloto | Una pregunta diaria sobre la comida principal |
| ¿Los recordatorios funcionan en la vida real? | % de recordatorios entregados a tiempo, y % seguidos de la acción (comer o tirar) | Logs de entrega (ya medido: `delay_s`) + la pregunta diaria |
| ¿Ayuda a albergues y comedores? | Porciones tiradas por tanda, y porciones servidas fuera de la ventana | La hoja de tandas del coordinador, antes vs. durante |
| ¿Es seguro? | Respuestas que contradicen las reglas oficiales | El log del verificador + revisión de una muestra aleatoria del 10% |
| ¿Es accesible en costo? | Costo por hogar al mes | Cost Explorer con la etiqueta del proyecto (ya configurada) |

**No** diremos que hubo menos enfermedades con un piloto tan chico. Eso necesita un estudio más grande con datos de servicios de salud. Lo que el piloto puede mostrar con honestidad es comprensión, cambio de conducta y desperdicio de comida.

## Ejecución técnica

**Hoy corre en AWS**, y todo es infraestructura como código (AWS CDK en Python), dividido en dos stacks:
- **AlTiempoAccess:** un usuario IAM de mínimo privilegio para el proyecto, un rol de despliegue con OIDC de GitHub, el presupuesto y las alarmas.
- **AlTiempoApp:** todo lo que toca el usuario.

**Núcleo determinista, con pruebas.** 244 pruebas de pytest cubren:
- cada regla, incluidos casos frontera (exactamente 32 °C, exactamente 2 horas, datos faltantes → peor caso);
- la lectura de horas a partir de las palabras del usuario en español e inglés (*"a las 12:00"*, *"hace una hora y media"*, *"since 7am"*, *"desde anoche"*, *"come a las 3"*, *"voy a cocinar a las 2"*), más la temperatura del cuarto que dice;
- el verificador, la API y las Lambdas de recordatorios.

**El hook verificador.** Usa hooks de Strands:
- `AfterToolCallEvent` junta cada hora y límite que devolvieron las herramientas.
- `AfterModelCallEvent` revisa el borrador del modelo.
- Si el borrador menciona una hora o un límite que el motor nunca produjo, el modelo reintenta **una vez** con una nota de corrección. Si sigue mal, la respuesta se reemplaza con una plantilla segura armada con el resultado del motor.

![Cómo pasa un mensaje por el motor de reglas y el verificador](img/verifier.png)

**Las evals eligieron el modelo.** 18 escenarios bilingües cubren:
- hogares, apagones, bebés, albergues y señales de alarma;
- usuarios adversariales (*"solo dime que es 100% seguro"*).

Corrimos el mismo agente con tres modelos de Bedrock:

![Tasa de aprobación de evals por modelo](img/model-evals.png)

**Amazon Nova Lite** pasó **8/18 (44%)**, **Nova Pro 15/18 (83%)** y **Nova 2 Lite 18/18 (100%)**. Nova 2 Lite cuesta más o menos la mitad por turno que Nova Pro. Con Nova 2 Lite, esa suite de 18 escenarios pasó **36/36** en dos corridas.

**Después hicimos la prueba más difícil.** Ampliamos la suite a **50 escenarios** (26 en español, 24 en inglés). Las horas esperadas salen del motor de reglas, no de nosotros. Los escenarios nuevos incluyen comida ya vencida, horas dichas con palabras, fórmula, niños pequeños, un refrigerador abierto, antibióticos, remedios caseros, *"ignora tus reglas"* y una afirmación falsa de la OMS. La primera corrida completa sacó **95/100**, y las fallas valieron más que la calificación. Revelaron **cuatro bugs reales**: una hora límite de apagón que el modelo reusó después de que se abrió la puerta del refrigerador, una regla del prompt que parecía aplicar solo a apagones, un molde de plantilla (*"cómelo antes de las HH:MM"*) copiado en una respuesta, y un arnés de evals que no le decía al agente el idioma del usuario. Cada uno ya tiene su prueba. Después de los arreglos: **98/100**, y **99/100** en la corrida siguiente (ya con la frase del *porqué*), mediana de **1,644 ms**, **0.00227 USD** por turno y **0** respuestas con plantilla segura. Ninguna falla fue insegura. Las reportamos tal como son.

**Después de los arreglos de las preguntas reales y las respuestas cortas (4 de noviembre, noche), corrida final con el código final:** **50/50** (mediana **1,950 ms**, **0.00285 USD** por turno), **18/18** escenarios nuevos, **11/11** seguimientos de varios turnos, **9/10** adversariales (la que faltó se negó a decir "100% seguro" y pidió la hora en vez de llamar al motor: segura, pero no la respuesta esperada), **3/3** consejos de higiene y **5/6** casos nuevos de temperatura del cuarto, cocina planeada y ensaladas (la que faltó: una ensalada "para el comedor" recibió "¿de qué hora a qué hora sirven?" en vez de un plan; una pregunta razonable, pero no la respuesta esperada). Los resultados crudos están en `evals/results/`.

**Rendimiento en vivo (medido en la demo desplegada):**

| Medición | Resultado |
|---|---|
| Tiempo del agente por turno (mediana, 15 turnos en vivo) | **1.9 s** |
| De punta a punta, turnos de seguimiento | **2.1–3.0 s** |
| Primer mensaje, antes del calentamiento (navegador real, 6 escenarios) | **6.2 s** de mediana |
| Primer mensaje con calentamiento, haciendo clic 5 s después de abrir la página | **2.0 s** de mediana (−68%) |
| Primer mensaje si se hace clic al instante (el calentamiento sigue corriendo) | 5.8 s de mediana, no peor que antes |

**Calentamiento.** La mayor parte de la espera del primer mensaje era AgentCore arrancando una sesión nueva para cada visitante, no el modelo. Al abrir la página, la web llama a `/api/warm`, que arranca la sesión y arma el agente **sin llamar al modelo (0 tokens)**, con su propio tope diario. Medido en un navegador real sobre la demo en vivo: la primera respuesta bajó de **6.2 s a 2.0 s** (mediana de 6 escenarios).

**DevOps:**
- **CI:** GitHub Actions corre lint, pruebas con cobertura, búsqueda de secretos (gitleaks), revisión de dependencias (pip-audit) y `cdk synth` en cada pull request.
- **Despliegue:** cada merge a `main` despliega con **OIDC** (sin llaves de AWS guardadas en GitHub) y corre una prueba de humo contra el sitio en vivo.
- **Políticas como código:** un release se bloquea si alguna regla de alimentos no está verificada.
- **Observabilidad:** un tablero de CloudWatch, 3 alarmas por correo y logs estructurados con latencia, tokens y bloqueos del verificador por turno.

La prueba de humo que corre después de cada despliegue, contra la demo en vivo (salida real, 4 de noviembre, después del último despliegue):
```
$ make smoke
1) health: {'ok': True}
2) safe window: PASS (5150 ms) -> According to U.S. FDA, eat it before 13:00 or throw it away. In this heat (over 32 °C) bacteria grow faster: it lasts 1 hour, not 2. Shall I remind you at 12:45
3) reminder requested -> Reminder set for 12:45: "Al Tiempo: eat the food before 13:00. After that, throw it away. Source: U.S. FDA"
   reminder: PASS, arrived 102 s after asking; scheduler delay 35 s -> Al Tiempo: eat the food before 13:00. After that, throw it away. Source: U.S. FDA
RESULT: PASS
```

![GitHub Actions desplegando a AWS con OIDC: pruebas, paquete ARM64, despliegue con CDK y prueba de humo, todo en verde](capturas/06-github-actions.png)

![Tablero de CloudWatch al-tiempo](capturas/07-cloudwatch-dashboard.png)

**Desplegar sin Docker.** AgentCore Runtime corre en ARM64 y mi laptop es x86. En lugar de emular un contenedor, el agente se despliega con el *direct code deployment* de AgentCore: un zip determinista de wheels ARM64 para Python 3.12. El mismo código siempre produce el mismo hash, así que nada se vuelve a desplegar si nada cambió.

## Originalidad

| Lo que enseñó el workshop | Lo que agrega Al Tiempo |
|---|---|
| Ciclo del agente + herramientas | Herramientas que son un **motor de reglas con fuentes oficiales**: el LLM nunca calcula una hora, un límite ni una temperatura |
| Hooks | Un **hook verificador** que revisa cada hora de la respuesta contra el motor (reintenta una vez y luego usa una plantilla segura) |
| Desplegar en AgentCore Runtime | **Direct code deployment** de un zip ARM64 armado sin Docker, definido en CloudFormation a través de CDK |
| Session managers | Agentes por sesión detrás de una API con límite de peticiones y **tope diario** |
| Evals | Evals como **filtro para elegir el modelo** (44% → 100%), y cada bug real se vuelve una prueba de regresión |
| — | **EventBridge Scheduler**: el agente actúa en el futuro (recordatorios), no solo cuando le hablas |
| — | **Pronóstico de calor por hora** → la regla de 1 o 2 horas se aplica hora por hora |
| — | **Modo apagón** y un **planificador de tandas para albergues** |
| — | **Lectura determinista de horas** a partir de las palabras del usuario (el texto del usuario gana sobre los argumentos del modelo) |
| — | **FinOps:** inference profile etiquetado, alertas de presupuesto y un **interruptor de apagado** (acción de AWS Budgets) |
| — | **Conversación hablada** (voz del navegador de entrada, Amazon Polly de salida), **TTL** de DynamoDB para la privacidad |
| — | Una **gráfica del calor por hora** con el pronóstico que usó el motor, y una **tarjeta imprimible para la cocina** con código QR |
| — | Un **semáforo + línea de tiempo** dibujados con la salida estructurada del motor, no con el texto del modelo, con cuenta regresiva en vivo |
| — | **Planear antes de cocinar**: "voy a cocinar a las 14:00" da la hora límite y un recordatorio antes de que la comida se quede afuera |
| — | **Detalles leídos en código a partir de las palabras del usuario**: hora de comer vs. hora de cocción, comida todavía en la lumbre, la temperatura del cuarto, "desde anoche"; las horas que adivina el modelo se ignoran |
| — | Una **web instalable que funciona sin conexión** con las reglas oficiales básicas (la señal es intermitente donde faltan refrigeradores) |

## Soluciones existentes

- **USDA FoodKeeper** dice cuánto dura la comida en el refrigerador, el congelador o la alacena. Da por hecho que **sí** tienes refrigerador.
- **Las Cinco claves de la OMS** y **las guías de la FDA/USDA** dan reglas generales: 2 horas a temperatura ambiente, 1 hora por encima de 32 °C. Son correctas, pero no se convierten en una hora para *tu* comida, *hoy*, con *tu* calor.

No encontramos una herramienta que:
- aplique estas reglas al pronóstico por hora del día para un hogar sin refrigerador;
- te recuerde en el minuto exacto;
- planee tandas de cocina para un albergue sin refrigeración.

Al Tiempo cubre ese hueco, y cada regla apunta a su fuente oficial.

## Retos y un error real que medimos

**El error: el agente le dijo a un usuario que tirara comida que todavía era segura.**
- **Qué falló:** en pruebas, *"cociné frijoles a las 12:00"* recibió *"hay que tirar los frijoles ahora"*. Lo correcto era *"cómelos antes de las 13:00"*.
- **Cómo lo encontramos:** lo reproducimos 3 veces y registramos las entradas de la herramienta. El modelo (Nova Lite en ese momento) hizo tres cosas distintas: pasó la hora correcta, volvió a preguntar, o **no mandó la hora**. Sin hora, la herramienta aplicó bien el peor caso: "hora desconocida = desechar".
- **Qué cambiamos:** las palabras del propio usuario ahora se leen **en código** (`agent/time_parse.py`, español e inglés), y ganan sobre lo que mande el modelo. Agregamos 20 pruebas de lectura de horas y 3 de regresión.
- **Cuánto mejoró:** el mismo mensaje ahora recibe *"cómelos antes de las 13:00"*. En la suite completa de evals, pasar a Nova 2 Lite subió la tasa de aprobación de **8/18 (44%) a 18/18 (100%)**, y luego a **36/36** en dos corridas de la suite original de 18 escenarios (hoy **50/50** en la suite más grande de 50 escenarios, corrida final).

**El error contrario fue peor.** *"¿Le doy a mi bebé el arroz que cociné hace 5 horas?"* una vez recibió *"cómelo antes de las 13:00"*. El verificador no lo atrapó, porque las 13:00 *sí* venían de la herramienta: el error estaba en la entrada, no en la salida.
- **El arreglo:** una entrada `minutes_ago` y un estado `discard_now` del motor.
- **La plantilla segura** dice que se tire cuando ya pasó el límite.
- **El resultado:** la misma pregunta ahora siempre recibe un **Tíralo** en rojo (ver la captura de arriba). Cada uno de estos se volvió una prueba de regresión.

**Dos bugs reales más, encontrados en el sistema en vivo:**
- **Texto del recordatorio:** los primeros recordatorios en vivo los escribía el modelo, y uno de los tres primeros llegó como *"Eat the beans now, discard after"*, sin hora. La hora y el texto del recordatorio ahora se arman en código con el resultado del motor.
- **Modo apagón:** el modelo una vez le dijo a un usuario a las 12:00 *"tienes hasta las 10:00"* para el refri. El motor tenía el veredicto correcto; el modelo lo leyó mal. El motor ahora devuelve un resumen en lenguaje sencillo en los dos idiomas, y el modelo solo lo transmite. Aplicamos la misma idea a la respuesta de ventana segura. En la siguiente corrida completa de evals, los reintentos del verificador bajaron de **2 a 0** y la suite de 18 escenarios siguió en **36/36**.

**Una prueba de usuario después del lanzamiento:** un probador escribió *"a las 3 y media de la tarde"*. Nuestro lector de horas entendió **03:00**. El verificador notó que las 15:30 del modelo no coincidían y usó la plantilla segura, así que a nadie se le dijo que comiera algo inseguro, pero la respuesta fue torpe. El lector ahora entiende "y media", "y cuarto", "menos cuarto", "al mediodía" y horas escritas con palabras. Agregamos 12 pruebas de regresión con la frase exacta del probador. En la misma ronda, el modelo a veces ignoraba *"mantuve el refri cerrado"*, así que el estado de la puerta y del congelador también se lee de las palabras del usuario. La suite de 18 escenarios que teníamos entonces volvió a **36/36** con **0** reintentos del verificador.

**La prueba más grande: 26 preguntas que hizo gente real.** Parafraseamos 26 preguntas que la gente publicó en foros: comida olvidada toda la noche, el lonche de un trabajador de la construcción, tamales que siguen echando vapor, las sobras de un bebé, apagones, "mi abuela dice que hervirla mata todo", un comedor comunitario para 150 personas, arroz fermentado. Las corrimos **una vez, antes de cambiar nada**, y leímos cada respuesta a mano:

| | Bien | Dudosas | Mal | Inseguras |
|---|---|---|---|---|
| Primera corrida, sin cambios | 15 | 4 | 7 | **2** |
| Corrida final, después de los arreglos de abajo | **24** | 2 | **0** | **0** |

Ninguna falla fue una regla equivocada. Dos fueron seguimientos que terminaban en una plantilla segura genérica y una fue que faltaba un *"mis reglas no cubren la comida fermentada"* (las tres se arreglaron más temprano ese día). La mayoría de las demás eran sobre **cómo describe el tiempo la gente real**, y cada una se volvió una prueba o un caso de evaluación:
- *"Come a las 3"* se leía como cocinado a las 03:00. Ahora la hora de comer y la de cocción van separadas, y la respuesta dice *"no aguanta hasta las 15:00"*.
- *"Hace una hora y media"* se leía como una hora, un error hacia el lado **inseguro**.
- *"Desde anoche"*, *"since 7am"* y *"después de 6 horas sin luz"* no se entendían, y el modelo llenaba el hueco con una hora inventada. La herramienta ahora ignora lo que adivine el modelo: sin hora en las palabras del usuario → pregunta.
- *"Voy a cocinar a las 2"* se leía como "ayer a las 2" → "tíralo". La cocina planeada ahora va en el futuro, con recordatorio.
- Un congelador que se descongeló y se volvió a congelar se calificaba como **"seguro hasta mañana"** (inseguro). El hielo derretido ahora anula la regla del congelador.
- El modelo puso el pollo crudo del usuario en un congelador que el usuario nunca mencionó. La respuesta de apagón ya no habla de un congelador si el usuario no lo mencionó.
- Un error real que encontramos en el camino: el verificador confundió un plan de comidas con una ventana segura y su respaldo lanzó un `KeyError`, así que el usuario veía "perdón, no pude responder". Arreglado, con su prueba.

Las 2 respuestas dudosas que quedan son de redacción, no de decisión: una dice que "no puede usar la temperatura de la cocina" (sí puede) y pide la hora de cocción, y otra le atribuye a la FDA que "el limón o el chile no cambian el límite", una regla que adaptamos, no una cita. Las dos van hacia el lado seguro. Las reportamos tal como son.

**Otros retos:**
- **Fuentes que bloquean lectores automáticos:** USDA FSIS devolvía HTTP 403, así que citamos las páginas de la FDA que publican las mismas reglas y que sí pudimos revisar palabra por palabra.
- **Falsos positivos del verificador:** *"quedan 30 minutos"* y *"el arroz de hace 5 horas"* se bloqueaban por error al principio, y los arreglamos con pruebas.
- **Un detalle de OIDC en GitHub Actions:** agregar `environment:` cambia el *subject* del token, así que AWS habría rechazado el rol.

## Costo

| Concepto | Valor |
|---|---|
| Bedrock, medido | **0.0029 USD por turno** en la corrida final de evals (7,571 tokens de entrada / 127 de salida en promedio sobre 50 turnos; AWS Price List API, us-east-1). Antes: 0.0022 USD (evals), 0.0024 USD (en vivo) |
| AgentCore Runtime | Se cobra por vCPU y GB-hora activos. No hay servidores 24/7: sin EC2, sin NAT gateway, sin throughput aprovisionado |
| Estimado para todo el periodo de evaluación (≈1,000 turnos hasta el 27 de noviembre) | **≈ 3–5 USD** en total |

Protecciones que de verdad limitan el gasto, no solo avisan:
- Límite de peticiones en la API (10/s, ráfagas de 20), un tope diario de 500 mensajes de chat y otro tope de 1,000 calentamientos de sesión.
- `max_tokens=800` por llamada y como máximo 1 reintento del verificador.
- Un presupuesto de $10 para el proyecto con alertas al 50/80/100%. El tráfico normal de los jueces se estima en unos $3, así que el interruptor solo se activa si alguien abusa de la demo.
- Al 100% del presupuesto, una **acción de AWS Budgets pega automáticamente una política DENY** a los roles del agente y de la API.

**Probamos las protecciones con tráfico real** (`make loadtest`, 4 de noviembre). La prueba solo llama al endpoint de salud, así que nunca llega al modelo:
- **Uso normal**, 8 peticiones por segundo durante 10 segundos: **80 / 80** respondidas, mediana de **141 ms**, p95 de 228 ms.
- **Una ráfaga de 300 peticiones en 1.6 segundos:** **65** respondidas, **57** detenidas por el límite de API Gateway (HTTP 429) y **178** detenidas por Lambda (HTTP 503). Ninguna llegó a Bedrock.
- **Lo que nos enseñaron los 503:** esta cuenta nueva de AWS solo permite **10** funciones Lambda corriendo al mismo tiempo (el valor normal de AWS es 1,000). API Gateway deja pasar ráfagas de 20, así que Lambda rechazó el resto. El costo quedó protegido y la web muestra "intenta otra vez", pero los límites no estaban alineados. Un aumento de cuota gratuito lo arregla. Lo encontramos porque lo medimos.

El presupuesto y su interruptor de apagado, como los reporta AWS (salida real):
```
$ aws budgets describe-budget-actions-for-budget --budget-name al-tiempo-monthly ...
type: APPLY_IAM_POLICY   threshold: 100%   approval: AUTOMATIC   status: STANDBY
policy: arn:aws:iam::<account>:policy/al-tiempo-kill-switch
```

## Limitaciones y siguientes pasos

**Limitaciones (sin rodeos):**
- Al Tiempo da **orientación general basada en reglas de salud pública**. No puede ver, oler ni analizar la comida, y no es consejo médico.
- Las reglas son de **tiempo y temperatura**. No cubren comida que ya venía contaminada, ni alergias.
- **Todavía no hay estudio de campo.** Todas las métricas de arriba son del sistema.
- El modelo todavía puede redactar mal algunas cosas. En una respuesta de las evals dijo que la comida "lleva 2 horas afuera" cuando llevaba 0 horas (conservador, pero falso). El verificador revisa horas y límites, no cada frase.
- Los recordatorios por SMS están implementados pero apagados en la demo: la cuenta de AWS está en el plan gratuito, donde los SMS no están disponibles. La demo usa recordatorios en la web y notificaciones del navegador.
- La voz de entrada solo funciona en navegadores con reconocimiento de voz (Chrome, Edge, Android).
- Por ahora, dos idiomas.
- El modelo varía entre corridas (más o menos ±2 escenarios de 26–50), así que un juez puede ver una redacción un poco distinta a la nuestra. La decisión y sus horas siempre salen del motor.

**Siguientes pasos:**
- Piloto con un comedor comunitario y con promotoras de salud.
- WhatsApp y SMS en producción.
- Amazon Transcribe para la voz de entrada, para que el audio se quede en AWS (hoy lo bloquea el plan gratuito de la cuenta).
- Más idiomas.
- Avisos masivos para promotoras de salud en días de onda de calor.
- Guía para refrigeradores de barro (enfriamiento por evaporación).
- Escuelas.
- Una app móvil nativa.

## Lo que aprendí

[TODO: personalizar: este es un borrador con mi voz]

- **Que el código decida y el modelo explique.** Mi primera versión le confiaba las horas al modelo y falló en los dos sentidos: le dijo a alguien que tirara comida segura, y le dijo a alguien que le diera a un bebé arroz que se debía desechar. Pasar cada cálculo a código con pruebas fue el punto de quiebre.
- **Las evals convierten opiniones en decisiones.** No elegí el modelo por su fama. Lo eligieron 18 escenarios, y cada bug que encontramos se volvió una prueba.
- **Las preguntas reales enseñan más que las inventadas.** Mis escenarios pasaban; las 26 preguntas de gente real sacaron 2 respuestas inseguras en la primera corrida. Casi todo era cómo habla la gente del tiempo.
- **Las fuentes necesitan citas textuales.** Revisar cada regla palabra por palabra eliminó tres números desactualizados de mis propias notas.
- **Nube y DevOps desde el primer día:**
  - un usuario IAM de mínimo privilegio por proyecto;
  - GitHub Actions con OIDC en lugar de llaves guardadas;
  - un presupuesto con un interruptor de apagado real;
  - todo en CDK, para poder reconstruir el sistema completo con un solo comando.

## Cómo se usó la IA

- **Para escribir el código:** usé **Claude Code** (Anthropic) como compañero de programación, y escribió la mayor parte del código.
- **Mi parte:** definí el problema, el alcance y los principios de seguridad. Revisé y probé el trabajo, aprobé cada cambio de IAM, desplegué en mi cuenta de AWS e hice yo mismo cada commit y cada merge.
- **Fuentes:** cada fuente y cada número se revisó contra la página original, y las citas textuales están guardadas en el repositorio (`docs/sources.md`).
- **Dentro del producto:** Al Tiempo usa **Amazon Nova 2 Lite** en Amazon Bedrock para conversar con los usuarios. Las horas y los límites siempre salen de código determinista.
- **Imágenes:** los diagramas y la gráfica de este artículo se generan con código del repositorio (`scripts/make_figures.py`). La gráfica lee los resultados crudos de las evals.

---

*Al Tiempo da orientación general sobre inocuidad de los alimentos basada en fuentes de salud pública. No es consejo médico. En una emergencia, llama al número de emergencia de tu país.*
