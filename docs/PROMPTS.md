# Prompts para fotografía de producto

Los prompts van en **inglés**: los tres modelos entienden español, pero responden bastante mejor
en inglés, sobre todo con vocabulario de iluminación. Las explicaciones de aquí están en español.

## Las cinco reglas que cambian el resultado

1. **Di siempre qué se conserva.** Es lo que evita que te reinvente la etiqueta:
   *keep the geometry, proportions, colours, materials, logo and label text EXACTLY as in the input image*.
2. **Describe la luz como un fotógrafo, no como un usuario.** *Softbox key light from the upper
   left, soft fill from the right, rim light* funciona; *buena luz* no.
3. **Pide la sombra explícitamente.** Sin mencionarla, el producto sale flotando:
   *one soft realistic contact shadow directly underneath the product*.
4. **Una instrucción por frase.** Los modelos de edición siguen listas mejor que párrafos.
5. **No pidas lo que ya está bien.** Si el encuadre te vale, no menciones el encuadre: cada cosa
   que nombras es una cosa que el modelo se siente autorizado a cambiar.

---

## 1 · Packshot de catálogo

### Base — fondo blanco puro

```
Turn this into a professional e-commerce packshot of the product.

Background: seamless pure white studio cyclorama (#FFFFFF), completely clean, no props, no text, no watermark.
Lighting: large softbox key light from the upper left, soft fill from the right, subtle rim light separating the edges from the background, no blown highlights, no colour cast.
Shadow: one soft realistic contact shadow directly underneath the product, grounding it on the surface.
Product: keep the geometry, proportions, colours, materials, logo and label text EXACTLY as in the input image, perfectly readable.
Camera: straight-on product shot, centred, even margins, sharp focus, high micro-detail, neutral white balance.
```

### Variantes de fondo

| Quiero | Cambia la línea `Background:` por |
|---|---|
| Degradado gris | `light grey seamless gradient background, brighter behind the product, darker towards the corners` |
| Fondo de color | `seamless solid pastel sand background (#E8DCC8), completely uniform` |
| Sombra sobre superficie | `product standing on a matte white surface with a soft seamless white backdrop, visible surface horizon line` |
| Reflejo tipo escaparate | `product standing on a glossy white acrylic surface with a soft mirror reflection below it` |

### Variantes de luz

| Producto | Línea `Lighting:` |
|---|---|
| Cosmética, envases mate | `large softbox key light from the upper left, broad soft fill, gentle gradient falloff, no hotspots` |
| Cristal, botellas, vino | `two large white strip softboxes at both sides creating clean vertical highlights on the glass, dark background edge for contrast, backlight through the liquid` |
| Metal, relojes, joyería | `large overhead diffuser dome, soft even reflections, black card gradients on the sides to shape the metal` |
| Textil, zapatillas | `soft frontal key light plus a raking side light to reveal fabric texture and stitching` |
| Comida y envases | `warm soft window light from the back left, gentle bounce fill from the front, slight specular highlights` |

### Negativo (packshot)

```
blurry, out of focus, low resolution, jpeg artifacts, noise, distorted product, deformed logo,
unreadable or invented label text, extra objects, props, hands, people, clutter, harsh shadows, double shadow,
colour cast, grey or dirty background, reflections of the room, watermark, text overlay, oversaturated, plastic look
```

---

## 2 · Lifestyle — el producto dentro de una escena

Plantilla: **escena → integración → producto → cámara**. Mantén siempre los bloques
“Product” y “Camera”; cambia sólo “Scene”.

```
Place the product from image 1 into a photorealistic lifestyle scene.

Scene: <describe aquí el ambiente>
Integration: match the scene's light direction, colour temperature and contrast onto the product, add a realistic contact shadow and a subtle reflection on the surface, correct perspective, the product sits naturally on the surface.
Product: keep its shape, proportions, materials, logo and label text pixel-accurate and fully readable, do not redesign it.
Camera: 50mm lens at f/2.8, shallow depth of field with the product in sharp focus, editorial commercial photography.
```

### Banco de escenas

**Baño de mármol (cosmética)**
```
a bright modern bathroom, white marble countertop with subtle grey veining, soft morning light coming through a window on the left, a folded linen towel and a small eucalyptus branch blurred in the background
```

**Terraza al atardecer (vino, bebidas)**
```
a wooden terrace table at golden hour, warm low sun from behind creating long soft shadows, blurred mediterranean garden and sea in the background, two empty glasses out of focus
```

**Cocina nórdica (alimentación)**
```
a light oak kitchen counter, matte white tiles behind, diffused daylight from a large window on the right, fresh ingredients scattered and blurred in the background
```

**Hormigón y cemento (tecnología, zapatillas)**
```
a raw polished concrete surface, cool overcast daylight from above, deep neutral grey background, minimal styling, single hard-edged soft shadow
```

**Escritorio de trabajo (papelería, tecnología)**
```
a walnut desk with a linen notebook and a matte black pen slightly out of focus, warm lamp light from the upper right mixed with cool window light from the left
```

