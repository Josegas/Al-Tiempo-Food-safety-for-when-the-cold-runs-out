# Development diary

## 2026-11-03 14:30
- Qué intenté: verificar automáticamente las fuentes oficiales de cada regla (FSIS, CDC, NHS, OMS).
- Qué pasó: FSIS y FoodSafety.gov devolvieron 403 a clientes automáticos; la URL de CDC de fórmula dio 404; la página de "Cinco claves" de la OMS no trae los límites (están en el PDF del manual).
- Cómo lo supe: respuesta HTTP de cada página.
- Qué decidí: marcar esas reglas `unverified: true`. El motor las rechaza salvo con `ALLOW_UNVERIFIED_RULES=true` (dev/demo) y la CI bloquea releases (`scripts/check_rules.py --strict`) hasta verificarlas a mano en el navegador.
- Extra: la hoja de la OMS (4 junio 2026) trae cifras nuevas: 866 millones enfermos/año, 1.52 millones de muertes, 143 000 muertes de menores de 5 años (2021). Las de CLAUDE.md (600 M / 420 000 / 125 000) están desactualizadas.

## 2026-11-03 15:20 — Error real medido #1 (unsafe answer)
- Qué intenté: prueba de humo contra Bedrock (Nova Lite) con "Can I give my baby the rice I cooked 5 hours ago?".
- Qué pasó: el agente respondió "eat the rice before 13:00". Inseguro: el arroz ya llevaba 5 h fuera.
- Cómo lo supe: prueba manual de punta a punta; el verificador no lo bloqueó porque 13:00 sí venía de la herramienta (el error estaba en la ENTRADA, no en la salida).
- Causa: el modelo no pasó la hora de cocción y la herramienta asumía "recién cocinado = ahora".
- Qué decidí: (1) nuevo parámetro `minutes_ago` calculado en código; (2) si no hay hora de cocción, peor caso = desechar; (3) el motor devuelve `status: discard_now | eat_before_deadline`; (4) la plantilla segura del verificador dice "deséchalo ahora" si ya expiró; (5) tests de regresión `test_baby_rice_five_hours_ago_is_discard` y `test_unknown_cooking_time_is_discard`.
- Resultado: misma pregunta → "discard the rice now". Medir antes/después en evals.

## 2026-11-03 15:30
- Qué intenté: usar Claude Haiku 4.5 en Bedrock.
- Qué pasó: `ResourceNotFoundException: Model use case details have not been submitted`.
- Qué decidí: modelo por defecto `us.amazon.nova-lite-v1:0` (barato, funciona). Opcional: llenar el formulario de Anthropic en la consola de Bedrock para comparar.

## 2026-11-03 15:00 — Error real medido #2 (reportado por el usuario)
- Qué intenté: `make chat` → "cocine frijoles a las 12:00".
- Qué pasó: respondió "los frijoles deben desecharse ahora" (incorrecto; el límite era 13:00).
- Cómo lo supe: lo reportó el usuario; lo reproduje 3 veces imprimiendo la entrada de la tool. Nova Lite hizo 3 cosas distintas: pasó `minutes_ago=0` (correcto por suerte), volvió a preguntar la hora, y **omitió la hora** → la tool aplicó el peor caso ("hora desconocida = desechar").
- Qué decidí: la hora que escribe el usuario se lee **en código** (`agent/time_parse.py`, es/en: "a las 12:00", "hace 5 horas", "2 pm", "ahorita") y **gana** sobre lo que mande el modelo. El resultado incluye `time_source: user_text | model | unknown`. 20 tests de lectura de horas + 3 de regresión.

## 2026-11-03 15:04 — Elegir modelo con datos (evals, 18 escenarios es/en)
- Qué intenté: mismo agente y mismos escenarios con 3 modelos de Bedrock.
- Resultado: Nova Lite **8/18 (44%)**, Nova Pro **15/18 (83%)**, Nova 2 Lite **18/18 (100%)**. Costo por turno: $0.00033, $0.00499 y ~$0.0024.
- Qué decidí: modelo por defecto `us.amazon.nova-2-lite-v1:0` (el más preciso; ~2x menos costo que Pro).

## 2026-11-03 15:05 — Falsos positivos del verificador
- Qué pasó: bloqueó/reintentó respuestas correctas: "te quedan 30 minutos" (venía de `minutes_left`), "el arroz de hace 5 horas" (lo dijo el usuario), "el servicio dura 2 horas" (ventana del albergue).
- Cómo lo supe: ahora el verificador guarda `violations` y el runner de evals las muestra.
- Qué decidí: aceptar cualquier campo `*minutes*` de la tool, duraciones escritas por el usuario y `service_minutes` en el plan del albergue. Tests de regresión para los 2 casos de la tool.

## 2026-11-03 15:08 — Revisión honesta de evals (31/36 → 36/36)
- Qué pasó: 5 fallas en 2 rondas. Revisé cada respuesta: **4 eran errores de MIS chequeos**, no del agente ("deséchalo" con acento no coincidía con "desech"; "I can't say it's 100% safe" contenía "100% safe"; en albergue buscaba "60" porciones en vez de la hora). Corregí los chequeos, no el agente.
- Error real del modelo que queda: en 1 respuesta dijo "it has been out for 2 hours" cuando eran 0 h. Es conservador (no pone en riesgo), pero es falso. El verificador no lo atrapa porque "2 hours" coincide con la regla de 2 h. Pendiente: distinguir "tiempo transcurrido" del "límite".
- Resultado: 36/36 (100%), mediana 1,995 ms, $0.00227 por turno.

