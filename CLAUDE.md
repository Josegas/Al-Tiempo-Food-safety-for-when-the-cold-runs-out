# CLAUDE.md — Proyecto "Al Tiempo" (hackathon Strands SDK: Workshop to Ship)

> Este archivo es la guía principal para Claude Code. Léelo completo antes de escribir código.
> Nombre de trabajo: **Al Tiempo** (en México "al tiempo" = a temperatura ambiente). Puede cambiar.

---

## 0. Quién soy y cómo quiero que trabajes conmigo

- Soy estudiante de Ingeniería en Sistemas (software). Me interesa más **la nube (AWS)** que programar; no soy muy fuerte escribiendo código.
- Háblame en **español**, claro y sin jerga innecesaria.
- Después de cada paso importante:
  1. Resume **qué hiciste y por qué** (2–5 líneas).
  2. Dame los **comandos exactos** que debo correr y qué debo ver si funcionó.
  3. Dime si conviene **tomar una captura de pantalla** (hito, consola, despliegue, prueba pasando).
- Si algo se puede hacer de dos formas, elige la más simple que cumpla los requisitos y explícame la decisión en una línea.
- **No agregues funciones fuera de la lista de la sección 4 sin preguntarme.**
- Tengo poco tiempo: prioriza que funcione de punta a punta antes de pulir.

---

## 1. El hackathon (reglas que NO podemos romper)

**Hackathon:** Strands SDK: Workshop to Ship (AWS Builder Center).
**Reto:** construir y publicar un agente de IA de **impacto social** con el **Strands Agents SDK**, con mejoras **medibles** para poblaciones desatendidas (áreas: educación, salud o resiliencia climática). Nuestro proyecto: **salud + resiliencia climática**.

### Fechas (hora de Culiacán, UTC-7)
- **Cierre seguro: miércoles 4 de noviembre de 2026, 23:59** (el encabezado dice GMT-8 y las reglas dicen PDT; usamos la más temprana).
- **Meta interna: entregar el 4 de noviembre antes de las 20:00.**
- **Congelar funciones: 4 de noviembre a las 12:00.** Después solo se mide, se documenta y se arreglan bugs.
- La evaluación dura hasta el **27 de noviembre**: todo debe seguir funcionando hasta esa fecha (ojo con costos).

### Requisitos de pasa/no pasa
- [ ] Completar el workshop oficial con el sandbox gratuito dentro de la ventana del hackathon (lo hago yo).
- [ ] Agente construido con **Strands Agents SDK** que resuelve un problema real de impacto social.
- [ ] **Corre en AWS.**
- [ ] **Repositorio público** con **licencia aprobada por OSI** → usamos **MIT** (archivo `LICENSE` desde el primer commit).
- [ ] **Artículo** del proyecto en Builder Center (en **inglés**).
- [ ] **Video público de menos de 3 minutos** en YouTube, Vimeo, Facebook Video o Youku. Sin música con copyright ni marcas de terceros. Los jueces no ven más allá de los 3 minutos.
- [ ] Proyecto **original**, no publicado antes.
- [ ] Una entrada por persona.

### Rúbrica (25% cada criterio)
| Criterio | Qué buscan | Cómo lo demostramos |
|---|---|---|
| Social impact | Mejora medible para población desatendida | Usuario concreto, cifras con fuente, métricas propias |
| Technical execution | Strands bien usado y que funcione | Despliegue vivo, tests, evals, modo demo, manejo de errores |
| Communication | Artículo y video claros, que den ganas de probar | "Try it in 1 minute", capturas, retos reales, lo aprendido |
| Originality | Arquitectura original, uso novedoso de AWS, más allá del workshop | Tabla "Workshop vs. lo que agregamos" |

**Gate 1 incluye calificación con IA:** el artículo debe usar títulos con las palabras de la rúbrica y poner los números **en texto**, no solo en imágenes.

### Lo que el workshop ya enseña (NO cuenta como extra)
Agent loop + tools, hooks, skills + steering, session managers, despliegue en AgentCore Runtime, multi-agente, evals.
**Lo que sí cuenta como extra:** EventBridge Scheduler para recordatorios a futuro, motor de reglas con fuentes oficiales, modo apagón, planificador de albergues, voz con Polly, verificador de mensajes, DynamoDB con TTL, SMS.

---

## 2. El problema (con evidencia)

Comer comida que estuvo demasiado tiempo a temperatura ambiente enferma, sobre todo a niños pequeños, y el calor lo empeora. Unos 1,085 millones de personas pobres (339 M rurales + 746 M urbanas, suma nuestra) están en alto riesgo por falta de acceso a enfriamiento (Chilling Prospects 2026), y 655 millones no tienen electricidad. En India, aun en zonas rurales, el celular es mucho más común que el refrigerador (91.5% vs 25.2%, NFHS-5 reportado por prensa).

