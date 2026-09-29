# Contexto del proyecto: Demos de portafolio para Upwork


## Contexto general

### Quién soy y para qué es esto
Soy un desarrollador freelance en Chile armando mi perfil de Upwork. Mi posicionamiento es:
**"Python & AI Integration Developer | LLM Chatbots, APIs & Automation"**.

Estas demos son **proyectos de portafolio**. Su objetivo es que un cliente de Upwork (normalmente dueño de negocio o gerente, no siempre técnico) vea en 2 minutos que sé resolver un problema de negocio real con IA y backend.

### Cómo quiero trabajar contigo
- **Quiero entender todo lo que construimos.** Antes de cada paso importante, explícame brevemente qué vas a hacer y por qué. Cuando tomes una decisión de arquitectura, dime la alternativa que descartaste. En entrevistas me van a preguntar por este código.
- Avanza en pasos pequeños y verificables. Después de cada paso, dime cómo probarlo.
- Si algo es ambiguo, pregúntame antes de asumir.
- Conversa conmigo en **español**. Todo lo que ve el cliente (código, comentarios, README, interfaz, commits) va en **inglés**.

### Stack por defecto
- Python 3.12+, **FastAPI**, Pydantic
- PostgreSQL (Supabase o Neon en plan gratis) cuando se necesite base de datos
- LLM: API de Anthropic u OpenAI, con el proveedor configurable por variable de entorno
- Frontend mínimo: HTML + HTMX o una página simple; nada de frameworks pesados salvo que lo pida
- Docker para correr local y desplegar
- Tests con pytest para la lógica central
- Despliegue en plan gratis: Render, Railway o Fly.io

### Estándares de calidad (esto es lo que me diferencia)
- Código limpio, tipado, con nombres claros y funciones cortas.
- Configuración por variables de entorno, con un `.env.example`. **Nunca** credenciales en el repo.
- Manejo de errores visible y amigable: si la API del LLM falla, la demo lo dice claramente, no se rompe.
- Logs básicos.
- README profesional (plantilla abajo).
- Commits pequeños y descriptivos en inglés.

### Reglas para demos públicas
- **Límite de uso:** la demo desplegada debe tener rate limiting (por IP) y un tope de tokens por request, para que nadie me genere una cuenta enorme en la API. Usa el modelo más barato que funcione bien.
- **Datos ficticios y claramente marcados.** Las empresas de ejemplo son inventadas y la interfaz debe decir "Demo project with sample data". No usar nombres ni marcas de empresas reales.
- Botón o texto de "Reset demo" cuando la demo guarde datos.

### Plantilla de README
1. **Título + una línea** de qué problema resuelve (en lenguaje de negocio).
2. **Live demo** (link) + GIF o captura.
3. **The problem** — 2 o 3 líneas.
4. **The solution** — cómo funciona, con un diagrama simple (Mermaid).
5. **Tech stack**.
6. **Key decisions** — 3 a 5 bullets explicando decisiones técnicas y por qué.
7. **Run locally** — pasos exactos.
8. **What I'd add for production** — muestra criterio (auth, monitoreo, escalado, costos).
9. Nota: "Demo project built for portfolio purposes."

---

## Especificación de la demo

### Demo 1 — AI Document Assistant (RAG Chatbot)
**Escenario:** una clínica dental ficticia ("BrightSmile Dental — sample company") quiere un asistente que responda preguntas de pacientes usando sus propios documentos (precios, horarios, preparación para tratamientos, políticas).

**Funcionalidades:**
- Ingesta de documentos (PDF, Markdown, TXT) de ejemplo que generamos nosotros.
- Chunking + embeddings + búsqueda vectorial (pgvector o Chroma; explícame el trade-off).
- Chat web donde cada respuesta **cita la fuente** (documento y fragmento).
- Si la respuesta no está en los documentos, lo dice ("I don't have that information, please contact the clinic") en vez de inventar.
- Opción de subir un documento propio en la demo (con límite de tamaño).

**Criterios de aceptación:**
- 10 preguntas de prueba con respuestas esperadas; al menos 9 correctas y con fuente.
- 3 preguntas fuera de tema; las 3 rechazadas correctamente.
- Un script `eval.py` que corre estas preguntas y muestra el resultado (esto impresiona a clientes técnicos).

## Al terminar cada demo
1. Revisemos juntos el código: explícame las 3 partes más importantes como si me estuvieran entrevistando.
2. Genera la ficha para el portafolio de Upwork en inglés: título, descripción de 2 o 3 líneas orientada a negocio, stack y links.
3. Sugiere 3 preguntas técnicas que un cliente podría hacerme sobre este proyecto, con la respuesta.

---

## Decisiones tomadas en esta demo
- **Chat LLM:** Claude Haiku 4.5 (`claude-haiku-4-5`). Proveedor intercambiable con `LLM_PROVIDER` (anthropic | openai; OpenAI implementado pero no probado).
- **Embeddings:** Voyage AI (`voyage-3.5-lite`, 1024 dims). Plan gratis sin tarjeta = 3 requests/min: embeddings siempre en lote.
- **Vector store:** pgvector en Neon (us-east-2, conexión directa sin pooler), índice HNSW coseno. Tabla `chunks` con `is_sample` para separar docs de ejemplo y subidos.
- **Chunking propio por títulos** (~1000 chars), sin LangChain.
- **Respuestas:** salida estructurada (`answer_found`, `answer`, `source_ids`); las citas se arman desde los resultados de búsqueda; mensaje de fallback fijo en código.
- **Prompt:** describe un "document assistant" (no "asistente de BrightSmile"), si no Claude rechaza preguntas sobre documentos subidos.
- **Frontend:** HTML + CSS + JS simple servido por FastAPI; texto del servidor siempre con `textContent`.
- **Protección:** rate limit por IP en memoria (10 preguntas/min, 5 subidas/hora), cuota diaria global, `TRUSTED_PROXY_HOPS` para la IP real detrás de Render.
- **Subidas:** prefijo `uploaded-`, expiran a las 24 h, `/reset` borra solo `is_sample = false`.
- **Eval:** `eval.py` = 13/13 (2026-09-29).
- **Dev local:** el proyecto está en OneDrive y `uvicorn --reload` se queda pegado; correr sin `--reload`.
- **Empaquetado:** `pyproject.toml` + pip; Docker con `pip install -e .` para que `data/` resuelva junto al paquete.
