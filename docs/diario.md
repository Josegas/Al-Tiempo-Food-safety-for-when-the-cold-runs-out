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