**Datos para el artículo — VERIFICADOS el 2026-11-03 (detalle, frases textuales y links en `docs/sources.md`). Solo usar cifras que estén en ese archivo:**
- OMS (hoja del 4 jun 2026): **866 millones** se enferman al año por comida contaminada (casi 1 de cada 9 personas) y **1.52 millones** mueren; los menores de 5 años cargan el **29%** del daño, con **143 000 muertes en 2021**. https://www.who.int/news-room/fact-sheets/detail/food-safety
- Calor: los casos de salmonelosis aumentan de forma lineal con la temperatura por encima de 6 °C (Kovats et al., 2004, 10 poblaciones europeas). https://pmc.ncbi.nlm.nih.gov/articles/PMC2870124
- Sin electricidad: **655 millones** de personas en 2024; África concentra el **88.8%** (Tracking SDG7 2026, SEforALL, julio 2026).
- Sin refrigeración/enfriamiento: **339 millones** de pobres rurales y **746 millones** de pobres urbanos en alto riesgo, en 77 países expuestos al calor (Chilling Prospects 2026, SEforALL, vía UNEP Cool Coalition).
- India (NFHS-5, 2019–21, reportado por The Tribune): 37.9% de los hogares tiene refrigerador (25.2% rural) y 93.3% tiene celular (91.5% rural). ⚠️ Fuente secundaria: confirmar en el reporte primario o citar como "reportado por".
- **Eliminadas por no tener fuente primaria:** "<30% de hogares africanos con refrigerador" y ">86% con celular en África". Las cifras viejas de la OMS (600 M / 420 000 / 125 000) ya no se usan.

**Lo que existe hoy (para la sección "Existing solutions" del artículo):**
- USDA FoodKeeper: dice cuánto dura la comida en refrigerador, congelador o alacena. **Da por hecho que hay refrigerador.**
- Reglas generales (OMS "Cinco claves", FDA/USDA): no dejar comida cocida más de 2 h a temperatura ambiente; 1 h si hace más de 90 °F (32.2 °C).
- No encontramos ninguna herramienta que aplique esas reglas al pronóstico del día para un hogar sin refrigerador, ni que planee tandas de cocina para albergues sin refrigeración.
- **Nunca digas "somos los primeros".** Di "no encontramos una herramienta que…".

**Usuarios:**
- Principal: hogares sin refrigerador o con luz intermitente (India rural, África subsahariana, zonas rurales y asentamientos informales en general).
- Secundarios: familias con refrigerador durante apagones; **albergues y comedores comunitarios** después de desastres; promotoras de salud.

---

## 3. Principio de diseño (memorizar)

> **"El modelo conversa y explica. Las reglas oficiales deciden. Ante la duda, lo más seguro."**

Reglas duras:
1. **El LLM nunca calcula horas, límites ni temperaturas.** Todo eso sale del motor de reglas (código puro, con tests).
2. **Cada regla tiene fuente oficial** (`source_name`, `source_url`, `verified_on`). **No inventes fuentes ni URLs.** Si no puedes verificar una regla en su fuente oficial, márcala como `unverified: true` y avísame; no la uses en producción.
3. **Conservador por defecto:** si falta un dato (tipo de comida, temperatura, hora), se asume el peor caso razonable (calor > 32 °C → límite de 1 h).
4. **Nunca decir que algo es "100% seguro".** La forma correcta es: "Según [regla/fuente], cómelo antes de las HH:MM o deséchalo".
5. **No diagnosticar ni dar dosis de medicamentos.** Ante señales de alarma: mandar a la clínica o al número de emergencia del país.
6. **Bebés y niños pequeños: reglas más estrictas** (preparar al momento, no guardar sobras).
7. **Verificador antes de responder:** un hook de Strands revisa que toda hora o límite en la respuesta del modelo coincida con lo que devolvió el motor de reglas. Si no coincide, se bloquea y se regenera o se usa una plantilla segura. (Revisa en la documentación de Strands o en el Módulo 2 del workshop los nombres exactos de los eventos de hooks; no los adivines.)

---

## 4. Alcance (lo que SÍ construimos)

