# La web (`index.html`)

Una sola página, sin frameworks, sin build y sin librerías externas. Todo el CSS y el JS van
dentro de `index.html`; las fotos, en la carpeta `img/`. Se abre haciendo doble clic en el
archivo y funciona igual en GitHub Pages.

```
index.html      ← la web entera (textos, estilos y JS)
img/            ← las imágenes, todas de relleno hasta que pongas las tuyas
README-WEB.md   ← esto
```

---

## 1. Lo primero: pon tus datos

Abre `index.html` con cualquier editor y usa **buscar y reemplazar** (Ctrl+H) con estos siete
textos. Cada uno aparece varias veces, así que reemplaza **todas** las apariciones:

| Busca | Reemplaza por |
|---|---|
| `[TU NOMBRE O MARCA]` | tu nombre o el de tu marca |
| `34XXXXXXXXX` | tu WhatsApp con prefijo y sin espacios ni `+` (ej. `34612345678`) |
| `+34 XXX XXX XXX` | el mismo número, tal como quieres que se lea en pantalla |
| `TU_EMAIL@EJEMPLO.COM` | tu email |
| `TU_CUENTA` | tu usuario de Instagram, sin la arroba |
| `TU_ID_FORMSPREE` | el id que te da Formspree (ver punto 3) |
| `https://didaco555.github.io/WorkflowProduct/` | ya está puesta; cámbiala sólo si publicas en otro repo o con dominio propio |

Si no tienes Instagram, borra las dos líneas marcadas con
`<!-- CAMBIAR o BORRAR si no tienes Instagram -->`.

El resto de textos (titulares, packs, precios, preguntas) están en claro dentro del HTML y
llevan comentarios `<!-- CAMBIAR ... -->` encima de cada bloque. Cámbialos sin miedo: es texto
normal, no hay nada que compilar.

---

## 2. Cómo sustituyo las fotos

Mete tus imágenes en `img/` **con el mismo nombre** que las que ya hay y listo, no hay que tocar
el HTML:

| Archivo | Dónde sale | Tamaño actual |
|---|---|---|
| `antes-1.jpg` / `despues-1.jpg` | primer comparador (el grande) | 1000 × 1500 |
| `antes-2.jpg` / `despues-2.jpg` | comparador de abajo a la izquierda | 1100 × 1320 |
| `antes-3.jpg` / `despues-3.jpg` | comparador de abajo a la derecha | 1100 × 1320 |
| `caso-original.jpg` | la foto de partida de la sección **Exposición** | 900 × 1200 |
| `despues-1/2/3.jpg` | las tres piezas de la **Exposición** (se reutilizan) | — |
| `catalogo.jpg`, `ambiente.jpg`, `video.jpg` | tarjetas de “Qué hago” | 900 × 1200 |
| `og.jpg` | la miniatura al compartir el enlace por WhatsApp | 1200 × 630 |

Tres reglas para que no se descuadre nada:

1. **El “antes” y el “después” de cada pareja tienen que medir exactamente lo mismo.** Si no, el
   deslizador enseña la foto movida.
2. Respeta los tamaños de la tabla, o cambia también los atributos `width` y `height` del `<img>`
   correspondiente: sirven para que el navegador reserve el hueco y la página no pegue saltos.
3. Guarda en JPG de calidad media (unos 150–250 KB por imagen). Si subes fotos de 5 MB la web
   tardará en cargar en el móvil, que es por donde entra la mitad de la gente.

Y cambia el texto `alt` de cada imagen por lo que se ve realmente en ella (“bote de crema sobre
mármol…”). Es lo que lee Google y lo que oye quien navega con lector de pantalla.

### Añadir más trabajos a la Exposición

Dentro de `<section id="exposicion">` busca `<div class="galeria">`. Cada pieza es un bloque así:

```html
<figure class="obra">
  <button type="button" class="lupa-btn" data-lupa="img/mi-foto.jpg" data-pie="Pie que sale al ampliar.">
    <img src="img/mi-foto.jpg" width="1100" height="1320" loading="lazy" alt="Describe la imagen">
  </button>
  <figcaption>Título corto · para qué sirve.</figcaption>
</figure>
```

Copia el bloque, cambia `data-lupa`, `src`, `alt` y los dos pies, y ya aparece en la galería con la
lupa funcionando. Con más de tres piezas la rejilla sigue en tres columnas y va bajando de fila.

**El aviso de abajo.** Mientras las imágenes sean pruebas tuyas y no encargos, deja la línea
`<p class="aviso">`: dice que compraste el producto y que no es un trabajo para la marca. Si algún
día son encargos reales con permiso del cliente, bórrala.

---

## 3. El formulario

El formulario de contacto está preparado para [Formspree](https://formspree.io), que tiene plan
gratis:

1. Crea una cuenta y un formulario nuevo con tu email.
2. Formspree te da una dirección tipo `https://formspree.io/f/abcdwxyz`.
3. Pega ese id en `index.html`, en `action="https://formspree.io/f/TU_ID_FORMSPREE"`.
4. Envía una prueba desde la web: el primer envío te pide confirmar el email.

Mientras no lo cambies, el formulario no envía nada. El botón de WhatsApp y el email sí
funcionan desde el minuto uno.

---

## 4. Cómo lo publico en GitHub Pages

1. Sube `index.html` y la carpeta `img/` al repositorio (ya están en la rama
   `claude/intelligent-allen-t6pn6t`).
2. En GitHub, ve a **Settings → Pages**.
3. En **Source** elige **Deploy from a branch**.
4. En **Branch** elige la rama donde está el `index.html` (`claude/intelligent-allen-t6pn6t`) y la
   carpeta **`/ (root)`**. Guarda.
5. Espera un par de minutos y la web queda en
   **`https://didaco555.github.io/WorkflowProduct/`**.
6. Esa dirección ya está escrita dentro de `index.html` (`canonical`, `og:url` y `og:image`). Si
   publicas en otro repositorio o con dominio propio, cámbiala ahí: sin eso, la miniatura no sale
   al compartir el enlace por WhatsApp.

Cada vez que hagas un cambio y lo subas al repositorio, la web se actualiza sola en un par de
minutos. Si ves la versión antigua, recarga con Ctrl+F5.

**¿Dominio propio?** En la misma pantalla de Pages, apartado *Custom domain*: escribe tu dominio
y en tu proveedor apunta un registro `CNAME` a `didaco555.github.io`.

---

## Comprobaciones antes de enseñársela a nadie

- Ábrela en el móvil y arrastra los tres comparadores con el dedo.
- Pulsa el botón verde de WhatsApp: tiene que abrir el chat contigo con el mensaje escrito.
- Manda el enlace por WhatsApp a un amigo y mira si sale la miniatura de `og.jpg`.
- Envía el formulario una vez y comprueba que te llega el email.