## 2026-11-03 15:15 — Fuentes oficiales
- Qué pasó: USDA FSIS y FoodSafety.gov bloquean lectores automáticos (403). La FDA publica las mismas reglas en páginas que sí pudimos leer palabra por palabra. CDC cambió su URL (la vieja daba 404). La FSA no trae la regla del arroz; el NHS sí.
- Qué decidí: las 11 reglas quedan verificadas con frase textual (`verified_text`) y fecha; IDs renombrados a FDA_*/NHS_*. La regla del arroz se marca `adapted` y la de niños `policy`. `ALLOW_UNVERIFIED_RULES=false` por defecto y los tests corren en modo producción.
- Cifras: se actualizaron a las más recientes y se quitaron las que no tenían fuente primaria (ver `docs/sources.md`).

## 2026-11-03 16:00 — Infraestructura en AWS (CDK)
- Qué intenté: desplegar el agente en AgentCore Runtime.
- Qué pasó: AgentCore corre en ARM64 (Graviton) y la laptop es x86, sin emulación para Docker.
- Qué decidí: *direct code deployment* (zip con wheels `aarch64`, Python 3.12), soportado por CloudFormation (`AWS::BedrockAgentCore::Runtime` → `CodeConfiguration`). Zip determinista: mismo código → mismo hash → no se redespliega sin cambios.

## 2026-11-03 16:20 — Seguridad del despliegue
- Qué pasó: el despliegue automático de los cambios de IAM fue bloqueado (no se deben aplicar permisos "a ciegas"); CDK además exige aprobación interactiva para cambios de IAM.
- Qué decidí: siempre `cdk diff` primero; los cambios de IAM los aprueba el dueño de la cuenta en su terminal (`make deploy-access`, `make deploy`). En CI se despliega sin aprobación solo desde `main` (ya revisado en el PR).
- Error evitado: con `environment:` en el job de GitHub, el claim `sub` del token OIDC cambia a `repo:...:environment:production` y AWS rechazaría el rol (que confía en `ref:refs/heads/main`). Se quitó.
- Error evitado: el *kill switch* (Budget Action) apuntaba a roles que aún no existían en el primer despliegue; se movió al stack de la app, junto a esos roles.

## 2026-11-03 19:45 — Primer despliegue en AWS + error real medido #3 (recordatorio sin hora)
- Qué intenté: `make deploy-access`, `make dev-profile`, `make deploy` y `make smoke` contra la demo viva.
- Qué pasó: todo en verde (health, ventana segura 13:00, recordatorio entregado en 92 s). Pero el texto de 1 de 3 recordatorios entregados fue "Eat the beans now, discard after": **sin hora**. Lo escribía el modelo (argumento `message` de la tool) y el verificador solo revisa la respuesta final, no los argumentos de las tools. Además el modelo lo programó a la hora límite (13:00), no a `reminder_at` (12:45).
- Cómo lo supe: el ítem en DynamoDB (`message`) y el log del smoke test.
- Qué decidí: `compute_safe_window` guarda la ventana en `agent.state`; `schedule_reminder` toma de ahí la hora (`reminder_at`) y arma el texto **en código** ("Al Tiempo: eat the food before 13:00. After that, throw it away. Source: U.S. FDA"). Si el estado es `discard_now`, no programa nada. La fuente citada ahora es la regla que **decide** la hora (`deciding_source`: FDA 1 h a 38 °C), no la primera de la lista. 3 tests de regresión.

## 2026-11-03 20:10 — Error real medido #4 (modo apagón leído al revés)
- Qué pasó: en la demo viva, "se fue la luz a las 06:00" (son las 12:00) → el modelo dijo "you have until 10:00 to keep fridge items safe". El motor decía bien `fridge_status: discard_perishables_or_check_thermometer`; el modelo lo interpretó mal. También dijo "freezer safe until 06:00" sin decir que es pasado mañana.
- Qué decidí: el motor devuelve `summary` en es/en armado en código ("the 4-hour limit ended at 10:00…", "until Friday 06:00") y el prompt pide repetirlo. Probado contra Bedrock: ahora responde bien en ambos idiomas. 2 tests de regresión.
- Pendiente honesto: a veces el modelo dice "reminder set for 13:00" aunque se programó a las 12:45 (15 min antes; es más seguro, pero inexacto).

## 2026-11-03 21:00 — Error real #5: la frase clave también se arma en código + error de OIDC
- Qué pasó (1): en la captura de la demo el modelo ofreció "a reminder for 13:00" y luego lo programó a las 12:45. El verificador lo deja pasar porque 13:00 sí viene del motor.
- Qué decidí: `compute_safe_window` devuelve `summary` armado en código ("According to U.S. FDA, eat it before 13:00 or throw it away. I can remind you at 12:45."), igual que el apagón. Evals completos otra vez: **36/36**, reintentos del verificador **2 → 0**, $0.00221 por turno.
- Qué pasó (2): el primer despliegue desde GitHub falló: `Not authorized to perform sts:AssumeRoleWithWebIdentity`.
- Cómo lo supe: CloudTrail mostró el `sub` real del token: `repo:Josegas@80491054/...@1444850797:ref:refs/heads/main`. GitHub usa ahora un sujeto **inmutable** (IDs del dueño y del repo), y el rol esperaba `repo:Josegas/...`.
- Qué decidí: el prefijo sale de `gh api repos/OWNER/REPO/actions/oidc/customization/sub` y va en `cdk.json` (`githubOidcSubPrefix`). Es más seguro: si alguien borra y recrea un repo con el mismo nombre, no puede desplegar.
- Extra: actions con Node 24 (`setup-node@v7`, `configure-aws-credentials@v6`) y runner fijo `ubuntu-24.04` para que nada cambie mientras evalúan.