### Funciones en esta versión
1. **Ventana segura + recordatorios (núcleo).** El usuario dice qué cocinó y a qué hora → el motor calcula "cómelo antes de / deséchalo después de" con el pronóstico por hora → se programa un recordatorio.
2. **Planear porciones y horarios.** Según el calor del día, las comidas y cuántas personas: a qué hora cocinar y cuánto, para que no sobre comida al tiempo.
3. **Modo apagón.** Para quien sí tiene refrigerador y se quedó sin luz: cuenta el tiempo desde que se fue la luz y aplica las reglas oficiales de apagones (refrigerador cerrado / congelador lleno o a medias). Verificar en USDA FSIS.
4. **Modo estricto para bebés y niños pequeños.** Reglas más conservadoras. Para fórmula infantil, usar la guía oficial (verificar en CDC/OMS).
5. **Albergues y comedores comunitarios.** Entrada: número de personas, horarios de servicio, platillos y si hay fuente de calor para mantener caliente (≥ 60 °C según la OMS). Salida: plan de **tandas escalonadas** (cuándo empezar cada tanda y cuánto cocinar) para que nada se sirva fuera de la ventana segura, más alertas de "desechar" por tanda. Pensado para el coordinador o la cocinera.
6. **Escalada ante señales de alarma.** Si alguien tiene diarrea o vómito, preguntas fijas basadas en las señales de deshidratación de la OMS (verificar en la guía oficial). Si hay alguna señal de alarma → "ve a la clínica ahora / llama al número de emergencia". Sin diagnóstico ni dosis.

### Idiomas
- Interfaz y respuestas en **inglés y español** (selector). Configurable para agregar más idiomas después.
- README y artículo en inglés.

### Fuera de alcance (va en "Next steps" del artículo)
Compras inteligentes, avisos masivos de promotoras, escuelas, más idiomas, WhatsApp, refrigeradores de barro, app móvil nativa.

---

## 5. Arquitectura

```
Usuario (web / SMS / voz)
   │
   ▼
Web estática (S3 + CloudFront)  ──►  API (API Gateway + Lambda)  ──►  Agente Strands en AgentCore Runtime
                                                                        │
                    ┌───────────────────────────────────────────────────┼─────────────────────────────┐
                    ▼                       ▼                           ▼                             ▼
          get_forecast (Open-Meteo,   rules_engine (código puro:   schedule_reminder              synthesize_voice
          o fixture en modo demo)     ventana segura, apagón,      (EventBridge Scheduler        (Amazon Polly)
                                      bebés, albergues, alarma)     → Lambda → SNS SMS / web)
                                            │
                                            ▼
                                   DynamoDB (comidas, recordatorios, planes; TTL para borrar datos)
   Hook verificador: compara la respuesta del modelo con la salida del motor de reglas antes de enviarla.
```

### Servicios AWS y por qué
| Servicio | Para qué | Por qué este |
|---|---|---|
| Amazon Bedrock | Modelo de lenguaje | Requerido por el ecosistema Strands/AgentCore; modelo configurable por variable de entorno (elegir uno barato disponible en la cuenta/región) |
| AgentCore Runtime | Correr el agente | Despliegue visto en el workshop, sin servidores que mantener |
| EventBridge Scheduler | Recordatorios a una hora exacta del futuro | Programaciones de una sola vez que se borran solas al ejecutarse; el agente sigue actuando aunque el usuario cierre la app |
| Lambda | Enviar el recordatorio | Barato y simple |
| SNS (SMS) | Avisar a celulares básicos | El usuario objetivo tiene celular, no smartphone garantizado. En sandbox solo envía a números verificados: suficiente para la demo |
| DynamoDB | Guardar comidas, planes y recordatorios | Serverless; **TTL** para borrar datos personales automáticamente |
| Amazon Polly | Respuestas por voz | Para quien lee poco |
| S3 + CloudFront | Web de la demo | Estático, barato, link público para los jueces |
| CloudWatch + AWS Budgets | Logs, métricas y alerta de costos | Debe vivir hasta el 27 de noviembre sin sorpresas |

### Herramientas del agente (tools)
- `get_forecast(lat, lon)` → temperaturas por hora. En `DEMO_MODE` usa `fixtures/`.
- `compute_safe_window(food_type, cooked_at, storage, audience, location)` → `{eat_by, discard_at, rule_ids, sources, assumptions}`.
- `plan_meals(people, meal_times, dishes, location)` → horarios de cocción y porciones sugeridas.
- `track_outage(outage_started_at, fridge_door_opened, freezer_fullness)` → qué sigue dentro de la regla y qué no.
- `plan_shelter_batches(people, service_windows, dishes, can_hot_hold)` → tandas con hora de inicio, cantidad y hora de desecho.
- `schedule_reminder(at, message, channel, contact)` → crea la programación en EventBridge Scheduler.
- `check_danger_signs(answers)` → `{escalate: bool, message_id}` con número de emergencia por país.
- `synthesize_voice(text, language)` → audio con Polly.

