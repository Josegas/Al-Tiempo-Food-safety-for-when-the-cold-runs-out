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
