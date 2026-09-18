# WorkflowProduct — fotografía de producto con ComfyUI

Workflows `.json` listos para arrastrar a ComfyUI, pensados para trabajar con **la foto que manda
el cliente** (a menudo mala) y sacar de ahí dos entregables:

1. **Packshot de catálogo** — fondo limpio de estudio, luz y sombra natural.
2. **Lifestyle** — el producto dentro de una escena (la crema en un baño de mármol, el vino en una terraza).

Todo funciona con modelos **gratuitos y de pesos abiertos, en local**. GPT Image 2.5 aparece sólo
como motor alternativo opcional dentro del workflow único, apagado por defecto.

| Archivo | Para qué |
|---|---|
| **[`workflows/10_estudio_producto.json`](workflows/10_estudio_producto.json)** | **Todo en uno**: subes la foto, eliges el tipo en un desplegable y ejecutas |
| [`workflows/00_rescate_foto_cliente.json`](workflows/00_rescate_foto_cliente.json) | Reconstruye una foto mala (móvil, ruido, JPEG, borrosa) con SeedVR2 |
| [`workflows/01_packshot_catalogo.json`](workflows/01_packshot_catalogo.json) | Packshot de catálogo, con **4 niveles** encadenados |
| [`workflows/02_lifestyle_escena.json`](workflows/02_lifestyle_escena.json) | Producto integrado en una escena, con **dos motores** a elegir |
| [`workflows/03_retoque_zona.json`](workflows/03_retoque_zona.json) | “Rodear lo que no me gusta”: pintas una zona y sólo eso se regenera |

Empieza por **`10_estudio_producto.json`** si quieres un único grafo para todo. Los otros cuatro son
los mismos pasos por separado, más sencillos de leer y de modificar.

Cada workflow lleva dentro sus propias notas (nodos `MarkdownNote`), así que se explica solo una
vez abierto.

---

## Modelos que usa (todos gratis)

| Papel | Modelo | Por qué este |
|---|---|---|
| Edición de imagen | **Qwen-Image-Edit 2511** | El mejor libre conservando logotipos y **texto de etiqueta**; acepta hasta 3 imágenes de entrada |
| Edición alternativa | **FLUX.2 [klein] 9B destilado** | Apache-2.0, 4 pasos, luz y materiales muy realistas |
| Quitar fondo | **BiRefNet** | Ya es un nodo del núcleo de ComfyUI (`Remove Background`), sin instalar nada |
| Restaurar / reescalar | **SeedVR2 3B** | Reconstruye detalle real en fotos malas, no sólo interpola |
| Reescalado rápido | **RealESRGAN x4plus** | Barato y fiel para el paso final |
| Aceleración | **Qwen-Image-Edit-2511-Lightning 4 steps** (LoRA) | Pasa de 20 pasos a 4 para iterar rápido |

La lista de descargas con enlaces y carpetas está en **[`docs/MODELOS.md`](docs/MODELOS.md)**.

> **Sin nodos de terceros.** Todos los workflows usan únicamente nodos del núcleo de ComfyUI.
> No hace falta ComfyUI-Manager, ni BiRefNet de terceros, ni Impact Pack. Sólo mantén ComfyUI
> actualizado (los nodos `RemoveBackground`, `SeedVR2*` y `Flux2Scheduler` son recientes).

---

## Puesta en marcha

1. Actualiza ComfyUI a la última versión.
2. Descarga los modelos de [`docs/MODELOS.md`](docs/MODELOS.md) a sus carpetas.
3. Abre ComfyUI y **arrastra el `.json`** sobre el lienzo.
4. Sube la foto del cliente en el nodo *Cargar imagen* y pulsa **Ejecutar**.

Si un nodo aparece en rojo, es que falta el archivo del modelo en esa carpeta o que tu ComfyUI es
anterior a ese nodo: actualiza y vuelve a cargar el workflow.

---

## El workflow único: `10_estudio_producto.json`

Un solo grafo, y **un solo mando**: el desplegable `TIPO DE FOTO`.

```
▼ TIPO DE FOTO
   packshot_blanco              packshot_degradado_gris
   packshot_superficie_reflejo  packshot_fondo_color
   lifestyle_bano_marmol        lifestyle_terraza_atardecer
   lifestyle_cocina_nordica     lifestyle_hormigon_estudio
   lifestyle_escritorio_madera  lifestyle_mesita_noche
   lifestyle_exterior_natural   lifestyle_usar_referencia
   retoque_zona_marcada
```

Lo que eliges hace dos cosas a la vez:

1. Un nodo `Extract Text from JSON` saca ese prompt del **catálogo** y lo enchufa al motor.
2. El propio nombre reconfigura el grafo: si contiene `packshot` se activa el recorte con fondo
   blanco puro; si contiene `retoque` se pasa a modo máscara y sólo se regenera lo que hayas
   pintado en el MaskEditor.

**Añadir tus propios tipos** son dos pasos: escribes `"mi_tipo": "tu prompt"` en el nodo CATÁLOGO
y añades `mi_tipo` a la lista del desplegable (doble clic sobre él).

Además lleva un segundo desplegable, `MOTOR`, con tres opciones:

| Opción | Qué es | Coste |
|---|---|---|
| `qwen_local` | Qwen-Image-Edit 2511 en tu GPU | gratis |
| `flux2_local` | FLUX.2 [klein] 9B en tu GPU | gratis |
| `gpt_image_api` | GPT Image 2.5 de OpenAI, por la nube | se paga por imagen |

Sólo se ejecuta el motor elegido: los interruptores son perezosos, así que los otros dos ni cargan
su modelo ni facturan nada. El nodo de GPT Image enseña el precio estimado antes de ejecutar.

Los dos cargadores secundarios (*referencia de escena* e *imagen a retocar*) vienen **en bypass**
para que no tengas que subirles nada. Ctrl+B para activarlos cuando los necesites.

---

## El flujo completo, de principio a fin

Los cuatro workflows sueltos son las mismas piezas que van dentro de `10_estudio_producto.json`,
por si prefieres tocarlas por separado:

```
foto del cliente
      │
      ├─ ¿está mal?  ──►  00_rescate  (o Nivel 0 dentro de 01 / 02)
      │
      ├─────────────►  01_packshot     ──►  fondo blanco + PNG con alpha + 2048 px
      │
      └─────────────►  02_lifestyle    ──►  producto en escena + 2048 px
                              │
                              └─ ¿algo no te gusta?  ──►  03_retoque_zona
```

### 1 · Packshot de catálogo — los cuatro niveles

Están **dentro del mismo workflow**, encadenados, cada uno con su interruptor booleano:

| Nivel | Qué hace | Cuándo encenderlo |
|---|---|---|
| **0 · Rescate** | SeedVR2 reconstruye la foto | la foto del cliente viene mal |
| **1 · Packshot** | Qwen-Image-Edit rehace **fondo + luz + sombra** conservando el producto | siempre |
| **2 · Recorte** | BiRefNet recorta, fondo blanco **255,255,255** exacto y sombra de contacto | Amazon/marketplace, o si quieres el PNG transparente |
| **3 · Alta resolución** | Upscaler GAN 4x, reencuadre al lado largo y enfoque sutil | entrega final |

Además hay un interruptor **⚡ TURBO** que cambia entre LoRA Lightning (4 pasos, CFG 1) y calidad
(20 pasos, CFG 4). Encuadra el prompt en turbo y lanza la final en calidad.

Los interruptores son **perezosos**: la rama apagada ni se ejecuta ni carga su modelo en VRAM.

### 2 · Lifestyle — dos motores

| | Qwen-Image-Edit 2511 | FLUX.2 [klein] 9B |
|---|---|---|
| Fidelidad de etiqueta / logo | **la mejor** | buena |
| Realismo de escena y luz | muy bueno | **el mejor** |
| Referencia de escena por imagen | sí (`image2`) | no, sólo texto |
| Pasos | 20, o 4 con LoRA turbo | 4 (destilado) |

Puedes darle una **foto de referencia de la escena** al motor A: la crema se integra copiando la
luz y el estilo de esa referencia. Si no la quieres, selecciona ese nodo y pulsa **Ctrl+B**.

También incluye un bloque opcional **“proteger la etiqueta”**: si el modelo te deforma el texto del
envase, vuelve a pegar los píxeles originales del producto dentro de su silueta.

### 3 · Retoque por zona — el equivalente a “rodear con un círculo”

Es lo más parecido a marcar algo con un círculo en un chat y decir *“esto no me gusta”*:

1. Carga la imagen y haz **clic derecho → “Open in MaskEditor”**.
2. Pinta encima de lo que falla (un brochazo o un círculo relleno) y guarda.
3. Escribe qué quieres que pase ahí y ejecuta.

Sólo se regenera lo pintado: `SetLatentNoiseMask` limita la difusión a la máscara,
`DifferentialDiffusion` funde el borde y `ImageCompositeMasked` devuelve el resto de píxeles
originales intactos.

---

## Fotos de cliente de mala calidad

Es el caso normal, así que está tratado en los tres workflows principales:

- **Nivel 0 / workflow 00**: SeedVR2 3B reconstruye detalle antes de tocar nada más. No es un
  upscaler clásico: regenera textura y bordes, así que aguanta fotos de móvil, con ruido o con
  compresión JPEG visible.
- Sube el **pre-escalado** a 3x o 4x si la foto es diminuta; bájalo si te quedas sin VRAM.
- Si la foto está movida más allá de lo recuperable, el rescate no hace magia: pide otra toma.
- En lifestyle es especialmente importante rescatar antes: un producto con ruido dentro de una
  escena limpia canta muchísimo.

---

## Prompts

La plantilla de prompt es la mitad del resultado. En **[`docs/PROMPTS.md`](docs/PROMPTS.md)** hay
prompts listos para packshot, para varias escenas lifestyle y para retoques, con las reglas que
funcionan (decir siempre qué se conserva, describir la luz como un fotógrafo, pedir la sombra de
forma explícita).

---

## Regenerar los workflows

Los `.json` se generan desde código, que es más fácil de revisar y de mantener que un grafo a mano:

```bash
python3 tools/build_workflows.py      # reescribe workflows/*.json
python3 tools/validate_workflows.py   # comprueba enlaces, sockets y tipos
```

`tools/validate_workflows.py --comfyui /ruta/a/ComfyUI` comprueba además que todos los tipos de
nodo usados existen en tu instalación.