**Todas las funciones que calculan algo son deterministas y tienen tests.** El modelo solo decide qué herramienta llamar y cómo explicar el resultado.

### Reglas en datos, no en código
Archivo `rules/food_rules.yaml`. Cada regla:
```yaml
- id: WHO_COOKED_2H
  description: "Cooked food should not stay at room temperature more than 2 hours"
  applies_to: [cooked_food]
  condition: {storage: none}
  limit_minutes: 120
  source_name: "WHO - Five Keys to Safer Food"
  source_url: "<URL oficial verificada>"
  verified_on: "2026-11-03"
  unverified: false
```
Reglas a verificar en su fuente oficial antes de usarlas (✅ las 11 verificadas el 2026-11-03 con frase textual; para las de USDA se usan las páginas equivalentes de la FDA porque FSIS bloquea lectores automáticos — ver `docs/sources.md`):
- OMS "Cinco claves para la inocuidad de los alimentos": límite de 2 h, mantener caliente (> 60 °C), recalentar hasta que eche vapor, no descongelar a temperatura ambiente.
- USDA FSIS: 1 h cuando hace más de 32 °C (90 °F).
- USDA FSIS: apagones (cuánto tiempo mantiene la comida un refrigerador cerrado; congelador lleno vs. a medias).
- CDC/OMS: preparación y uso de fórmula infantil.
- OMS (AIEPI/IMCI): señales de deshidratación y de alarma.
- Arroz cocido: guía oficial sobre *Bacillus cereus* (por ejemplo, NHS).

---

## 6. Estructura del repositorio

```
al-tiempo/
├── CLAUDE.md
├── README.md                 # en inglés, con "Try it in 1 minute"
├── LICENSE                   # MIT
├── .gitignore                # incluye .env, __pycache__, cdk.out, etc.
├── .env.example              # sin secretos reales
├── agent/
│   ├── app.py                # entrypoint de AgentCore Runtime
│   ├── agent.py              # creación del agente Strands
│   ├── prompts/              # system prompts en/es
│   ├── tools/                # una tool por archivo
│   └── hooks/verifier.py     # verificador de mensajes
├── rules/                    # food_rules.yaml, danger_signs.yaml
├── fixtures/                 # pronósticos de demo (día de 38 °C, apagón, etc.)
├── infra/                    # IaC (AWS CDK en Python)
├── web/                      # index.html + JS: chat, selector en/es, banner de modo demo
├── evals/                    # scenarios.json, run_evals.py, results/
├── tests/                    # pytest del motor de reglas y tools
└── docs/
    ├── diario.md             # diario de desarrollo
    ├── capturas/
    ├── architecture.png
    └── metrics.md            # números finales para el artículo
```

---

## 7. Convenciones de código

- Python 3.11+, `strands-agents`, `boto3`. Type hints. `pytest` para tests y `ruff` para formato.
- Antes de usar una API de Strands o de AgentCore, **revisa la documentación actual o los patrones del workshop**; no inventes nombres de clases o eventos.
- Configuración por variables de entorno: `MODEL_ID`, `AWS_REGION`, `DEMO_MODE`, `TABLE_NAME`, `SMS_ENABLED`, etc.
- **Nunca subas secretos.** Nada de llaves, tokens ni números de teléfono reales en el repo.
- Commits pequeños y descriptivos. Repo público desde el primer commit, siempre desplegable en `main`.
- Manejo de errores: si falla el pronóstico, usar el peor caso (límite de 1 h) y decírselo al usuario.
- Privacidad: datos mínimos; sin nombres; el teléfono solo si se piden recordatorios por SMS; TTL de 7 días en DynamoDB.

---

## 8. Modo demo (obligatorio)

- `DEMO_MODE=true`: usa pronósticos guardados en `fixtures/` (un día de calor de 38 °C, un apagón por tormenta y un albergue con 120 personas) y un **reloj acelerado** para que los recordatorios lleguen en segundos y no en horas.
- La web muestra un banner "Demo mode" y botones de escenarios listos para que el juez pruebe en 1 minuto, sin login.
- Debe verse bien en celular.

---

## 9. Pruebas, evals y métricas (para el artículo)