**Mesita de noche (velas, difusores)**
```
a dark wooden nightstand at night, warm candlelight from the left as the only light source, deep shadows, cosy and intimate atmosphere
```

**Exterior natural (deporte, outdoor)**
```
a flat mossy rock in a forest clearing, dappled sunlight filtering through leaves, soft green bokeh in the background
```

### Si usas foto de referencia de escena (motor A)

Con el nodo *Referencia de escena* conectado, el modelo ve dos imágenes. Nómbralas:

```
Place the product from image 1 into the scene of image 2.
Match the lighting direction, colour temperature, contrast and grain of image 2 exactly.
Put the product on the main surface of image 2, at a realistic scale, with a contact shadow consistent with the light in image 2.
Keep the product's shape, materials, logo and label text pixel-accurate.
Do not change the background composition of image 2.
```

### Negativo (lifestyle)

```
blurry product, distorted product, deformed or invented logo, unreadable label, wrong scale,
floating product, missing shadow, duplicated product, extra objects on top of the product, people, hands,
low resolution, jpeg artifacts, flat lighting, HDR look, watermark, text overlay, cartoon, illustration
```

---

## 3 · Retoque por zona marcada

Con el workflow `03`, pinta la zona en el MaskEditor y usa frases cortas y concretas. Empieza
siempre por *“Only change what is inside the selected area”*.

| Problema | Prompt |
|---|---|
| Polvo, pelusas, huellas | `Remove the dust specks and fingerprints from the selected area, keep the same glossy plastic texture and highlights.` |
| Fondo sucio en una esquina | `Replace the selected background area with clean seamless pure white studio backdrop, no gradient.` |
| Etiqueta borrosa | `Make the selected label text sharp and perfectly readable, same font, same colours, same layout.` |
| Reflejo del fotógrafo | `Remove the reflection of the photographer and the room in the selected area of the glass, keep a clean natural specular highlight.` |
| Sombra fea | `Replace the harsh dark shadow in the selected area with a soft realistic contact shadow.` |
| Añadir un elemento | `Add a small folded linen towel in the selected area, out of focus, matching the scene lighting.` |
| Quitar un objeto | `Remove the object in the selected area and rebuild the surface behind it with the same material and lighting.` |

Ajustes útiles en ese workflow:

- **Se nota el parche** → sube `Ampliar selección` a 24–32 y `Suavizar borde` a 32.
- **Cambia demasiado** → baja `denoise` del `KSampler` a 0.6–0.7.
- **No cambia nada** → tu máscara es muy pequeña, o el prompt describe lo que ya hay.

---

## 4 · Las 3 vistas del producto

El bloque de vistas de `10_estudio_producto.json` parte de la foto ya buena y le cambia sólo el
ángulo. La plantilla es siempre la misma y lo único que cambias es la última línea:

```
Keep the exact same product: same shape, proportions, materials, colours, logo and label text.
Keep the same background, the same lighting setup and the same framing and scale.
Only the camera angle changes.

<aquí el ángulo>
```

| Ángulo | Última línea |
|---|---|
| Tres cuartos izquierda *(por defecto)* | `Rotate the product to a three-quarter view seen from the left, about 35 degrees.` |
| Tres cuartos derecha *(por defecto)* | `Rotate the product to a three-quarter view seen from the right, about 35 degrees.` |
| Cenital / flat lay *(por defecto)* | `Move the camera above the product for a top-down flat-lay view, looking straight down.` |
| Perfil | `Rotate the product to a perfect side profile view, 90 degrees.` |
| Trasera | `Show the back of the product, rotated 180 degrees.` |
| Contrapicado | `Lower the camera below the product for a heroic low angle shot looking slightly up.` |
| Picado suave | `Raise the camera to about 45 degrees above the product, looking down at it.` |
| Tumbado | `Lay the product down flat on the surface, seen from the front.` |

**La limitación que hay que tener presente**: el modelo no ha visto las caras que no aparecen en
la foto original, así que las inventa. Los giros suaves (±35°) y el cenital son los que menos se
inventan. `Show the back` sobre un producto con texto en la etiqueta trasera va a producir texto
falso casi seguro — úsalo sólo con productos lisos o cuando vayas a revisar a mano.

Si una vista sale casi bien pero con un defecto puntual, no la repitas entera: pásala por la
categoría `retoque_zona_marcada` y arregla sólo esa zona.

---

## 5 · Ajustes numéricos de referencia

| Parámetro | Calidad | Turbo (LoRA Lightning) |
|---|---|---|
| Pasos | 20 (hasta 40 para la toma final) | 4 |
| CFG | 4.0 | 1.0 |
| Sampler / scheduler | `euler` / `simple` | `euler` / `simple` |
| `shift` (ModelSamplingAuraFlow) | 3.1 | 3.1 |
| Denoise | 1.0 (edición completa) | 1.0 |

FLUX.2 [klein] destilado: 4 pasos, CFG 1, sigmas del nodo `Flux2Scheduler`. Subir el CFG en un
modelo destilado no mejora nada, lo quema.