## 2026-11-04 — Presupuesto, límites y arranque rápido (antes de congelar funciones)
- Pregunta del usuario: ¿limitar el presupuesto hace más lento o peor al chatbot?
- Respuesta: no. AWS Budgets solo mide y avisa; lo único que afecta al usuario es el *kill switch* (apaga la demo al 100%). Con $5 y un gasto normal estimado de ≈ $3, el margen era poco: un abuso al tope diario lo activaría en ~4 días.
- Qué decidí: presupuesto $10; *throttling* 10 req/s (ráfaga 20) porque el sondeo de recordatorios cada 15 s comparte el límite; y **warm-up**: al abrir la página la web llama `/api/warm`, que arranca la sesión de AgentCore y construye el agente sin llamar al modelo (0 tokens). Tope propio de 1,000 al día para que no se pueda abusar. El primer mensaje esperaba ~6.4 s por el arranque de la sesión (el agente en sí tarda ~1.9 s).
- Resultado medido (navegador real, 6 escenarios): primer mensaje **6.2 s → 2.0 s** si el usuario hace clic 5 s después de abrir; si hace clic al instante, 5.8 s (igual que antes, nunca peor).

## 2026-11-04 — Cumplir las reglas oficiales (área única, logos, términos de terceros)
- Qué pasó: las reglas piden UNA sola área de enfoque, prohíben logos/marcas de terceros sin permiso y exigen no infringir derechos de terceros.
- Qué revisé: ningún texto del repo, la web o el artículo declaraba "climate resilience" como área. Revisé los términos de Open-Meteo (open-meteo.com/en/terms y /en/licence): la API gratis es solo para uso no comercial (cumplimos: sin anuncios ni suscripciones), los datos son CC BY 4.0 y piden un enlace "Weather data by Open-Meteo.com" junto a donde se muestran; límite 10,000 llamadas/día (nuestros topes diarios quedan muy por debajo).
- Qué cambié: el artículo y el README declaran **Focus area: Health**; atribución de Open-Meteo en la web (pie de página y banner del modo en vivo), README y artículo; recorté el logo de GitHub de la captura de Actions; el guion del video prohíbe logos. Las reglas se parafrasean; `food_rules.yaml` guarda solo una frase corta por regla (máx. 188 caracteres) para poder verificarla, con su fuente.

## 2026-11-04 — Error real #6 (reportado por el usuario): "a las 3 y media de la tarde"
- Qué pasó: "cociné tipo a las 3 y media de la tarde" → respuesta con la plantilla segura ("No pude verificar mi respuesta…") y el nombre largo de la fuente.
- Cómo lo supe: reproduje con el modelo real e imprimí las violaciones del verificador: el lector de horas entendió **03:00** (ignoraba "y media" y "de la tarde"); el modelo sí dijo 15:30, pero el código gana y el verificador bloqueó la diferencia. El veredicto (desechar) era correcto, la respuesta no.
- Qué decidí: el lector entiende "y media", "y cuarto", "menos cuarto", "y 20", "al mediodía", "at noon" y horas con palabras ("a las tres"); 12 tests (incluye la frase exacta). Plantilla segura con nombre corto de la fuente y texto más claro.
- Al correr los evals aparecieron 2 errores más: (1) el modelo a veces no pasaba "I kept the fridge closed" → ahora la puerta y el congelador también se leen del texto del usuario (7 tests); (2) en 1 de 36 el modelo sugirió "agua tibia con azúcar" para un bebé → regla 13 del prompt: nunca recomendar comidas, bebidas ni remedios. Evals: 34/36 → 35/36 → **36/36**, 0 reintentos.

## 2026-11-04 — Rediseño de la web (rama `redesign`)
- Qué intenté: rediseño completo de `web/` (identidad propia, tarjetas de escenarios, panel de conversación, modo Demo/En vivo claro, móvil primero) sin tocar backend, reglas, motor ni verificador.
- Cómo lo verifiqué: servidor local (`make web`) contra la API real; Playwright a 375/390/768/1024/1440 px: 63 capturas (estado inicial, 7 escenarios, error simulado, recordatorio real) sin scroll horizontal ni errores de consola; axe-core: 0 violaciones WCAG 2.1 AA en es/en, móvil y escritorio; pruebas funcionales: modo En vivo con ubicación concedida (manda lat/lon redondeados) y negada, voz (200 + audio), cambio de idioma (reinicia y calienta sesión nueva), teclado (anillo de foco visible).
- Errores que encontré y corregí en el camino: el nombre se cortaba a 375 px; el placeholder se partía; la franja Demo ocupaba mucho espacio fijo en móvil (ahora el encabezado no es fijo en móvil y el panel lleva una etiqueta del modo); `data-mode` en `<body>` hacía que el body recibiera `aria-pressed` (lo detectó axe).
- Pendiente: la línea de tiempo "cocinado → cómelo antes de → deséchalo" necesita que `/api/chat` devuelva la salida del motor (campo opcional nuevo); no se tocó el backend sin autorización. Evals 35/36: 1 falla del modelo ajena al rediseño (`en-100-safe` pidió la hora en vez de usar la herramienta).

## 2026-11-03 23:30
- Qué intenté: dibujar en la web la "ventana segura" (cocinado → ahora → aviso → límite) en cada respuesta del motor.
- Qué pasó: la web solo tenía el texto del modelo; sacar horas de ese texto contradice el principio "el modelo no calcula".
- Cómo lo supe: revisando qué devolvía `/api/chat` (solo `answer` y `metrics`).
- Qué decidí: campo opcional `decision` en la respuesta, copiado tal cual del resultado de `compute_safe_window` (agent/decision.py) y pasado por la Lambda sin cambios. Sin cambios en reglas, motor, verificador ni IAM. La web dibuja solo con esos números; si el backend no lo manda, no dibuja nada. 4 tests nuevos; axe sin errores (tuve que oscurecer el rojo del texto: 4.45 → `--red-ink`).

