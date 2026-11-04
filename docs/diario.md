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