1. **Tests del motor de reglas** (`tests/`): cada regla, con casos frontera (exactamente 32 °C, exactamente 2 h, falta de datos → peor caso).
2. **Evals de punta a punta** (`evals/scenarios.json`, 40–60 escenarios en inglés y español). Incluye hogares sin refrigerador, apagones, bebés, albergues y señales de alarma. Para cada uno se guarda la decisión esperada según las reglas.
3. **Pruebas adversariales:**
   - Inyectar respuestas del modelo con horas inventadas → el verificador debe bloquearlas todas.
   - Usuarios que presionan ("¿le doy a mi bebé el arroz de hace 5 horas?") → nunca "sí".
   - Pedidos de dosis o diagnóstico → rechazo amable y escalada.
4. **Métricas a reportar en `docs/metrics.md`:**
   - % de reglas correctas en tests (meta: 100%).
   - % de respuestas del agente consistentes con el motor (X de Y escenarios).
   - Respuestas inseguras bloqueadas (N de N).
   - Recordatorios entregados a tiempo (N de N en la demo).
   - Latencia (mediana) y **costo por conversación** en USD.
5. **Error real medido:** documenta al menos un problema real (qué falló, cómo lo detectamos, qué cambiamos y cuánto mejoró). Es de lo que más confianza da.

---

## 10. Diario y capturas

Cada vez que algo falle o tomemos una decisión, agrega una entrada a `docs/diario.md`:
```
## 2026-11-03 21:40
- Qué intenté:
- Qué pasó:
- Cómo lo supe:
- Qué decidí:
```
Recuérdame tomar capturas en: primer despliegue, tests pasando, evals, recordatorio llegando, demo del albergue, consola de costos.

---

## 11. Costos y operación

- Crear una **alerta de AWS Budgets** (por ejemplo, 10 USD) antes del primer despliegue.
- Modelo barato por defecto; registrar tokens por conversación.
- Nada de recursos encendidos 24/7 que cobren por hora si no hacen falta.
- Mantener todo vivo hasta el **27 de noviembre de 2026** y no hacer cambios grandes mientras evalúan.

---

## 12. Plan de tiempo

| Cuándo (hora de Culiacán) | Qué |
|---|---|
| Mar 3, tarde | Yo hago el workshop (requisito). |
| Mar 3, noche | Repo + LICENSE + motor de reglas con tests + get_forecast + agente local funcionando. |
| Mar 3, madrugada | Recordatorios (EventBridge), apagón, albergues, señales de alarma, verificador; despliegue en AgentCore Runtime. |
| Mié 4, mañana | Web + Polly + modo demo + evals y métricas. **Congelar funciones a las 12:00.** |
| Mié 4, tarde | README, artículo y video. |
| Mié 4, antes de 20:00 | Entregar y revisar todos los links en incógnito y desde el celular. |

---

## 13. Artículo (inglés) — estructura

Usar estos títulos (coinciden con la rúbrica):
1. Título que diga qué hace y para quién.
2. The problem (una escena concreta + 2–3 cifras con fuente).
3. **Try it in 1 minute** (link de la demo, link del repo, pasos exactos).
4. What it does (las 6 funciones, con capturas).
5. How it works (diagrama + tabla "Servicio | Para qué").
6. **Social Impact** (usuarios, cifras, métricas).
7. **Technical Execution** (tests, evals, despliegue, verificador).
8. **Originality** (tabla "What the workshop taught vs. what we added").
9. Existing solutions (FoodKeeper y guías) y qué hueco cubrimos.
10. Challenges and a real error we measured.
11. Cost.
12. Limitations and next steps (sin rodeos).
13. What I learned.
14. How AI was used (declarar que se usó Claude Code para programar).

Tono: concreto y verificable; sin superlativos sin respaldo; honesto sobre lo que falta.

## 14. Video (< 3 min)

| Tiempo | Contenido |
|---|---|
| 0:00–0:15 | El problema con una escena: una mamá sin refrigerador, un día de calor. |
| 0:15–1:30 | Demo real: ventana segura → recordatorio que llega → modo apagón → plan del albergue. |
| 1:30–2:15 | Cómo funciona: reglas oficiales + verificador + EventBridge. |
| 2:15–2:45 | Un número medido e impacto. |
| 2:45–3:00 | Qué sigue y dónde probarlo. |

Subtítulos en inglés. Sin música con copyright.

---

## 15. Checklist final antes de entregar

- [ ] Repo público con LICENSE MIT, README y sin secretos ni archivos sueltos.
- [ ] Demo abre en incógnito, sin login, y funciona desde el celular.
- [ ] Video público y menor a 3 minutos.
- [ ] Artículo publicado en Builder Center con todos los links.
- [ ] Cada criterio de la rúbrica tiene su sección con evidencia.
- [ ] Alerta de presupuesto activa; todo vivo hasta el 27 de noviembre.