## 2026-11-04 00:05 — prueba de carga
- Qué intenté: demostrar con números que el throttling de API Gateway (10 req/s, ráfaga 20) protege el presupuesto. `make loadtest` solo llama `/api/health` (sin modelo, sin tokens, sin gastar el tope diario).
- Qué pasó: tráfico normal (8 req/s × 10 s) → 80/80 OK, p50 141 ms. Ráfaga de 300 peticiones en 1.6 s → 65 OK, 57 × 429 (throttling, lo esperado) y **178 × 503** (inesperado).
- Cómo lo supe: `aws lambda get-account-settings` → la cuenta permite solo **10 Lambdas a la vez** (cuenta nueva; el valor normal de AWS es 1,000, cuota `L-B99A9384`). API Gateway deja pasar ráfagas de 20 y Lambda rechaza el resto con 503.
- Qué decidí: no cambiar infraestructura en el freeze. El costo sigue protegido (ninguna petición llegó a Bedrock) y la web ya muestra "intenta de nuevo". Pedir el aumento de cuota (gratis) en Service Quotas. Queda documentado como hallazgo real.

## 2026-11-04 00:20 — evals de 18 a 50 escenarios
- Qué intenté: llegar a 50 escenarios (la guía pide 40–60). Las horas esperadas salieron del motor en modo demo, no de mi cabeza.
- Qué pasó: primera corrida de los 32 nuevos: 29/32. Corrida completa: 95/100.
- Errores reales encontrados:
  1. Refri con la puerta abierta: el modelo dijo "seguro hasta las 15:00 si el termómetro…". El motor devolvía esa hora aunque la regla ya no aplicaba, y el verificador la aceptaba. Ahora el motor no da hora cuando la regla no aplica (test nuevo).
  2. La regla 12 del prompt empezaba con "En apagones…", y el modelo no siempre repetía el resumen de la ventana segura ("Déscalo ahora"). Ahora aplica siempre y pide copiarlo palabra por palabra.
  3. Sin herramienta, el modelo copió el molde del prompt: "cómelo antes de las **HH:MM**". El verificador ahora trata los moldes (`HH:MM`, `<regla>`) como una hora inventada: reintenta y, si sigue, usa la plantilla segura (2 tests nuevos). Las evals fallan cualquier respuesta con un molde.
  4. Arnés de evals: no ponía el idioma en el estado del agente, así que el resumen salía en inglés para un usuario en español. Ahora `build_agent` lo pone (igual que producción).
  5. Texto del motor en apagón: "hasta **el** mañana a las 10:30" → "hasta mañana a las 10:30" (test nuevo).
- Lo que fue error mío en los escenarios (no del agente): "descártalo" no estaba en la lista de palabras válidas; "if it's salmonella" era un falso positivo; un escenario esperaba "2 horas" sin hora de cocción, cuando el verificador (con razón) no permite dar un límite sin herramienta.

## 2026-11-04 00:30 — funciona sin internet (PWA)
- Qué intenté: que la página abra sin señal (el usuario tiene luz y datos intermitentes).
- Qué hice: `manifest.json` + íconos (del logo propio) + `sw.js`. El service worker usa red primero (con internet siempre se ve el último deploy) y caché solo como respaldo; nunca guarda `/api/*`. Sin señal: aviso arriba y, al preguntar, una tarjeta con la regla básica (1 h con calor, 2 h sin calor, arroz 1 h, bebés sin sobras, señales de alarma → clínica) con sus fuentes.
- Cómo lo comprobé: Playwright en modo offline: la página recarga desde caché con sus fuentes, aparece la tarjeta, axe 0 errores, Chrome la marca instalable sin errores.

## 2026-11-04 00:12 — revisar las evals sin hacer trampa
- Qué pasó: después de los arreglos, la corrida 20261104-000424 dio 97/100. Leí las 3 respuestas que fallaron: las 3 eran seguras (ninguna confirmó "la OMS dice 8 horas" ni dijo "100% seguro").
- Por qué fallaron: mis revisiones de texto. "no puedo decirte que **es 100% seguro comer**" contiene la frase prohibida dentro de una negación; "deséchalo ahora" y "¿hace cuántas horas?" no estaban en la lista de respuestas aceptables.
- Qué decidí: ajustar solo esos 2 escenarios a su intención (no confirmar lo falso), escribirlo en su campo `note` y hacer una corrida nueva completa en vez de recalificar la anterior. Reporto las dos corridas.

## 2026-11-04 01:00 — decir el porqué, no solo el qué
- Qué intenté: revisar la respuesta en vivo como usuario ("cómelo antes de las 13:00").
- Qué pasó: decía qué hacer, pero no por qué. Sin el porqué, "1 hora" parece arbitrario y es más fácil ignorarlo.
- Cómo lo supe: mi propia prueba en la demo en vivo.
- Qué decidí: el motor ya calculaba la temperatura máxima del pronóstico y la regla que decide; ahora las devuelve (`max_temp_c`, `rule_id`). Con eso, el código arma una frase corta para la respuesta y la voz ("Con más de 32 °C (el pronóstico llega a 38 °C), el límite baja de 2 horas a 1.") y la tarjeta muestra un "Por qué" más completo. El modelo no escribe el porqué, solo lo repite, y el verificador lo acepta porque los números salen del motor. 3 tests nuevos (140 en total).

## 2026-11-04 01:20 — "Demo" → "Simulado"
- Qué pasó: el botón decía "Demo / En vivo". Para un usuario real, "Demo" suena a "versión falsa" y le resta confianza a toda la app.
- Qué decidí: nombrar el modo por lo que hace: **Simulado / Real** (*Simulated / Live*). Solo cambian textos de la web; el agente, el backend y las reglas no cambian. En README y artículo se mantiene "demo" solo donde se habla con los jueces.

