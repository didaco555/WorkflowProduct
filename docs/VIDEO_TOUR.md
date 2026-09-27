# Vídeo tour inmobiliario con IA — el método

Workflow: **[`workflows/20_video_tour_inmobiliario.json`](../workflows/20_video_tour_inmobiliario.json)**.
Modelos y descargas: [`MODELOS.md`](MODELOS.md#6--vídeo-wan-22-14b--film).

## La idea en una frase

**Un plano de ~5 s por cada foto real, anclado a esa foto, y los planos unidos en el montaje.**
No se hace un único vídeo que recorra el piso entero de un tirón.

## Por qué así y no encadenando todo

Lo que parece más cómodo, generar un clip y usar su último frame como inicio del siguiente para
todo el piso, es justo lo que estropea un vídeo inmobiliario:

1. **Deriva.** Cada salto pasa por la IA otra vez. Al tercer o cuarto clip los colores se han
   desplazado y los detalles ya no son los de las fotos.
2. **Arquitectura inventada.** Si del salón le pides ir al baño, la IA no sabe qué hay entre medias
   y se inventa un pasillo, una puerta o una pared. Eso es enseñar un piso que no existe.
3. **Un mal plano te obliga a rehacer todo lo que viene detrás.**

Los videógrafos inmobiliarios de verdad tampoco graban de un tirón: hacen planos cortos con gimbal
(avance, paneo, travelling) y los cortan en el montaje. Con planos anclados a fotos reales, cada
uno sale fiel al piso y se repite sin tocar los demás.

## Cuándo sí se encadena

| Situación | Qué hacer en el workflow |
|---|---|
| Dos fotos **del mismo espacio** (dos ángulos del salón, puerta de la terraza → terraza) | INICIO = foto A, **FINAL** = foto B, movimiento `transicion_foto_a_foto`. El plano va de una a otra y **termina exactamente en la foto real**. |
| Quieres **alargar un plano** (salón grande, 10 s de avance) | INICIO = `output/tour/ultimo_frame_…png` del plano anterior, **mismo movimiento**. |
| Alargar **sin deriva** | Lo anterior + FINAL = la siguiente foto real del mismo espacio. Sigue el movimiento y aterriza en una foto real. |

El último frame es una imagen suelta: no sabe hacia dónde iba la cámara. Por eso hay que repetir el
mismo movimiento en el prompt; si no, puede cambiar de dirección.

## Elección del modelo (septiembre 2026)

| Modelo | Licencia | Veredicto |
|---|---|---|
| **Wan 2.2 14B I2V** | Apache 2.0 | **El elegido.** El más fiel a la foto de partida, sigue bien los movimientos de cámara escritos, nodo nativo de primer + último frame, LoRA de 4 pasos para ir rápido y el ecosistema más probado. |
| LTX-2.5 (agosto 2026) | Comunitaria: gratis por debajo de 10 M$ de facturación | Alternativa si la velocidad manda: bastante más rápido y también tiene primer + último frame nativo. Es reciente y hay menos pruebas de fidelidad en interiores. |
| HunyuanVideo 1.5 | Comunitaria de Tencent: excluye la UE, Reino Unido y Corea | **No se puede usar legalmente en España.** |
| MiniMax H3 (agosto 2026) | Excluye la UE, Reino Unido, Corea y EE. UU. | **No se puede usar legalmente en España.** |
| Wan 2.5 / 2.6 | Sólo API, sin pesos | No se puede correr en local. |

De lo que ya tenías se aprovecha **SeedVR2**, que es un restaurador de **vídeo**: sube el plano de
720p a 1080p con coherencia entre frames. Se añade **FILM** (interpolación de frames, nodo nativo)
para pasar de los 16 fps de Wan a 32 fps: en un travelling lento, 16 fps se ve a saltos.

## Plan de planos para un piso típico (40–60 s)

| # | Foto | Movimiento | Nota |
|---|---|---|---|
| 1 | Fachada o portal | `exterior_avance` | Si no hay buena foto exterior, empieza por el salón. |
| 2 | Salón, vista general | `avance_lento` | El plano estrella: dale calidad (TURBO = false) si hace falta. |
| 3 | Salón, otro ángulo | `travelling_lateral_*` | O `transicion_foto_a_foto` desde el plano 2 si comparten espacio. |
| 4 | Cocina | `paneo_a_*` | Los paneos lucen en cocinas alargadas. |
| 5 | Dormitorio principal | `avance_lento` u `orbita_suave` | |
| 6 | Baño | `fijo_con_vida` o `avance_lento` | Espacio pequeño: movimientos cortos. |
| 7 | Terraza o vistas | `retroceso_revelado` | Sólo si la foto ya enseña las vistas. **Nunca** pidas vistas que no están. |

## Ajustes

- **Fotos**: horizontales, con luz, sin gran angular extremo. La foto se recorta al centro para
  llenar el formato; una foto 3:2 pierde un poco de techo y suelo en 16:9, nada grave.
- **Formato**: genera siempre en **horizontal 1280×720**. El reel vertical sácalo recortando en el
  montaje; generar en vertical desde fotos horizontales tira a la basura los lados de la habitación.
- **TURBO primero**: 4 pasos para comprobar que el movimiento funciona. Si sale bien, ya está; si
  se deforma algo, prueba otra semilla antes de pasar a calidad (20 pasos).
- **ESTANCIA**: una línea en inglés con lo que se ve (*bright kitchen with white cabinets and a
  wooden island*). Ayuda a que no invente objetos.
- **Revisa cada plano** antes de darlo por bueno: puertas que se mueven, líneas que se doblan,
  objetos que aparecen. Descártalo y cambia la semilla. Es lo que prometes en la web.
- **VRAM**: los dos modelos de 14B en fp8 ocupan unos 14 GB cada uno, pero se cargan de uno en uno.
  Con 24 GB, 1280×720 va cómodo. Con 16 GB, empieza en 832×480 y activa *1080p con SeedVR2*.
  Ten 64 GB de RAM si puedes: ComfyUI aparca ahí el modelo que no está usando.

## Producir todos los planos seguidos

ComfyUI guarda en la cola una copia de los ajustes de cada ejecución. Carga la foto 1, elige el
movimiento y pulsa **Run**; sin esperar, carga la foto 2, cambia el movimiento y **Run** otra vez.
Así dejas los siete planos en cola y te vas a hacer otra cosa.

## Montaje

En CapCut, DaVinci o Premiere:

1. Pon los planos en orden, de fuera hacia dentro, como si entrases al piso.
2. Corte seco o fundido corto (0,3–0,5 s) entre estancias.
3. Música libre de derechos y textos: nombre del alojamiento, plazas, una línea por estancia y el
   contacto al final.
4. Exporta en horizontal 1920×1080 y saca el reel en vertical 1080×1920 recortando el centro.
