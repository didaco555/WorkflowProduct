#!/usr/bin/env python3
"""Genera los workflows .json de fotografía de producto para ComfyUI.

    python3 tools/build_workflows.py

Escribe en `workflows/`. Editar aquí y regenerar es más seguro que tocar el JSON a mano.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from comfy_graph import MODE_BYPASS, MODE_NEVER, Graph  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workflows")

# ======================================================================================
# Modelos (nombres de archivo tal y como quedan dentro de ComfyUI/models/...)
# ======================================================================================
QWEN_UNET = "qwen_image_edit_2511_fp8mixed.safetensors"
QWEN_CLIP = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
QWEN_VAE = "qwen_image_vae.safetensors"
QWEN_TURBO_LORA = "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"

FLUX2_UNET = "flux-2-klein-9b-fp8.safetensors"
FLUX2_CLIP = "qwen_3_8b_fp8mixed.safetensors"
FLUX2_VAE = "flux2-vae.safetensors"

SEEDVR2_UNET = "seedvr2_3b_int8_convrot.safetensors"
SEEDVR2_VAE = "seedvr2_ema_vae_fp16.safetensors"

BIREFNET = "birefnet.safetensors"
GAN_UPSCALER = "RealESRGAN_x4plus.safetensors"

BLUE, GREEN, PURPLE, ORANGE, RED, GREY = "#3f789e", "#2d7d46", "#6b3f9e", "#9e6b3f", "#9e3f3f", "#444"

# ======================================================================================
# Prompts
# ======================================================================================
PACKSHOT_POS = """Turn this into a professional e-commerce packshot of the product.