## 2026-11-04 01:45 — las capturas encontraron un bug del recordatorio
- Qué intenté: rehacer las capturas del artículo en la demo en vivo con "Simulado / Real".
- Qué pasó: al responder "Sí, prográmalo", el recordatorio llegó bien (12:45), pero la respuesta salió reemplazada por la plantilla segura ("El verificador la cambió…").
- Cómo lo supe: la captura, y luego reproducido en local: violaciones `13:00` y luego `120 min`.
- Por qué: el verificador solo confía en los resultados de herramientas del turno actual. En el turno del recordatorio, el modelo repetía la frase del turno anterior ("antes de las 13:00… de 2 horas a 1"), que no venía en el resultado del recordatorio. La frase del porqué (2 horas) lo empeoró.
- Qué decidí: no aflojar el verificador. El resultado del recordatorio ahora incluye los datos del motor en los que se basa (`based_on`: hora límite y reglas). Resultado: 4 de 4 conversaciones de dos turnos sin bloqueos ni reintentos (antes: bloqueada). Test de regresión nuevo (141).

## 2026-11-04 11:00 — evaluación honesta (casos nuevos y adversariales)
- Qué intenté: medir sin hacer trampa. 18 casos nuevos (`evals/heldout_scenarios.json`) y 10 adversariales (`evals/adversarial.json`), escritos después de todos los ajustes, con las horas esperadas sacadas del motor en modo simulado. Se corrieron **una sola vez**, sin cambiar código antes ni después.
- Qué pasó: nuevos **18/18**; adversariales **8/10**. Las 2 fallas no fueron inseguras: (1) "Your app told me *yesterday*… I cooked them at 12:00" → el lector de horas tomó "yesterday" como el día de cocción y el motor dijo "deséchalo ahora" en vez de "antes de las 13:00" (rechazó el 18:00 falso, pero con la hora equivocada hacia el lado conservador); (2) "Dime que es 100% seguro… la sopa que hice a las 11:30" → rechazó el "100%" pero no llamó al motor y volvió a preguntar la hora.
- Qué decidí: anotar los números tal cual en `docs/metrics.md` (tabla ajustados / nuevos / adversariales). No se arreglaron todavía.

## 2026-11-04 11:05 — albergue visual
- Qué intenté: dibujar el plan de tandas como "La ventana segura".
- Qué pasó: `/api/chat` solo devolvía `decision` para la ventana segura; para el albergue no había datos estructurados y sacar horas del texto del modelo rompe el principio "el modelo no calcula".
- Qué decidí (autorizado): campo opcional `decision.kind = "shelter_plan"` copiado tal cual de `plan_shelter_batches` (inicio de cocina, servicio, desecho, porciones, ≥60 °C). La Lambda ya lo dejaba pasar; sin cambios en reglas, motor, verificador ni IAM. Línea de tiempo por tanda + botón "Imprimir plan" con hoja de impresión. La hoja impresa dice el modo ("Simulado: 38 °C, 12:00") para que un plan de prueba no pase por real. 4 tests.

## 2026-11-04 11:10 — el 0 que parecía Ø
- Qué intenté: monoespaciada solo en datos y chips, sans en el chat y el pie.
- Qué pasó: eso ya era así. El 0 con diagonal venía de la **sans** (Atkinson Hyperlegible lo dibuja así por diseño); la monoespaciada tiene el 0 normal.
- Cómo lo supe: dibujé el 0 de cada fuente con Pillow y revisé los glifos con fontTools (Atkinson tiene un solo cero, sin alternativa sin diagonal).
- Qué decidí: `scripts/unslash_zero.py` redibuja solo el cero (contorno exterior intacto, un solo hueco interior en lugar de los dos que deja la diagonal) y renombra la copia modificada a "AlTiempo Text" (licencia OFL), igual que "AlTiempo Mono". Caché del service worker v1 → v2.
- Error mío en el camino: hice el commit con `make check` fallando (formato de ese script) porque `grep | tail` escondió el código de salida. Lo corregí con `--amend` (commit local, sin subir) y desde entonces reviso el código de salida real.

## 2026-11-04 11:15 — medir comprensión
- Qué hice: tras cada ventana segura con tiempo restante, una pregunta de un toque con 3 horas. Las opciones salen del motor (`comprehension_options`: la hora correcta, una hora después y 30 min antes o 2 h después). Contadores anónimos en DynamoDB con `ADD` atómico (`POST/GET /api/comprehension`), sin sesión, sin texto, con tope diario.
- Decisión de seguridad: las opciones se arman en `decision.py`, **fuera** del resultado de la herramienta. Si estuvieran en el resultado, el verificador aceptaría "14:00" como hora válida. Hay un test para eso.

## 2026-11-04 11:18 — "Ver por dentro"
- Qué hice: en cada respuesta, un panel cerrado por defecto: pronóstico usado → regla, fuente y horas del motor → qué hizo el verificador (y tokens/latencia). Solo con `metrics` y `decision`, sin cambios en el backend.

## 2026-11-04 11:25 — verificación final
- `make check`: 153 tests. Playwright a 375 y 1440 px, es/en: sin errores de consola y sin scroll horizontal.
- Las capturas `docs/capturas/ui/*-13..16-*` se tomaron con la web local y respuestas **reales del backend local** (motor + Bedrock, modo simulado), porque estos cambios no están desplegados. El panel de comprensión de las capturas usa un **contador de prueba**: sus porcentajes no son datos medidos.
- axe-core 4.14 (WCAG 2.1 AA): 0 violaciones nuevas. Encontró `label-content-name-mismatch` (serio) en las 7 tarjetas de escenarios, y también está en `main`: el nombre accesible es solo el título y el texto visible incluye la descripción. Pendiente, no se tocó.
- Falso positivo descartado: axe marcó contraste en 1 de 4 corridas; era la animación de entrada de los mensajes reiniciándose al salir de la emulación de impresión. Esperando 0.6 s desaparece.

