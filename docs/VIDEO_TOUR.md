# Vídeo tour inmobiliario con IA — el método

Workflows:

| Archivo | Motor | Para qué |
|---|---|---|
| **[`21_video_tour_ltx25.json`](../workflows/21_video_tour_ltx25.json)** | **LTX-2.5** | **foto → plano**. El recomendado. |
| **[`22_video_transicion_ltx25.json`](../workflows/22_video_transicion_ltx25.json)** | **LTX-2.5** | **foto → foto** del mismo espacio |
| [`20_video_tour_inmobiliario.json`](../workflows/20_video_tour_inmobiliario.json) | Wan 2.2 14B | las dos cosas en un grafo (FINAL opcional), con SeedVR2 y FILM |
| [`23_video_tour_minimax_h3.json`](../workflows/23_video_tour_minimax_h3.json) | MiniMax H3 | foto → plano, FINAL opcional. **Licencia: excluye la UE** |
| [`24_video_tour_fasth3.json`](../workflows/24_video_tour_fasth3.json) | FastVideo FastH3 (H3 a 8 pasos) | lo mismo, mucho más rápido. **Licencia: la de H3** |

Modelos y descargas: [`MODELOS.md`](MODELOS.md) secciones 6 (Wan), 7 (LTX-2.5) y 8 (H3).

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

| Situación | Qué hacer |
|---|---|
| Dos fotos **del mismo espacio** (dos ángulos del salón, puerta de la terraza → terraza) | Workflow **22** (o el 20 con FINAL activado): INICIO = foto A, FINAL = foto B, movimiento `transicion_foto_a_foto`. El plano va de una a otra y **termina exactamente en la foto real**. |
| Quieres **alargar un plano** (salón grande, 10 s de avance) | Workflow **21** (o el 20): INICIO = `output/tour/ultimo_frame_…png` del plano anterior, **mismo movimiento**. |
| Alargar **sin deriva** | Workflow **22** (o el 20 con FINAL): INICIO = último frame, FINAL = la siguiente foto real del mismo espacio. Sigue el movimiento y aterriza en una foto real. |

El último frame es una imagen suelta: no sabe hacia dónde iba la cámara. Por eso hay que repetir el
mismo movimiento en el prompt; si no, puede cambiar de dirección.

## Elección del modelo (septiembre 2026)

Criterio: **gratis, que corra en ComfyUI en tu PC y que puedas usarlo legalmente en España para
un servicio de pago**. La calidad sale del ranking de votos a ciegas de Artificial Analysis
(imagen a vídeo, modelos de pesos abiertos).

| Modelo | Ranking | ¿Lo puedes usar? | Veredicto |
|---|---|---|---|
| MiniMax H3 | **1.º** | **No**: su licencia excluye la UE, Reino Unido, Corea y EE. UU. | Es el mejor, pero en España no tienes licencia para usarlo. |
| Cosmos 3 Super (NVIDIA) | 2.º | Licencia sí (OpenMDW); en tu PC, no | 64B de parámetros: pide una GPU de 48 GB o más y en ComfyUI sólo hay nodos de terceros para Linux. |
| **LTX-2.5** (agosto 2026) | **el mejor de los que puedes usar** | **Sí**: gratis por debajo de 10 M$ de facturación | **El elegido.** Nativo en ComfyUI, primer + último frame, rápido. La generación anterior, LTX-2, ya superaba a Wan 2.2 en ese ranking. |
| Wan 2.2 14B | por debajo de LTX-2 | Sí: Apache 2.0 | **La alternativa.** Las comparativas le siguen dando ventaja en seguir movimientos de cámara concretos a partir de una foto. |
| HunyuanVideo 1.5 | — | **No**: su licencia excluye la UE | — |
| Wan 2.5 / 2.6 | — | Sólo API, sin pesos | No se puede correr en local. |

**Lo práctico:** haz el mismo plano con el 21 (LTX-2.5) y con el 20 (Wan 2.2) usando la misma foto
y el mismo movimiento, y quédate con el que mejor respete tu piso. El ranking mide gustos
generales; lo que importa aquí es que no se deformen puertas ni muebles.

De lo que ya tenías, el workflow de Wan aprovecha **SeedVR2**, que es un restaurador de **vídeo**:
sube el plano de 720p a 1080p con coherencia entre frames. LTX-2.5 ya sale a más resolución y a 24
fps, así que en el 21 y el 22 no hace falta.

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

- **LTX-2.5**: deja el *prompt enhance* apagado. Reescribe el prompt en plan cinematográfico y tiende
  a añadir cosas que no están en el piso. El audio que genera (ambiente) lo cambias por música en el montaje.

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
