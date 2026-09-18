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

Mete tus imágenes en `img/` **con el mismo nombre** que las de relleno y ya está, no hay que
tocar el HTML:

| Archivo | Dónde sale |
|---|---|
| `antes-1.jpg` / `despues-1.jpg` | primer comparador (el grande) |
| `antes-2.jpg` / `despues-2.jpg` | comparador de abajo a la izquierda |
| `antes-3.jpg` / `despues-3.jpg` | comparador de abajo a la derecha |
| `catalogo.jpg`, `ambiente.jpg`, `video.jpg` | sección “Qué hago” |
| `og.jpg` | la miniatura que se ve al pasar el enlace por WhatsApp |

Tres reglas para que no se descuadre nada:

1. **El "antes" y el "después" de cada pareja tienen que medir exactamente lo mismo.** Si no, el
   deslizador enseña la foto movida.
2. Usa **1200 × 900 px** (o cualquier medida con esa proporción 4:3) para los comparadores y las
   tres de “Qué hago”, y **1200 × 630 px** para `og.jpg`.
3. Guarda en JPG de calidad media (unos 150–250 KB por imagen). Si subes fotos de 5 MB la web
   tardará en cargar en el móvil, que es por donde entra la mitad de la gente.

Si cambias la proporción de las fotos, cambia también los atributos `width` y `height` de cada
`<img>`: sirven para que el navegador reserve el hueco y la página no pegue saltos al cargar.

Y cambia el texto `alt` de cada imagen por lo que se ve realmente en ella (“bote de crema sobre
mármol…”). Es lo que lee Google y lo que oye quien navega con lector de pantalla.

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