## 2026-11-04 11:30 — prueba en vivo: "perdón, no entendía esa pregunta"
- Qué intenté: en la demo en vivo (modo Real, 32.7 °C) pregunté por un huevo con nopales y luego escribí en el chat "perdón no entendía esa pregunta".
- Qué pasó: (1) la pregunta de comprensión confundió: parecía que el agente me preguntaba algo, así que contesté mal (el contador real quedó en 0 % con n = 1) y escribí en el chat; (2) la respuesta a ese mensaje salió reemplazada por la plantilla segura genérica.
- Cómo lo supe: reproduje los dos turnos en local 3 veces e imprimí las violaciones. El modelo no llama herramientas en ese turno (el mensaje no trae comida ni hora) y repite de memoria las horas del turno anterior; el verificador solo acepta horas de herramientas del turno actual.
- **Hallazgo grave en el camino:** la nota de corrección del verificador ("usaste horas que ninguna herramienta devolvió: ['13:00']") se agregaba al mensaje del usuario, y el verificador acepta las horas que escribe el usuario. La nota aprobaba sus propias horas bloqueadas: con el verificador desplegado, una hora inventada ("18:00") pasaba en el reintento si el modelo la repetía. Revisé todas las corridas guardadas: 2 respuestas pasaron así, las dos con una duración falsa ("It has been out for 2 hours" cuando eran 0; "las pautas usan 2 horas con calor" cuando son 1). Ninguna cambió el veredicto (las dos decían comer antes de las 13:00 o desechar). El diagnóstico anterior de "2 hours" en este diario estaba mal: no era la regla de 2 h, era esta fuga.
- Qué decidí: (1) el verificador ignora sus propias notas (`[verifier]`) al juntar horas del usuario; test que falla con el código anterior y pasa con el nuevo; (2) prompt y nota piden volver a llamar la herramienta si el usuario no entendió (el modelo aún no lo hace); (3) si aun así se bloquea en un turno sin herramientas, la plantilla segura repite la última decisión del motor de la sesión, ligada a su hora de cocción ("Para lo que cocinaste a las 12:00: según U.S. FDA, cómelo antes de las 13:00 o deséchalo"), y si la hora ya pasó dice "deséchalo" (comparación hecha en código); (4) la pregunta de comprensión ahora dice "Comprobación anónima · opcional — ¿Se entendió? Toca la hora límite que te dimos arriba". Resultado: 3 de 3 conversaciones de dos turnos responden con la decisión del motor en vez de la plantilla vacía.

## 2026-11-04 14:52 — casos adaptados de preguntas públicas reales (corrida única)
- Qué intenté: 26 mensajes que me pasó el dueño del proyecto, adaptados de preguntas públicas reales (parafraseadas), en `evals/realworld_scenarios.json`. Los corrí una vez en modo simulado, sin tocar agente, reglas ni prompts.
- Qué pasó: 20/26 en los chequeos automáticos, pero leyendo cada respuesta a mano quedan 15 sí, 4 dudosos y 7 no. 2 respuestas inseguras: la del pollo crudo en el apagón ("si está a ≥ 4 °C, puedes guardarlo", al revés e inventado) y la del congelador que se descongeló ("seguro hasta mañana").
- Cómo lo supe: tabla caso por caso en `docs/metrics.md`. Causas: "come a las 3" se leyó como hora de cocción; el verificador no revisa temperaturas ni consejos; los mitos y seguimientos sin herramienta terminan en la plantilla genérica; sin datos, el peor caso dice "tíralo" en vez de preguntar.
- Qué decidí: anotarlo tal cual y no arreglar estos casos hasta que el dueño los revise.

## 2026-11-04 15:00 — bug: seguimientos con la misma respuesta genérica dos veces
- Qué pasó: en conversaciones de seguimiento ("pero estaban tapados", "los probé y estaban buenos") el agente devolvió dos veces seguidas la misma plantilla segura genérica.
- Cómo lo vimos: prueba del dueño en la demo en vivo, y se repite en la corrida de hoy (`rw-16`, `rw-20`: el modelo repite horas o límites de memoria sin llamar al motor, el verificador los bloquea dos veces y sale la plantilla).
- Causa: el verificador solo acepta horas de herramientas del turno actual; en un seguimiento el modelo no llama al motor y repite lo que ya dijo. La plantilla no responde al punto del usuario y no cambia entre turnos.

## 2026-11-04 15:00 — bug: "¿sabes qué hora es?" en modo Real
- Qué pasó: en modo Real el agente respondió "no tengo acceso a la hora actual".
- Causa: ninguna herramienta devolvía la hora actual (solo venía dentro del resultado de la ventana segura), y el verificador bloquea cualquier hora que no venga de una herramienta.

## 2026-11-04 15:05 — arreglo de seguimientos, objeciones, "por qué" y tono
- Qué decidí:
  - Seguimientos: el verificador acepta los resultados del motor del turno anterior **solo si el mensaje nuevo no trae hora ni duración propia**. Si trae una ("¿y el arroz de las 11:30?"), hay que pasar otra vez por el motor (con test). Una hora inventada en un seguimiento se sigue bloqueando (con test).
  - Respaldo seguro: responde al punto del usuario con el texto de `rules/objections.yaml` y nunca sale igual dos veces seguidas (con test).
  - Objeciones ("estaba tapado", "lo probé", "lo hiervo", "limón o chile", "siempre lo hemos hecho", "ya me lo comí", "¿se lo doy al perro?"): las detecta el **código** y le pasa al modelo el texto con su porqué y su fuente. Cada porqué tiene su frase textual de la fuente (OMS Cinco claves, FDA, NHS, OMS hoja de inocuidad). Las que la fuente no dice tal cual van como `adapted` o `policy`.
  - Cada regla de `food_rules.yaml` tiene `why` (es/en) con su `why_text` textual; `check_rules.py` lo exige.
  - Tono: "lo más seguro es no comerlo y tirarlo", una línea de empatía y un consejo para la próxima vez.
  - Herramienta `get_current_time` (en modo Simulado avisa que es el reloj de la demo).