Background: seamless pure white studio cyclorama (#FFFFFF), completely clean, no props, no text, no watermark.
Lighting: large softbox key light from the upper left, soft fill from the right, subtle rim light separating the edges from the background, no blown highlights, no colour cast.
Shadow: one soft realistic contact shadow directly underneath the product, grounding it on the surface.
Product: keep the geometry, proportions, colours, materials, logo and label text EXACTLY as in the input image, perfectly readable.
Camera: straight-on product shot, centred, even margins, sharp focus, high micro-detail, neutral white balance."""

PACKSHOT_NEG = """blurry, out of focus, low resolution, jpeg artifacts, noise, distorted product, deformed logo,
unreadable or invented label text, extra objects, props, hands, people, clutter, harsh shadows, double shadow,
colour cast, grey or dirty background, reflections of the room, watermark, text overlay, oversaturated, plastic look"""

LIFESTYLE_POS = """Place the product from image 1 into a photorealistic lifestyle scene.

Scene: a bright modern bathroom, white marble countertop with subtle grey veining, soft morning light coming
through a window on the left, a folded linen towel and a small eucalyptus branch blurred in the background.
Integration: match the scene's light direction, colour temperature and contrast onto the product, add a realistic
contact shadow and a subtle reflection on the marble, correct perspective, the product sits naturally on the surface.
Product: keep its shape, proportions, materials, logo and label text pixel-accurate and fully readable, do not redesign it.
Camera: 50mm lens at f/2.8, shallow depth of field with the product in sharp focus, editorial commercial photography."""

LIFESTYLE_NEG = """blurry product, distorted product, deformed or invented logo, unreadable label, wrong scale,
floating product, missing shadow, duplicated product, extra objects on top of the product, people, hands,
low resolution, jpeg artifacts, flat lighting, HDR look, watermark, text overlay, cartoon, illustration"""

RETOUCH_POS = """Only change what is inside the selected area. Fix it so it looks like a clean, professional product
photograph: remove the defect, rebuild the surface with the same material, texture, colour and lighting as the
surrounding area. Everything outside the selection must stay exactly the same."""

RETOUCH_NEG = """blurry patch, visible seam, different colour, different material, smudged texture, new objects,
text, watermark, distorted geometry"""


# ======================================================================================
# Bloques reutilizables
# ======================================================================================
def note(g: Graph, text: str, title: str = "Léeme"):
    return g.add("MarkdownNote", [text], title=title)


def seedvr2_rescue(g: Graph, img_port, *, scale: float = 2.0):
    """SeedVR2: restaura y reescala fotos de cliente de mala calidad (móvil, JPEG, poca luz)."""
    up = g.add("ImageScaleBy", ["lanczos", scale], {"image": img_port}, title="1 · Pre-escalado (x2)")
    pre = g.add("SeedVR2Preprocess", [], {"resized_images": up.out(0)})
    vae = g.add("VAELoader", [SEEDVR2_VAE])
    unet = g.add("UNETLoader", [SEEDVR2_UNET, "default"])
    enc = g.add("VAEEncodeTiled", [512, 128, 4096, 8], {"pixels": pre.out(0), "vae": vae.out(0)})
    cond = g.add("SeedVR2Conditioning", [], {"model": unet.out(0), "vae_conditioning": enc.out(0)})
    ks = g.add(
        "KSampler",
        [0, "fixed", 1, 1.0, "euler", "simple", 1.0],
        {
            "model": unet.out(0),
            "positive": cond.out(0),
            "negative": cond.out(1),
            "latent_image": enc.out(0),
        },
        title="SeedVR2 · 1 paso",
    )
    dec = g.add("VAEDecodeTiled", [512, 128, 4096, 8], {"samples": ks.out(0), "vae": vae.out(0)})
    post = g.add(
        "SeedVR2PostProcessing",
        ["lab"],
        {"images": dec.out(0), "original_resized_images": up.out(0)},
        title="Corrección de color",
    )
    return post.out(0)


def qwen_edit_engine(
    g: Graph,
    image_port,
    prompt_pos: str,
    prompt_neg: str,
    *,
    seed: int = 1,
    image2=None,
    image3=None,
    steps_quality: int = 20,
    cfg_quality: float = 4.0,
    scale: str = "kontext",
    noise_mask=None,
    noise_mask_switch=None,
    differential: bool = False,
):
    """Motor Qwen-Image-Edit 2511 con conmutador TURBO (LoRA Lightning, 4 pasos) / CALIDAD.

    Devuelve (puerto_imagen_salida, puerto_imagen_entrada_normalizada).
    """
    unet = g.add("UNETLoader", [QWEN_UNET, "default"], title="Modelo · Qwen-Image-Edit 2511")
    clip = g.add("CLIPLoader", [QWEN_CLIP, "qwen_image", "default"], title="Text encoder · Qwen2.5-VL 7B")
    vae = g.add("VAELoader", [QWEN_VAE], title="VAE · Qwen-Image")

    ms = g.add("ModelSamplingAuraFlow", [3.1], {"model": unet.out(0)})
    cfgn = g.add("CFGNorm", [1.0, False], {"model": ms.out(0)})
    model_port = cfgn.out(0)
    if differential:
        dd = g.add(
            "DifferentialDiffusion",
            [],
            {"model": model_port},
            title="Differential Diffusion (fundido suave de máscara)",
        )
        model_port = dd.out(0)

    lora = g.add("LoraLoaderModelOnly", [QWEN_TURBO_LORA, 1.0], {"model": model_port}, title="LoRA Lightning 4 pasos")

    turbo = g.add(
        "PrimitiveBoolean",
        [False],
        title="⚡ TURBO  (false = CALIDAD)",
        color=ORANGE,
    )
    sw_model = g.add(
        "ComfySwitchNode",
        [False],
        {"on_false": model_port, "on_true": lora.out(0), "switch": turbo.out(0)},
        title="Modelo: calidad / turbo",
    )
    steps_q = g.add("PrimitiveInt", [steps_quality, "fixed"], title="Pasos (calidad)")
    steps_t = g.add("PrimitiveInt", [4, "fixed"], title="Pasos (turbo)")
    cfg_q = g.add("PrimitiveFloat", [cfg_quality], title="CFG (calidad)")
    cfg_t = g.add("PrimitiveFloat", [1.0], title="CFG (turbo)")
    sw_steps = g.add(
        "ComfySwitchNode",
        [False],
        {"on_false": steps_q.out(0), "on_true": steps_t.out(0), "switch": turbo.out(0)},
        title="Pasos",
    )
    sw_cfg = g.add(
        "ComfySwitchNode",
        [False],
        {"on_false": cfg_q.out(0), "on_true": cfg_t.out(0), "switch": turbo.out(0)},
        title="CFG",
    )

    if scale == "kontext":
        fit_port = g.add(
            "FluxKontextImageScale", [], {"image": image_port}, title="Ajuste a resolución óptima"
        ).out(0)
    elif scale == "total":
        fit_port = g.add(
            "ImageScaleToTotalPixels",
            ["lanczos", 1.0, 16],
            {"image": image_port},
            title="Ajuste a 1 MP (conserva proporción)",
        ).out(0)
    else:
        fit_port = image_port

    pos_in = {"clip": clip.out(0), "vae": vae.out(0), "image1": fit_port}
    if image2 is not None:
        pos_in["image2"] = image2
    if image3 is not None:
        pos_in["image3"] = image3
    pos_widgets = [prompt_pos if isinstance(prompt_pos, str) else ""]
    neg_widgets = [prompt_neg if isinstance(prompt_neg, str) else ""]
    if not isinstance(prompt_pos, str):
        pos_in_pos = dict(pos_in, prompt=prompt_pos)
    else:
        pos_in_pos = dict(pos_in)
    if not isinstance(prompt_neg, str):
        pos_in_neg = dict(pos_in, prompt=prompt_neg)
    else:
        pos_in_neg = dict(pos_in)
    pos = g.add("TextEncodeQwenImageEditPlus", pos_widgets, pos_in_pos, title="PROMPT ✅ positivo")
    neg = g.add("TextEncodeQwenImageEditPlus", neg_widgets, pos_in_neg, title="PROMPT ❌ negativo")
    pos_r = g.add("FluxKontextMultiReferenceLatentMethod", ["index_timestep_zero"], {"conditioning": pos.out(0)})
    neg_r = g.add("FluxKontextMultiReferenceLatentMethod", ["index_timestep_zero"], {"conditioning": neg.out(0)})

    lat = g.add("VAEEncode", [], {"pixels": fit_port, "vae": vae.out(0)})
    lat_port = lat.out(0)
    if noise_mask is not None:
        snm = g.add(
            "SetLatentNoiseMask",
            [],
            {"samples": lat_port, "mask": noise_mask},
            title="Denoise sólo dentro de la selección",
        )
        if noise_mask_switch is None:
            lat_port = snm.out(0)
        else:
            lat_port = g.add(
                "ComfySwitchNode",
                [False],
                {"on_false": lat_port, "on_true": snm.out(0), "switch": noise_mask_switch},
                title="Latente: completo / sólo zona marcada",
            ).out(0)

    ks = g.add(
        "KSampler",
        [seed, "randomize", steps_quality, cfg_quality, "euler", "simple", 1.0],
        {
            "model": sw_model.out(0),
            "positive": pos_r.out(0),
            "negative": neg_r.out(0),
            "latent_image": lat_port,
            "steps": sw_steps.out(0),
            "cfg": sw_cfg.out(0),
        },
        title="KSampler",
    )
    dec = g.add("VAEDecode", [], {"samples": ks.out(0), "vae": vae.out(0)})
    return dec.out(0), fit_port


def flux2_klein_engine(g: Graph, image_port, prompt, *, ref_port=None, seed: int = 1, steps: int = 4):
    """Motor FLUX.2 [klein] 9B destilado (4 pasos, Apache-2.0)."""
    unet = g.add("UNETLoader", [FLUX2_UNET, "default"], title="Modelo · FLUX.2 klein 9B")
    clip = g.add("CLIPLoader", [FLUX2_CLIP, "flux2", "default"], title="Text encoder · Qwen3 8B")
    vae = g.add("VAELoader", [FLUX2_VAE], title="VAE · FLUX.2")

    fit = g.add("ImageScaleToTotalPixels", ["lanczos", 1.0, 16], {"image": image_port}, title="Ajuste a 1 MP")
    enc = g.add("VAEEncode", [], {"pixels": fit.out(0), "vae": vae.out(0)})
    txt_in = {"clip": clip.out(0)}
    if isinstance(prompt, str):
        txt_widgets = [prompt]
    else:
        txt_widgets, txt_in["text"] = [""], prompt
    txt = g.add("CLIPTextEncode", txt_widgets, txt_in, title="PROMPT (FLUX.2)")
    zero = g.add("ConditioningZeroOut", [], {"conditioning": txt.out(0)})

    pos = g.add("ReferenceLatent", [], {"conditioning": txt.out(0), "latent": enc.out(0)})
    neg = g.add("ReferenceLatent", [], {"conditioning": zero.out(0), "latent": enc.out(0)})
    if ref_port is not None:
        fit2 = g.add("ImageScaleToTotalPixels", ["lanczos", 1.0, 16], {"image": ref_port}, title="Referencia a 1 MP")
        enc2 = g.add("VAEEncode", [], {"pixels": fit2.out(0), "vae": vae.out(0)})
        pos = g.add("ReferenceLatent", [], {"conditioning": pos.out(0), "latent": enc2.out(0)})
        neg = g.add("ReferenceLatent", [], {"conditioning": neg.out(0), "latent": enc2.out(0)})

    size = g.add("GetImageSize", [], {"image": fit.out(0)})
    lat = g.add("EmptyFlux2LatentImage", [1024, 1024, 1], {"width": size.out(0), "height": size.out(1)})
    sig = g.add("Flux2Scheduler", [steps, 1024, 1024], {"width": size.out(0), "height": size.out(1)})
    guider = g.add("CFGGuider", [1.0], {"model": unet.out(0), "positive": pos.out(0), "negative": neg.out(0)})
    sampler = g.add("KSamplerSelect", ["euler"])
    noise = g.add("RandomNoise", [seed, "randomize"])
    smp = g.add(
        "SamplerCustomAdvanced",
        [],
        {
            "noise": noise.out(0),
            "guider": guider.out(0),
            "sampler": sampler.out(0),
            "sigmas": sig.out(0),
            "latent_image": lat.out(0),
        },
    )
    dec = g.add("VAEDecode", [], {"samples": smp.out(0), "vae": vae.out(0)})
    return dec.out(0)


def cutout_block(g: Graph, img_port, *, erode: int = -2, feather: int = 3, preview: bool = True):
    """BiRefNet -> máscara del producto (alpha), ya erosionada y suavizada."""
    bgm = g.add("LoadBackgroundRemovalModel", [BIREFNET], title="BiRefNet")
    rb = g.add("RemoveBackground", [], {"bg_removal_model": bgm.out(0), "image": img_port})
    inv = g.add("InvertMask", [], {"mask": rb.out(0)}, title="→ alpha del producto")
    grow = g.add("GrowMask", [erode, True], {"mask": inv.out(0)}, title="Erosionar borde (halo)")
    fea = g.add("FeatherMask", [feather] * 4, {"mask": grow.out(0)}, title="Suavizar borde")
    # Un nodo de salida siempre se ejecuta, así que rompería la evaluación perezosa de los
    # interruptores: cuando el bloque está en una rama opcional se deja silenciado (Ctrl+M).
    g.add(
        "MaskPreview",
        [],
        {"mask": fea.out(0)},
        title="Comprobar máscara" + ("" if preview else "  (Ctrl+M para activar)"),
        mode=0 if preview else MODE_NEVER,
    )
    return fea.out(0)


def gan_finish(g: Graph, img_port, prefix: str, *, largest: int = 2048):
    up_model = g.add("UpscaleModelLoader", [GAN_UPSCALER], title="Upscaler GAN 4x")
    up = g.add("ImageUpscaleWithModel", [], {"upscale_model": up_model.out(0), "image": img_port})
    fit = g.add("ImageScaleToMaxDimension", ["lanczos", largest], {"image": up.out(0)}, title=f"Lado largo {largest}px")
    sharp = g.add("ImageSharpen", [1, 0.8, 0.28], {"image": fit.out(0)}, title="Enfoque final (sutil)")
    g.add("SaveImage", [prefix], {"images": sharp.out(0)}, title="GUARDAR final")
    return sharp.out(0)


# ======================================================================================
# 00 · Rescate de la foto del cliente
# ======================================================================================
def build_rescue():
    g = Graph("00-rescate")
    with g.group("ENTRADA · foto del cliente", BLUE):
        note(
            g,
            "# 00 · Rescate de foto de cliente\n\n"
            "Para fotos **malas**: de móvil, pequeñas, con ruido, JPEG machacado, poca luz o desenfocadas.\n\n"
            "1. Sube la foto en **Cargar imagen**.\n"
            "2. Ejecuta. SeedVR2 reconstruye detalle real (no es un simple upscaler).\n"
            "3. El resultado se guarda en `output/rescate/`; úsalo como entrada del workflow 01 o 02.\n\n"
            "**Ajustes**\n"
            "- *Pre-escalado*: 2x normal, 3–4x si la foto es diminuta. Más = más VRAM.\n"
            "- Si te quedas sin VRAM: baja el pre-escalado o usa el modelo 3B (ya puesto).\n"
            "- `color_correction_method`: `lab` es el más fiel; `wavelet` conserva más detalle fino.\n\n"
            "## Modelos necesarios\n"
            "- `models/diffusion_models/seedvr2_3b_int8_convrot.safetensors`\n"
            "- `models/vae/seedvr2_ema_vae_fp16.safetensors`\n"
            "- `models/upscale_models/RealESRGAN_x4plus.safetensors`\n\n"
            "Enlaces en `docs/MODELOS.md`.",
            title="Instrucciones",
        )
        src = g.add("LoadImage", ["ejemplo_producto.png", "image"], title="Cargar imagen (foto del cliente)")

    with g.group("RESTAURACIÓN · SeedVR2 3B", GREEN):
        fixed = seedvr2_rescue(g, src.out(0), scale=2.0)

    with g.group("SALIDA", PURPLE):
        g.add("SaveImage", ["rescate/limpia"], {"images": fixed}, title="GUARDAR limpia")
        g.add("ImageCompare", [], {"image_a": src.out(0), "image_b": fixed}, title="Antes / después")

    g.save(os.path.join(OUT, "00_rescate_foto_cliente.json"))


# ======================================================================================
# 01 · Packshot de catálogo (3 niveles)
# ======================================================================================
def build_packshot():
    g = Graph("01-packshot")

    with g.group("ENTRADA", BLUE):
        note(
            g,
            "# 01 · Packshot de catálogo\n\n"
            "Foto de producto para ficha de tienda: fondo limpio, luz de estudio y sombra natural.\n\n"
            "## Cómo se usa\n"
            "1. **Cargar imagen** → sube la foto del cliente (tal cual, aunque sea mala).\n"
            "2. Elige el **nivel** (ver más abajo) y pulsa *Ejecutar*.\n\n"
            "## Niveles\n"
            "| Nivel | Qué hace | Cuándo |\n"
            "|---|---|---|\n"
            "| **0 · Rescate** | SeedVR2 reconstruye una foto mala | foto de móvil, ruido, JPEG, borrosa |\n"
            "| **1 · Packshot** | Qwen-Image-Edit 2511 rehace fondo + luz + sombra | siempre |\n"
            "| **2 · Recorte** | BiRefNet recorta, fondo blanco puro + sombra de contacto | Amazon/marketplace, PNG con alpha |\n"
            "| **3 · Alta resolución** | Upscaler GAN 4x + reencuadre + enfoque | entrega final |\n\n"
            "Cada nivel tiene un **interruptor booleano** (`⚡`/`Nivel …`) para encenderlo o apagarlo.\n"
            "Los interruptores son perezosos: la rama apagada **no se ejecuta ni carga modelos**.\n\n"
            "## Calidad vs velocidad\n"
            "El interruptor **⚡ TURBO** cambia entre LoRA Lightning (4 pasos, CFG 1) y calidad (20 pasos, CFG 4).\n"
            "Empieza en TURBO para encuadrar el prompt, y pásalo a calidad para la toma final.",
            title="LÉEME PRIMERO",
        )
        src = g.add("LoadImage", ["ejemplo_producto.png", "image"], title="Cargar imagen (foto del cliente)")
        base = g.add(
            "ImageScaleToTotalPixels",
            ["lanczos", 1.0, 16],
            {"image": src.out(0)},
            title="Normalizar a 1 MP",
        )

    with g.group("NIVEL 0 · Rescate de foto mala (SeedVR2) — opcional", GREEN):
        note(
            g,
            "### Nivel 0 — Rescate\n\n"
            "Pon **`Nivel 0`** en `true` cuando la foto del cliente venga mal: móvil, poca luz, ruido, "
            "compresión JPEG, poco tamaño o algo desenfocada.\n\n"
            "Si está en `false`, SeedVR2 **no se carga** (no gasta VRAM ni tiempo).",
            title="Cuándo activarlo",
        )
        rescued = seedvr2_rescue(g, base.out(0), scale=2.0)
        rescued_fit = g.add(
            "ImageScaleToTotalPixels", ["lanczos", 1.0, 16], {"image": rescued}, title="Volver a 1 MP"
        )
        use_rescue = g.add("PrimitiveBoolean", [False], title="Nivel 0 · usar rescate", color=ORANGE)
        sw_in = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": base.out(0), "on_true": rescued_fit.out(0), "switch": use_rescue.out(0)},
            title="Entrada del packshot",
        )

    with g.group("NIVEL 1 · Packshot con Qwen-Image-Edit 2511", PURPLE):
        note(
            g,
            "### Nivel 1 — Packshot\n\n"
            "El modelo de edición rehace **fondo + iluminación + sombra** conservando el producto.\n\n"
            "**Reglas de prompt que funcionan**\n"
            "- Di siempre qué se conserva: *keep the logo and label text exactly as in the input image*.\n"
            "- Describe la luz como un fotógrafo: *softbox key light from the upper left, soft fill, rim light*.\n"
            "- Pide la sombra explícitamente: *soft realistic contact shadow directly underneath*.\n"
            "- Fondo: *seamless pure white studio background (#FFFFFF)*; para degradado gris pide "
            "*light grey seamless gradient background, darker at the top*.\n\n"
            "Más plantillas de prompt en `docs/PROMPTS.md`.",
            title="Prompting",
        )
        packshot, _ = qwen_edit_engine(
            g, sw_in.out(0), PACKSHOT_POS, PACKSHOT_NEG, seed=815, steps_quality=20, cfg_quality=4.0
        )
        g.add("PreviewImage", [], {"images": packshot}, title="Previsualizar nivel 1")

    with g.group("NIVEL 2 · Recorte BiRefNet + fondo blanco puro + sombra", ORANGE):
        note(
            g,
            "### Nivel 2 — Recorte y fondo garantizado\n\n"
            "El nivel 1 da un fondo *casi* blanco. Los marketplaces suelen exigir **255,255,255 exacto**.\n"
            "Aquí BiRefNet recorta el producto y lo pega sobre un blanco puro generado, con una sombra "
            "de contacto sintética por debajo.\n\n"
            "**Ajustes**\n"
            "- `Erosionar borde` = `-2` quita el halo del recorte. Pon `-4` si aún se ve borde claro.\n"
            "- `color` del fondo: `16777215` = blanco. Para gris claro usa `15790320` (#F0F0F0).\n"
            "- Sombra: sube/baja `blend_factor` del nodo *Sombra de contacto* (0 = sin sombra).\n"
            "- Se guarda además un **PNG con transparencia** listo para montar sobre cualquier fondo.\n\n"
            "> El recorte se calcula siempre (BiRefNet tarda ~1 s y el PNG transparente se guarda igualmente); "
            "el interruptor `Nivel 2` sólo decide **qué imagen pasa al nivel 3**: la del modelo o la recortada.\n\n"
            "> Si la máscara sale invertida (se recorta el fondo en vez del producto), borra el nodo "
            "`InvertMask` — la convención de máscaras depende del modelo de segmentación que cargues.",
            title="Cómo ajustarlo",
        )
        alpha = cutout_block(g, packshot, erode=-2, feather=3)
        size = g.add("GetImageSize", [], {"image": packshot})
        bg = g.add(
            "EmptyImage",
            [1024, 1024, 1, 16777215],
            {"width": size.out(0), "height": size.out(1)},
            title="Fondo blanco puro",
        )
        mask_img = g.add("MaskToImage", [], {"mask": alpha})
        mask_inv = g.add("ImageInvert", [], {"image": mask_img.out(0)})
        shadow = g.add("ImageBlur", [31, 10.0], {"image": mask_inv.out(0)}, title="Desenfoque de sombra")
        bg_shadow = g.add(
            "ImageBlend",
            [0.22, "multiply"],
            {"image1": bg.out(0), "image2": shadow.out(0)},
            title="Sombra de contacto",
        )
        comp = g.add(
            "ImageCompositeMasked",
            [0, 0, False],
            {"destination": bg_shadow.out(0), "source": packshot, "mask": alpha},
            title="Producto sobre fondo limpio",
        )
        rgba = g.add("JoinImageWithAlpha", [], {"image": packshot, "alpha": alpha}, title="RGBA")
        g.add("SaveImage", ["packshot/recorte_transparente"], {"images": rgba.out(0)}, title="GUARDAR PNG alpha")

        use_cutout = g.add("PrimitiveBoolean", [True], title="Nivel 2 · usar recorte", color=ORANGE)
        sw_lvl2 = g.add(
            "ComfySwitchNode",
            [True],
            {"on_false": packshot, "on_true": comp.out(0), "switch": use_cutout.out(0)},
            title="Salida del nivel 2",
        )

    with g.group("NIVEL 3 · Alta resolución y entrega", RED):
        note(
            g,
            "### Nivel 3 — Alta resolución\n\n"
            "Upscaler GAN 4x (rápido y fiel; no inventa detalle) → reencuadre al lado largo deseado → "
            "enfoque sutil.\n\n"
            "- `Lado largo 2048px`: cámbialo a 1600 / 2400 / 3000 según lo que pida la tienda.\n"
            "- Si quieres que el reescalado **invente** micro-detalle real en vez de sólo interpolar, "
            "usa el workflow `00_rescate_foto_cliente.json` sobre la salida.\n"
            "- Alternativas al modelo GAN: `4x-UltraSharp.safetensors`, `4x_NMKD-Siax_200k.pth`.",
            title="Entrega",
        )
        final = gan_finish(g, sw_lvl2.out(0), "packshot/final", largest=2048)
        g.add("ImageCompare", [], {"image_a": src.out(0), "image_b": final}, title="Original / packshot")

    g.save(os.path.join(OUT, "01_packshot_catalogo.json"))


# ======================================================================================
# 02 · Lifestyle (producto dentro de una escena)
# ======================================================================================
def build_lifestyle():
    g = Graph("02-lifestyle")

    with g.group("ENTRADAS", BLUE):
        note(
            g,
            "# 02 · Lifestyle — el producto dentro de una escena\n\n"
            "La crema en un baño de mármol, el vino en una mesa de terraza, la zapatilla sobre hormigón…\n\n"
            "## Cómo se usa\n"
            "1. **Producto** → la foto del cliente (mejor si ya pasó por el workflow 01, pero sirve cruda).\n"
            "2. **Referencia de escena** *(opcional)* → una foto del ambiente/estilo que quieres copiar.\n"
            "   Si no quieres usarla, selecciona ese nodo y pulsa **Ctrl+B** (bypass).\n"
            "3. Escribe la escena en el prompt y ejecuta.\n\n"
            "## Dos motores (elige con el interruptor)\n"
            "| | Qwen-Image-Edit 2511 | FLUX.2 [klein] 9B |\n"
            "|---|---|---|\n"
            "| Fidelidad de etiqueta/logo | **la mejor** | buena |\n"
            "| Realismo de escena y luz | muy bueno | **el mejor** |\n"
            "| Multi-imagen (producto + escena) | sí, hasta 3 | no en este grafo, sólo texto |\n"
            "| Velocidad | 4 pasos con LoRA turbo | 4 pasos (destilado) |\n"
            "| Licencia | Apache-2.0 | Apache-2.0 |\n\n"
            "Sólo se carga el motor seleccionado: el interruptor es perezoso.\n\n"
            "## Si la foto del cliente es mala\n"
            "Pon **`Nivel 0`** en `true`: SeedVR2 la reconstruye antes de montarla en la escena. "
            "Es importante aquí — un producto con ruido o pixelado dentro de una escena limpia canta muchísimo.",
            title="LÉEME PRIMERO",
        )
        prod = g.add("LoadImage", ["ejemplo_producto.png", "image"], title="Producto (foto del cliente)")
        ref = g.add("LoadImage", ["ejemplo_escena.png", "image"], title="Referencia de escena (opcional · Ctrl+B)")
        base = g.add("ImageScaleToTotalPixels", ["lanczos", 1.0, 16], {"image": prod.out(0)}, title="Normalizar a 1 MP")

    with g.group("NIVEL 0 · Rescate de foto mala (SeedVR2) — opcional", GREEN):
        rescued = seedvr2_rescue(g, base.out(0), scale=2.0)
        rescued_fit = g.add("ImageScaleToTotalPixels", ["lanczos", 1.0, 16], {"image": rescued}, title="Volver a 1 MP")
        use_rescue = g.add("PrimitiveBoolean", [False], title="Nivel 0 · usar rescate", color=ORANGE)
        sw_in = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": base.out(0), "on_true": rescued_fit.out(0), "switch": use_rescue.out(0)},
            title="Producto listo",
        )

    with g.group("MOTOR A · Qwen-Image-Edit 2511 (multi-imagen)", PURPLE):
        note(
            g,
            "### Motor A — Qwen-Image-Edit 2511\n\n"
            "`image1` = producto, `image2` = referencia de escena. En el prompt refiérete a ellas como "
            "*image 1* / *image 2*, p.ej.:\n\n"
            "> *Place the product from image 1 into the scene of image 2. Match the lighting of image 2…*\n\n"
            "Si no usas referencia (nodo en bypass), describe la escena entera con palabras.\n\n"
            "**Lo que más ayuda al realismo**: dirección de la luz, temperatura de color, sombra de contacto, "
            "reflejo en la superficie, óptica (*50mm f/2.8*) y profundidad de campo.",
            title="Prompting lifestyle",
        )
        qwen_raw, qwen_fitted = qwen_edit_engine(
            g,
            sw_in.out(0),
            LIFESTYLE_POS,
            LIFESTYLE_NEG,
            seed=2024,
            image2=ref.out(0),
            steps_quality=20,
            cfg_quality=4.0,
        )

    with g.group("PROTEGER LA ETIQUETA (opcional, sólo motor A)", ORANGE):
        note(
            g,
            "### Proteger la etiqueta\n\n"
            "Si el motor A te deforma el logo o el texto, este bloque vuelve a pegar los **píxeles originales "
            "del producto** dentro de su silueta, conservando la escena y la luz generadas.\n\n"
            "Sólo es válido cuando el producto **no se ha movido** (Qwen-Image-Edit suele mantener la "
            "composición al cambiar sólo el fondo). Si sí se movió, o usas el motor B, corrige con "
            "`03_retoque_zona.json` marcando la etiqueta con el pincel.\n\n"
            "Está en `false` por defecto. Ojo: al pegar el producto original pierdes la reiluminación sobre "
            "él, así que úsalo sólo si la etiqueta ha salido mal.",
            title="Cuándo usarlo",
        )
        alpha = cutout_block(g, qwen_raw, erode=-3, feather=4, preview=False)
        protect = g.add("PrimitiveBoolean", [False], title="Proteger etiqueta", color=ORANGE)
        comp = g.add(
            "ImageCompositeMasked",
            [0, 0, False],
            {"destination": qwen_raw, "source": qwen_fitted, "mask": alpha},
            title="Pegar producto original",
        )
        qwen_img = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": qwen_raw, "on_true": comp.out(0), "switch": protect.out(0)},
            title="Salida motor A",
        ).out(0)

    with g.group("MOTOR B · FLUX.2 [klein] 9B destilado", BLUE):
        note(
            g,
            "### Motor B — FLUX.2 [klein]\n\n"
            "4 pasos, CFG 1, `Flux2Scheduler`. Muy bueno en luz y materiales; el prompt es lenguaje natural "
            "largo, sin negativo (usa `ConditioningZeroOut`).\n\n"
            "Este motor trabaja **sólo con el producto y el texto**: describe la escena con palabras. "
            "La referencia de escena es exclusiva del motor A.\n\n"
            "Para VRAM baja cambia en los cargadores:\n"
            "`flux-2-klein-9b-fp8.safetensors` → `flux-2-klein-4b-fp8.safetensors` y "
            "`qwen_3_8b_fp8mixed.safetensors` → `qwen_3_4b.safetensors`.",
            title="Notas FLUX.2",
        )
        flux_img = flux2_klein_engine(g, sw_in.out(0), LIFESTYLE_POS, seed=2024, steps=4)

    with g.group("SELECCIÓN DE MOTOR", GREY):
        engine = g.add("PrimitiveBoolean", [False], title="Motor: false = Qwen · true = FLUX.2", color=ORANGE)
        sw_engine = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": qwen_img, "on_true": flux_img, "switch": engine.out(0)},
            title="Imagen lifestyle",
        )
        g.add("PreviewImage", [], {"images": sw_engine.out(0)}, title="Previsualizar escena")

    with g.group("ALTA RESOLUCIÓN Y ENTREGA", RED):
        final = gan_finish(g, sw_engine.out(0), "lifestyle/final", largest=2048)
        g.add("ImageCompare", [], {"image_a": prod.out(0), "image_b": final}, title="Original / lifestyle")

    g.save(os.path.join(OUT, "02_lifestyle_escena.json"))


# ======================================================================================
# 03 · Retoque por zona marcada (estilo "rodear con un círculo")
# ======================================================================================
def build_retouch():
    g = Graph("03-retoque")

    with g.group("ENTRADA Y SELECCIÓN", BLUE):
        note(
            g,
            "# 03 · Retoque por zona — “rodear lo que no me gusta”\n\n"
            "Es el equivalente local de marcar con un círculo en un chat: en vez de rehacer toda la foto, "
            "**pintas la zona** y sólo eso se regenera.\n\n"
            "## Cómo se marca la zona\n"
            "1. Carga la imagen a corregir en **Cargar imagen**.\n"
            "2. **Clic derecho sobre el nodo → “Open in MaskEditor”** (Editor de máscaras).\n"
            "3. Pinta encima de lo que no te gusta (un brochazo o un círculo relleno) y pulsa **Save**.\n"
            "4. Escribe en el prompt qué quieres que pase ahí y ejecuta.\n\n"
            "La salida `MASK` del nodo *Cargar imagen* es justo lo que has pintado.\n\n"
            "## Por qué sólo cambia lo marcado\n"
            "- `SetLatentNoiseMask` obliga al sampler a difuminar únicamente dentro de la máscara.\n"
            "- `DifferentialDiffusion` hace que el borde de la máscara se funda en vez de cortar.\n"
            "- `ImageCompositeMasked` al final vuelve a pegar el resto de píxeles originales, bit a bit.\n\n"
            "## Ajustes\n"
            "- `Ampliar selección` (+16): dale margen al modelo para que empalme bien. Súbelo si se nota el parche.\n"
            "- `Suavizar borde` (24 px): más = transición más larga.\n"
            "- Para cambios pequeños (una mota, un reflejo) baja `denoise` del KSampler a 0.6–0.8.\n\n"
            "## Ejemplos de prompt\n"
            "- *Remove the dust specks and fingerprints from the selected area, keep the glossy plastic texture.*\n"
            "- *Replace the selected background area with clean seamless white studio backdrop.*\n"
            "- *Make the selected label text sharp and perfectly readable, same font and colours.*\n"
            "- *Remove the reflection of the photographer in the selected area of the glass.*",
            title="LÉEME PRIMERO",
        )
        src = g.add("LoadImage", ["ejemplo_packshot.png", "image"], title="Cargar imagen → MaskEditor")
        base = g.add("ImageScaleToTotalPixels", ["lanczos", 1.0, 16], {"image": src.out(0)}, title="Normalizar a 1 MP")
        grow = g.add("GrowMask", [16, True], {"mask": src.out(1)}, title="Ampliar selección")
        fea = g.add("FeatherMask", [24] * 4, {"mask": grow.out(0)}, title="Suavizar borde")
        g.add("MaskPreview", [], {"mask": fea.out(0)}, title="Zona que se va a regenerar")

    with g.group("REGENERAR SÓLO LA ZONA (Qwen-Image-Edit 2511)", PURPLE):
        edited, fitted = qwen_edit_engine(
            g,
            base.out(0),
            RETOUCH_POS,
            RETOUCH_NEG,
            seed=77,
            steps_quality=20,
            cfg_quality=4.0,
            scale="total",
            noise_mask=fea.out(0),
            differential=True,
        )

    with g.group("REINTEGRAR Y GUARDAR", RED):
        comp = g.add(
            "ImageCompositeMasked",
            [0, 0, True],
            {"destination": fitted, "source": edited, "mask": fea.out(0)},
            title="Sólo la zona marcada",
        )
        g.add("SaveImage", ["retoque/corregida"], {"images": comp.out(0)}, title="GUARDAR corregida")
        g.add("ImageCompare", [], {"image_a": fitted, "image_b": comp.out(0)}, title="Antes / después")

    g.save(os.path.join(OUT, "03_retoque_zona.json"))


# ======================================================================================
# 10 · Estudio de producto — todo en uno, con selector de tipo de foto
# ======================================================================================
PACK_TAIL = (
    "Product: keep the geometry, proportions, colours, materials, logo and label text EXACTLY as in "
    "the input image, perfectly readable.\n"
    "Camera: straight-on product shot, centred, even margins, sharp focus, high micro-detail, "
    "neutral white balance."
)
LIFE_TAIL = (
    "Integration: match the scene's light direction, colour temperature and contrast onto the product, "
    "add a realistic contact shadow and a subtle reflection on the surface, correct perspective, the "
    "product sits naturally on the surface.\n"
    "Product: keep its shape, proportions, materials, logo and label text pixel-accurate and fully "
    "readable, do not redesign it.\n"
    "Camera: 50mm lens at f/2.8, shallow depth of field with the product in sharp focus, editorial "
    "commercial photography."
)


def _packshot(background: str, lighting: str) -> str:
    return (
        "Turn this into a professional e-commerce packshot of the product.\n\n"
        f"Background: {background}\n"
        f"Lighting: {lighting}\n"
        "Shadow: one soft realistic contact shadow directly underneath the product, grounding it on "
        "the surface.\n" + PACK_TAIL
    )


def _lifestyle(scene: str) -> str:
    return (
        "Place the product from image 1 into a photorealistic lifestyle scene.\n\n"
        f"Scene: {scene}\n" + LIFE_TAIL
    )


CATALOGO = {
    "packshot_blanco": _packshot(
        "seamless pure white studio cyclorama (#FFFFFF), completely clean, no props, no text, no watermark.",
        "large softbox key light from the upper left, soft fill from the right, subtle rim light "
        "separating the edges from the background, no blown highlights, no colour cast.",
    ),
    "packshot_degradado_gris": _packshot(
        "light grey seamless gradient background, brighter behind the product, darker towards the "
        "corners, no props, no text.",
        "large softbox key light from the upper left, soft fill from the right, rim light on the edges, "
        "smooth gradient falloff.",
    ),
    "packshot_superficie_reflejo": _packshot(
        "product standing on a glossy white acrylic surface with a soft mirror reflection below it, "
        "seamless white backdrop behind.",
        "two large strip softboxes at both sides creating clean vertical highlights, soft overhead fill.",
    ),
    "packshot_fondo_color": _packshot(
        "seamless solid pastel sand background (#E8DCC8), completely uniform, no texture, no props.",
        "soft frontal key light with a gentle gradient, low contrast, editorial catalogue look.",
    ),
    "lifestyle_bano_marmol": _lifestyle(
        "a bright modern bathroom, white marble countertop with subtle grey veining, soft morning light "
        "through a window on the left, a folded linen towel and a small eucalyptus branch blurred behind."
    ),
    "lifestyle_terraza_atardecer": _lifestyle(
        "a wooden terrace table at golden hour, warm low sun from behind creating long soft shadows, "
        "blurred mediterranean garden and sea in the background, empty glasses out of focus."
    ),
    "lifestyle_cocina_nordica": _lifestyle(
        "a light oak kitchen counter, matte white tiles behind, diffused daylight from a large window on "
        "the right, fresh ingredients scattered and blurred in the background."
    ),
    "lifestyle_hormigon_estudio": _lifestyle(
        "a raw polished concrete surface, cool overcast daylight from above, deep neutral grey "
        "background, minimal styling, a single hard-edged soft shadow."
    ),
    "lifestyle_escritorio_madera": _lifestyle(
        "a walnut desk with a linen notebook and a matte black pen slightly out of focus, warm lamp "
        "light from the upper right mixed with cool window light from the left."
    ),
    "lifestyle_mesita_noche": _lifestyle(
        "a dark wooden nightstand at night, warm candlelight from the left as the only light source, "
        "deep shadows, cosy and intimate atmosphere."
    ),
    "lifestyle_exterior_natural": _lifestyle(
        "a flat mossy rock in a forest clearing, dappled sunlight filtering through leaves, soft green "
        "bokeh in the background."
    ),
    "lifestyle_usar_referencia": (
        "Place the product from image 1 into the scene of image 2.\n\n"
        "Match the lighting direction, colour temperature, contrast and grain of image 2 exactly.\n"
        "Put the product on the main surface of image 2 at a realistic scale, with a contact shadow "
        "consistent with the light in image 2.\n"
        "Do not change the background composition of image 2.\n" + LIFE_TAIL
    ),
    "retoque_zona_marcada": (
        "Only change what is inside the selected area. Fix it so it looks like a clean, professional "
        "product photograph: remove the defect and rebuild the surface with the same material, texture, "
        "colour and lighting as the surrounding area.\n"
        "Everything outside the selection must stay exactly the same."
    ),
}

NEGATIVO_COMUN = """blurry, out of focus, low resolution, jpeg artifacts, noise, distorted product,
deformed or invented logo, unreadable label text, wrong scale, floating product, missing shadow,
duplicated product, extra objects, props, hands, people, clutter, harsh shadows, double shadow,
colour cast, dirty background, reflections of the room, watermark, text overlay, oversaturated,
plastic look, cartoon, illustration"""


def combo(g: Graph, options: list[str], default: str, *, title: str, color: str = ORANGE):
    """Desplegable con opciones escritas por el usuario (nodo `CustomCombo` del núcleo)."""
    values = [default, options.index(default), *options, ""]
    return g.add("CustomCombo", values, title=title, color=color)


def build_estudio():
    g = Graph("10-estudio")

    # ---------------------------------------------------------------- entradas
    with g.group("1 · ENTRADAS", BLUE):
        note(
            g,
            "# Estudio de producto — todo en uno\n\n"
            "Subes la foto, **eliges en el desplegable qué tipo de foto quieres** y ejecutas. "
            "El grafo se reconfigura solo según lo que elijas.\n\n"
            "## En tres pasos\n"
            "1. Sube la foto del cliente en **1 · PRODUCTO**.\n"
            "2. En **TIPO DE FOTO** elige `packshot_…` o `lifestyle_…`.\n"
            "3. Ejecutar.\n\n"
            "## Los otros dos cargadores están en bypass\n"
            "Salen en gris a propósito, para no tener que subirles nada. Quítales el bypass con "
            "**Ctrl+B** sólo cuando los necesites:\n\n"
            "- **2 · REFERENCIA DE ESCENA** → para el tipo `lifestyle_usar_referencia`.\n"
            "- **3 · IMAGEN A RETOCAR** → para el tipo `retoque_zona_marcada`.\n\n"
            "## Qué hace cada cosa automáticamente\n"
            "- Tipo que contiene `packshot` → activa el recorte y el fondo blanco puro.\n"
            "- Tipo que contiene `retoque` → cambia a modo máscara: sólo se regenera lo que pintes.\n"
            "- Todo lo demás (rescate de foto mala, motor, turbo) son interruptores manuales.\n\n"
            "> Si prefieres los workflows sueltos y más simples, están en `01_packshot_catalogo.json`, "
            "`02_lifestyle_escena.json` y `03_retoque_zona.json`.",
            title="LÉEME PRIMERO",
        )
        prod = g.add("LoadImage", ["ejemplo_producto.png", "image"], title="1 · PRODUCTO (foto del cliente)")
        ref = g.add(
            "LoadImage",
            ["ejemplo_escena.png", "image"],
            title="2 · REFERENCIA DE ESCENA (Ctrl+B)",
            mode=MODE_BYPASS,
        )
        ret = g.add(
            "LoadImage",
            ["ejemplo_packshot.png", "image"],
            title="3 · IMAGEN A RETOCAR → MaskEditor (Ctrl+B)",
            mode=MODE_BYPASS,
        )

    # ------------------------------------------------------------- el selector
    with g.group("2 · QUÉ FOTO QUIERES  ←  el único mando que tienes que tocar", ORANGE):
        note(
            g,
            "### El desplegable manda\n\n"
            "**TIPO DE FOTO** elige una clave del catálogo de la derecha, y el nodo *Extract Text from "
            "JSON* saca ese prompt y lo enchufa a los tres motores.\n\n"
            "## Añadir tus propios tipos\n"
            "1. Escribe una entrada nueva en el **CATÁLOGO**: `\"mi_tipo\": \"tu prompt aquí\"`.\n"
            "2. Haz doble clic en el desplegable **TIPO DE FOTO** para añadir `mi_tipo` a la lista.\n\n"
            "Respeta el prefijo: lo que empiece por `packshot` activa el recorte sobre fondo puro, y lo "
            "que contenga `retoque` activa el modo máscara.\n\n"
            "El JSON tiene que ser válido: comillas dobles y sin coma final. Si te equivocas, el prompt "
            "sale vacío y la imagen no cambia — es la pista de que hay una coma de más.\n\n"
            "Los prompts largos y el porqué de cada línea están en `docs/PROMPTS.md`.",
            title="Cómo funciona / cómo ampliarlo",
        )
        tipo = combo(
            g,
            list(CATALOGO.keys()),
            "packshot_blanco",
            title="▼ TIPO DE FOTO",
        )
        catalogo = g.add(
            "PrimitiveStringMultiline",
            [json.dumps(CATALOGO, ensure_ascii=False, indent=2)],
            title="CATÁLOGO de prompts (JSON)",
        )
        prompt = g.add(
            "JsonExtractString",
            ["", ""],
            {"json_string": catalogo.out(0), "key": tipo.out(0)},
            title="PROMPT elegido",
        )
        negativo = g.add("PrimitiveStringMultiline", [NEGATIVO_COMUN], title="PROMPT ❌ negativo (común)")
        es_packshot = g.add(
            "StringContains",
            ["", "packshot", True],
            {"string": tipo.out(0)},
            title="¿es packshot? → recorte automático",
        )
        es_retoque = g.add(
            "StringContains",
            ["", "retoque", True],
            {"string": tipo.out(0)},
            title="¿es retoque? → modo máscara",
        )

    # ------------------------------------------------------------------ motor
    with g.group("3 · MOTOR", GREY):
        note(
            g,
            "### Qué motor usa\n\n"
            "| Opción | Qué es | Coste |\n"
            "|---|---|---|\n"
            "| `qwen_local` | Qwen-Image-Edit 2511 en tu GPU | gratis |\n"
            "| `flux2_local` | FLUX.2 [klein] 9B en tu GPU | gratis |\n"
            "| `gpt_image_api` | GPT Image 2.5 de OpenAI, por la nube | **se paga por imagen** |\n\n"
            "Sólo se ejecuta el motor elegido: los interruptores son perezosos, así que el modelo de "
            "los otros dos ni se carga ni se factura.\n\n"
            "**Para `retoque_zona_marcada` usa `qwen_local`**: es el único de los tres conectado a la "
            "máscara del MaskEditor en este grafo.\n\n"
            "`gpt_image_api` necesita saldo de API en tu cuenta de Comfy. El nodo enseña el precio "
            "estimado antes de ejecutar; con `quality: high` a 1024×1024 ronda los 0,08 $ por imagen.",
            title="Motores",
        )
        motor = combo(
            g,
            ["qwen_local", "flux2_local", "gpt_image_api"],
            "qwen_local",
            title="▼ MOTOR",
            color=GREY,
        )
        usar_flux = g.add(
            "StringCompare", ["", "flux2_local", "Equal", True], {"string_a": motor.out(0)}, title="¿FLUX.2?"
        )
        usar_gpt = g.add(
            "StringCompare", ["", "gpt_image_api", "Equal", True], {"string_a": motor.out(0)}, title="¿GPT Image?"
        )

    # ---------------------------------------------------------------- rescate
    with g.group("4 · RESCATE de foto mala (SeedVR2) — opcional", GREEN):
        note(
            g,
            "### Cuándo encenderlo\n\n"
            "Pon **`Rescate`** en `true` si la foto del cliente viene de móvil, con ruido, poca luz, "
            "compresión JPEG o poco tamaño. SeedVR2 la reconstruye antes de tocar nada más.\n\n"
            "En `false` no se carga: no gasta VRAM ni tiempo.\n\n"
            "Sube el *pre-escalado* a 3x o 4x si la foto es diminuta; bájalo si te quedas sin memoria.",
            title="Rescate",
        )
        base = g.add("ImageScaleToTotalPixels", ["lanczos", 1.0, 16], {"image": prod.out(0)}, title="Normalizar a 1 MP")
        rescued = seedvr2_rescue(g, base.out(0), scale=2.0)
        rescued_fit = g.add("ImageScaleToTotalPixels", ["lanczos", 1.0, 16], {"image": rescued}, title="Volver a 1 MP")
        use_rescue = g.add("PrimitiveBoolean", [False], title="Rescate", color=ORANGE)
        img_gen = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": base.out(0), "on_true": rescued_fit.out(0), "switch": use_rescue.out(0)},
            title="Producto listo",
        )

    # -------------------------------------------------------- entrada efectiva
    with g.group("5 · ENTRADA EFECTIVA Y MÁSCARA", BLUE):
        note(
            g,
            "### De dónde sale la imagen que entra al motor\n\n"
            "- Tipo normal → la foto del producto (rescatada o no), ajustada a la resolución óptima del "
            "modelo de edición.\n"
            "- Tipo `retoque_…` → la **imagen a retocar**, escalada conservando la proporción para que "
            "la máscara que pintaste siga cuadrando píxel a píxel.\n\n"
            "La máscara sale de la salida `MASK` del cargador 3, que es exactamente lo que pintaste en "
            "el MaskEditor. Se amplía 16 px y se suaviza 24 px para que el empalme no se note.",
            title="Entrada y máscara",
        )
        src = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": img_gen.out(0), "on_true": ret.out(0), "switch": es_retoque.out(0)},
            title="Imagen de partida",
        )
        kfit = g.add("FluxKontextImageScale", [], {"image": src.out(0)}, title="Resolución óptima (generar)")
        pfit = g.add(
            "ImageScaleToTotalPixels", ["lanczos", 1.0, 16], {"image": src.out(0)}, title="1 MP proporcional (retoque)"
        )
        img_in = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": kfit.out(0), "on_true": pfit.out(0), "switch": es_retoque.out(0)},
            title="Entrada del motor",
        )
        grow = g.add("GrowMask", [16, True], {"mask": ret.out(1)}, title="Ampliar selección")
        m_soft = g.add("FeatherMask", [24] * 4, {"mask": grow.out(0)}, title="Suavizar borde")

    # -------------------------------------------------------------- motor A
    with g.group("6 · MOTOR A · Qwen-Image-Edit 2511 (local, gratis)", PURPLE):
        qwen_out, _ = qwen_edit_engine(
            g,
            img_in.out(0),
            prompt.out(0),
            negativo.out(0),
            seed=815,
            image2=ref.out(0),
            steps_quality=20,
            cfg_quality=4.0,
            scale="none",
            noise_mask=m_soft.out(0),
            noise_mask_switch=es_retoque.out(0),
            differential=True,
        )

    # -------------------------------------------------------------- motor B
    with g.group("7 · MOTOR B · FLUX.2 [klein] 9B (local, gratis)", BLUE):
        note(
            g,
            "### FLUX.2 [klein]\n\n"
            "4 pasos, CFG 1. Muy bueno en luz y materiales. Trabaja **sólo con el producto y el texto**: "
            "no usa ni la referencia de escena ni la máscara.\n\n"
            "Para VRAM baja cambia en los cargadores `flux-2-klein-9b-fp8` → `flux-2-klein-4b-fp8` y "
            "`qwen_3_8b_fp8mixed` → `qwen_3_4b`.",
            title="Notas FLUX.2",
        )
        flux_out = flux2_klein_engine(g, img_in.out(0), prompt.out(0), seed=815, steps=4)

    # -------------------------------------------------------------- motor C
    with g.group("8 · MOTOR C · GPT Image 2.5 (API de OpenAI · DE PAGO)", RED):
        note(
            g,
            "### GPT Image 2.5\n\n"
            "Nodo de API: la imagen del cliente **sale de tu máquina** hacia OpenAI y cada ejecución "
            "consume saldo. Sólo se ejecuta si eliges `gpt_image_api` en el desplegable MOTOR.\n\n"
            "**Ajustes que mueven el precio**: `model.quality` y `model.size`. Referencia por imagen "
            "con gpt-image-2.5: `low` 1024² ≈ 0,008 $ · `medium` ≈ 0,019 $ · `high` ≈ 0,075 $ · "
            "`max` 2048² ≈ 0,61 $.\n\n"
            "**`model.background: transparent`** te devuelve el PNG recortado directamente, sin pasar "
            "por BiRefNet.\n\n"
            "Si el producto lleva una marca reconocible, el modelo puede negarse a editarlo: es una "
            "limitación de la API que los motores locales no tienen.",
            title="Aviso: esto cuesta dinero",
        )
        gpt = g.add(
            "OpenAIGPTImageNodeV2",
            ["", "gpt-image-2.5-flare", "auto", 1024, 1024, "auto", "high", 1, 0, "randomize"],
            {
                "model.images.image_1": img_in.out(0),
                "model.images.image_2": ref.out(0),
                "prompt": prompt.out(0),
            },
            title="GPT Image 2.5",
            color="#653",
            named={
                "prompt": "",
                "model": "gpt-image-2.5-flare",
                "model.size": "auto",
                "model.custom_width": 1024,
                "model.custom_height": 1024,
                "model.background": "auto",
                "model.quality": "high",
                "n": 1,
                "seed": 0,
                "control_after_generate": "randomize",
            },
        )

    # ------------------------------------------------------ selección + retoque
    with g.group("9 · SALIDA DEL MOTOR Y REINTEGRACIÓN DEL RETOQUE", GREY):
        sw1 = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": qwen_out, "on_true": flux_out, "switch": usar_flux.out(0)},
            title="Qwen / FLUX.2",
        )
        sw2 = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": sw1.out(0), "on_true": gpt.out(0), "switch": usar_gpt.out(0)},
            title="… / GPT Image",
        )
        comp_ret = g.add(
            "ImageCompositeMasked",
            [0, 0, True],
            {"destination": img_in.out(0), "source": sw2.out(0), "mask": m_soft.out(0)},
            title="Pegar sólo la zona marcada",
        )
        salida = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": sw2.out(0), "on_true": comp_ret.out(0), "switch": es_retoque.out(0)},
            title="Imagen generada",
        )
        g.add("PreviewImage", [], {"images": salida.out(0)}, title="Previsualizar")

    # ----------------------------------------------------- recorte automático
    with g.group("10 · RECORTE + FONDO PURO  (automático si el tipo es packshot)", ORANGE):
        note(
            g,
            "### Recorte y fondo garantizado\n\n"
            "Se activa solo cuando el **TIPO DE FOTO** contiene `packshot`. El modelo deja un fondo "
            "*casi* blanco; los marketplaces suelen exigir **255,255,255 exacto**, así que BiRefNet "
            "recorta el producto y lo pega sobre un blanco puro generado, con una sombra de contacto "
            "sintética debajo.\n\n"
            "**Ajustes**\n"
            "- `Erosionar borde` `-2` quita el halo del recorte; `-4` si aún se ve borde claro.\n"
            "- `color` del fondo: `16777215` = blanco, `15790320` = #F0F0F0.\n"
            "- Sombra: `blend_factor` del nodo *Sombra de contacto*; `0` la quita.\n\n"
            "**Guardar el PNG transparente**: el nodo *GUARDAR PNG alpha* está silenciado para no "
            "escribir archivos inútiles cuando haces lifestyle. Selecciónalo y pulsa **Ctrl+M** para "
            "activarlo (igual que el de *Comprobar máscara*).\n\n"
            "> Si la máscara sale al revés, borra el nodo `InvertMask`: la convención depende del "
            "modelo de segmentación que cargues.",
            title="Recorte",
        )
        alpha = cutout_block(g, salida.out(0), erode=-2, feather=3, preview=False)
        size = g.add("GetImageSize", [], {"image": salida.out(0)})
        bg = g.add(
            "EmptyImage",
            [1024, 1024, 1, 16777215],
            {"width": size.out(0), "height": size.out(1)},
            title="Fondo blanco puro",
        )
        mask_img = g.add("MaskToImage", [], {"mask": alpha})
        mask_inv = g.add("ImageInvert", [], {"image": mask_img.out(0)})
        shadow = g.add("ImageBlur", [31, 10.0], {"image": mask_inv.out(0)}, title="Desenfoque de sombra")
        bg_shadow = g.add(
            "ImageBlend",
            [0.22, "multiply"],
            {"image1": bg.out(0), "image2": shadow.out(0)},
            title="Sombra de contacto",
        )
        comp = g.add(
            "ImageCompositeMasked",
            [0, 0, False],
            {"destination": bg_shadow.out(0), "source": salida.out(0), "mask": alpha},
            title="Producto sobre fondo limpio",
        )
        rgba = g.add("JoinImageWithAlpha", [], {"image": salida.out(0), "alpha": alpha}, title="RGBA")
        g.add(
            "SaveImage",
            ["estudio/recorte_transparente"],
            {"images": rgba.out(0)},
            title="GUARDAR PNG alpha  (Ctrl+M para activar)",
            mode=MODE_NEVER,
        )
        final_img = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": salida.out(0), "on_true": comp.out(0), "switch": es_packshot.out(0)},
            title="Imagen final",
        )

    # ------------------------------------------------------------- alta resolución
    with g.group("11 · ALTA RESOLUCIÓN Y ENTREGA", RED):
        note(
            g,
            "### Entrega\n\n"
            "Upscaler GAN 4x → reencuadre al lado largo → enfoque sutil.\n\n"
            "- Cambia `2048` por lo que pida la tienda (1600 / 2400 / 3000).\n"
            "- Si quieres que el reescalado **invente** micro-detalle real en vez de sólo interpolar, "
            "pasa la salida por `00_rescate_foto_cliente.json`.\n"
            "- Otros modelos: `4x-UltraSharp.safetensors`, `4x_NMKD-Siax_200k.pth`.",
            title="Entrega",
        )
        final = gan_finish(g, final_img.out(0), "estudio/final", largest=2048)
        g.add("ImageCompare", [], {"image_a": prod.out(0), "image_b": final}, title="Original / final")

    g.save(os.path.join(OUT, "10_estudio_producto.json"))


def main():
    os.makedirs(OUT, exist_ok=True)
    build_rescue()
    build_packshot()
    build_lifestyle()
    build_retouch()
    build_estudio()
    for f in sorted(os.listdir(OUT)):
        print("escrito:", os.path.join("workflows", f))


if __name__ == "__main__":
    main()