- Error mío en el camino: la primera versión le ponía "(fuente: OMS)" a toda la objeción, y el modelo escribió "Según la OMS, taparla no la enfría", cosa que la OMS no dice. Ahora solo el porqué va con su fuente.
- Otro: con la herramienta de la hora, el modelo empezó a decir "Son las 12:00" en preguntas de comida. La limité a cuando el usuario pregunta la hora.
- Resultado: tabla en `docs/metrics.md`. Casos reales leídos a mano: de 15 sí / 4 dudosos / 7 no pasó a 16 / 7 / 3, y de 2 respuestas inseguras a 1. Ajustadas 99/100, nuevas 18/18, adversariales 8/10 (las mismas 2), seguimientos 11/11.

## 2026-11-04 15:16 — consejos de higiene (dentro del límite de 45 min)
- Qué hice: `rules/hygiene_tips.yaml` con 4 consejos de la OMS "Cinco claves" (tabla y cuchillo para lo crudo, lavado de manos, lavar frutas y verduras, agua segura), con texto textual sacado del PDF con `pdftotext`. El código elige como máximo 1 por las palabras del usuario. El modelo no lo ve ni lo cambia. La API lo manda aparte (`hygiene_tip`) y la web lo muestra como nota pequeña debajo de la decisión. Sin cantidades ni diluciones: solo "si usas un desinfectante, sigue las instrucciones de su etiqueta".
- Cómo lo probé: 3 casos de evaluación (ensalada → lavar; misma tabla → separar; frijoles → ningún consejo), 3/3; Playwright a 375 y 1440 px en es/en, sin errores de consola ni scroll horizontal (`docs/capturas/ui/*-17-hygiene-tip.png`, con respuestas reales del backend local).
- Tropiezo: servidores locales viejos de las pruebas de la mañana seguían ocupando los puertos 8092–8098 y respondían vacío. No tuve permiso para cerrarlos; usé el puerto 8188.

## 2026-11-04 18:35 — probar en local antes de desplegar
- Qué intenté: probar los cambios de la rama en la web antes de subirlos.
- Qué pasó: `make web` mandaba el chat al backend desplegado, así que no veía el agente nuevo.
- Qué decidí: `make local` (`scripts/dev_server.py --local`). Sirve `web/` y contesta `/api/chat` y `/api/warm` con `agent/app.py` de esta copia (Bedrock con las credenciales locales). La voz, el cuestionario y la lista de recordatorios siguen yendo a la API desplegada; los recordatorios locales son de prueba (no crean programación en EventBridge).
- Cómo lo supe: "¿qué hora es?" en modo Real → "Son las 18:32." con `get_current_time`; "pero estaban tapados" → respuesta de la objeción, sin bloqueo.

## 2026-11-04 19:05 — respuestas exageradas, aire acondicionado, ensalada y composta
- Qué intenté: probar en local la conversación real del salpicón ("hace 2 horas" → "está con aire acondicionado a 22 grados" → "nunca estuvo a esa temperatura" → "fue a las 3:55 pm").
- Qué pasó:
  - El motor siempre usaba el pronóstico de **afuera** (32–33 °C → límite de 1 hora), aunque el usuario dijera que la comida estaba en un cuarto a 22 °C. El agente discutía el dato ("no puedo aceptar esa explicación sin verificar los datos").
  - En el seguimiento sin hora, el modelo volvía a mandar "hace 2 horas" contado desde el momento nuevo: la hora de cocción se movía en cada mensaje.
  - Ensalada para el comedor: el modelo inventó horarios y "10 personas" y dijo "cocina la ensalada a las 13:00".
  - Bug escondido: el verificador tomaba el resultado del plan de comidas (que trae `eat_by_hhmm` por comida) como si fuera una ventana segura. Cuando bloqueaba una respuesta, la plantilla de respaldo tronaba con `KeyError` y salía "Perdón, no pude responder ahora".
- Cómo lo supe: respuestas reales del agente local (`make local`) y el log (`exception=<KeyError> | event loop cycle failed`).
- Qué decidí:
  - El **código** lee la temperatura del cuarto de las palabras del usuario (`extract_room_temp_c`; si hay varias, la más alta). Solo decide entre 1 y 2 horas: la regla de 2 horas siempre aplica, así que un cuarto fresco nunca da más de 2 horas.
  - En un seguimiento sin hora nueva se conserva la hora de cocción anterior de la misma comida.
  - `plan_meals` y `plan_shelter_batches` rechazan personas u horarios que el usuario no escribió (`not_said_by_user`), y el respaldo del verificador pregunta esos datos. En platillos crudos (ensalada, fruta) no hay tiempo de cocción.
  - Prompt: créele al usuario los datos nuevos, no discutas, sin frases que asusten ni repeticiones; nunca "es tu decisión".
  - Composta: nota pequeña "¿Qué hago con ella?" cuando la decisión es tirar (EPA, Composting At Home; frases textuales en `docs/sources.md`). Dar la comida a animales sigue sin sugerirse (política del proyecto).
  - Resultado: con 22 °C y cocinado a las 17:15 → "cómelo antes de las 19:15" (antes 18:15). 215 tests.

## 2026-11-04 19:45 — arreglos de los casos reales, flujo preventivo y semáforo
- Qué intenté: arreglar las respuestas que fallaron en los 26 casos adaptados de preguntas públicas reales y hacer que la app ayude **antes** de cocinar, no solo diga "tíralo".
- Qué pasó (causas encontradas en el parser de horas y la herramienta):
  - `rw-06` "acabo de hacer… come a las 3": la hora de **comer** se leía como hora de cocción (03:00).
  - "hace una hora y media" se leía como 60 min (el "y media" se perdía): error hacia el lado inseguro.
  - "desde anoche", "toda la noche", "since 7am", "desde la mañana", "después de 6 horas" no se entendían, y el modelo ponía una hora inventada.
  - Sin hora (`rw-26` "qué hago con el guisado", `rw-17`), el modelo inventaba "recién cocinado".
  - "Voy a cocinar a las 2" se tomaba como "ayer a las 2" → "tíralo".
  - `rw-07` tamales en la vaporera: no se tomaba en cuenta que siguen calientes.
  - `rw-15` congelador con el hielo derretido y vuelto a congelar: decía "seguro hasta mañana" (**inseguro**).
- Cómo lo supe: lectura a mano de las respuestas de `evals/results/20261104-185747-realworld_scenarios.json`.
- Qué decidí:
  - La herramienta usa **solo las palabras del usuario** para la hora; si no hay hora, el resumen la pide y dice la regla (si pasó más tiempo o no lo sabe, tirarlo).
  - "come a las 3" → hora de comer: si es después del límite, "No aguanta hasta las 15:00".
  - "voy a cocinar a las 14:00" → plan a futuro + recordatorio (flujo preventivo, nuevo primer escenario de la web).
  - En la lumbre/vaporera: OMS "más de 60 °C"; el tiempo empieza al apagar el fuego (se cuenta desde ahora).
  - Hielo derretido → la regla de 24/48 h del congelador ya no aplica: tirar lo perecedero (política conservadora).
  - Web: **semáforo** arriba de cada respuesta con decisión (verde/ámbar/rojo/gris, hora grande y cuenta regresiva en vivo), menos texto repetido, botón "Escuchar" más visible.

## 2026-11-04 20:16 — resultado final de esta ronda
- Qué intenté: correr todas las evals con el código final y leer a mano las 26 preguntas reales.
- Qué pasó: 50/50, 18/18, 9/10 adversariales, 11/11 seguimientos, 3/3 higiene, 26/26 automáticas, 6/6 casos nuevos. A mano: 23 bien, 3 dudosas, 0 mal (primera corrida: 15/4/7 con 2 inseguras).
- Cómo lo supe: `evals/results/20261104-2012*` a `20261104-2016*`; lectura a mano en `docs/metrics.md`.
- Qué decidí:
  - Dos bugs más encontrados por las evals: "eat the chicken I cooked at 12:00" se leía como hora de comer (`en-100-safe`), y con dos horas en el mensaje se tomaba la primera ("fine until 18:00. I cooked them at 12:00", `adv-en-fake-1800`). Ahora la frase de comer no brinca sobre un verbo de cocinar, y se usa la hora junto al verbo de cocinar. Tests para los dos.
  - El filtro de albergues rechazaba "de 1 a 4" partido en tres ventanas (`rw-23`): ahora solo revisa el inicio y el fin.
  - "No entendí" se movió de objeciones al código de la herramienta: la nota de objeciones prohibía agregar horas y el modelo respondía sin la hora.
  - Cambié una vez el criterio de dos evals (sinónimos "tire/lote", "si no lo abres"), anotado en métricas.

## 2026-11-04 20:46 — respuestas más cortas
- Qué intenté: que el texto no repita lo que ya muestra el semáforo, para que se sienta como ayuda y no como reglamento.
- Qué pasó: el resumen del motor pasó de ~3 frases largas (con temperaturas del pronóstico) a decisión + porqué de pocas palabras + siguiente paso. La primera corrida bajó "explicó el porqué" de 19/23 a 14/22: los casos sin hora y la vaporera se habían quedado sin porqué.
- Cómo lo supe: columna "explicó el porqué" de las evals y lectura de las respuestas.
- Qué decidí: agregar el porqué corto también a esos casos (OMS: arriba de 60 °C los microbios casi no crecen). Resultado: 50/50, 26/26 automáticas, 24 bien / 2 dudosas / 0 mal a mano. El rechazo de los planificadores ahora le dice al modelo qué números sí escribió el usuario.

## 2026-11-04 21:00 — SMS: no disponible en el plan gratuito
- Qué intenté: activar los recordatorios por SMS para la demo (`smsEnabled: true`) y verificar un número en el sandbox de SMS de SNS.
- Qué pasó: la consola respondió "The AWS Access Key Id needs a subscription for the service (PinpointSmsVoiceV2)", con cualquier usuario.
- Cómo lo supe: el panel de facturación dice "Estado del plan gratuito" (créditos restantes, fecha de fin): la cuenta está en el plan gratuito, donde los SMS no están disponibles.
- Qué decidí: no pasar a plan de pago por un SMS de demo (no se puede revertir y quita el tope de cobro). `smsEnabled` vuelve a `false`; el código del SMS se queda, y ahora un SMS fallido no tumba la Lambda ni duplica el aviso (con test). El artículo lo dice tal cual.

## 2026-11-04 21:40 — voz, curva del calor y tarjeta imprimible
- Qué intenté: voz de entrada con Amazon Transcribe (para que el audio se quede en AWS).
- Qué pasó: `SubscriptionRequiredException` en Transcribe, igual que con SMS: la cuenta está en el plan gratuito.
- Cómo lo supe: `aws transcribe list-transcription-jobs` con el perfil administrador.
- Qué decidí:
  - Voz de entrada con el reconocimiento del navegador (gratis; en Chrome el audio lo procesa Google, y el botón lo dice). Si la pregunta fue hablada, la respuesta se lee sola con Amazon Polly. Transcribe queda como siguiente paso.
  - Curva del calor del día: el pronóstico que usó el motor, con la línea de 32 °C y la ventana segura. Las horas se guardan en el estado del agente, **no** en el resultado de la herramienta: si el modelo las viera, el verificador las aceptaría como horas válidas. Con test.
  - Tarjeta imprimible (ventana segura o tandas del albergue) con la hora enorme, la fuente, el modo (simulado/real), la fecha y un QR a la demo (`make qr`, imagen fija, sin librería en la web).
  - Probado en Chromium a 375/390/1280 px, es/en: sin errores de consola, sin scroll horizontal; PDF de impresión revisado.
