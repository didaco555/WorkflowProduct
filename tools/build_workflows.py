#!/usr/bin/env python3
"""Genera los workflows .json de ComfyUI: fotografía de producto y vídeo tour inmobiliario.

    python3 tools/build_workflows.py

Escribe en `workflows/`. Editar aquí y regenerar es más seguro que tocar el JSON a mano.
"""

from __future__ import annotations

import json
import os
import sys
from collections import namedtuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from comfy_graph import MODE_BYPASS, MODE_NEVER, Graph  # noqa: E402

# Lo que devuelve `qwen_edit_engine`: la imagen editada, la entrada ya normalizada y los
# cargadores, para poder colgar más ramas del mismo modelo sin duplicarlo.
Engine = namedtuple("Engine", "image fitted clip vae model steps cfg")

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

# Vídeo: Wan 2.2 14B imagen-a-vídeo (dos expertos: ruido alto + ruido bajo) y su LoRA de 4 pasos
WAN_HIGH = "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
WAN_LOW = "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
WAN_LORA_HIGH = "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors"
WAN_LORA_LOW = "wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors"
WAN_CLIP = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
WAN_VAE = "wan_2.1_vae.safetensors"
FILM_INTERP = "film_net_fp16.safetensors"
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
    turbo_switch=None,
):
    """Motor Qwen-Image-Edit 2511 con conmutador TURBO (LoRA Lightning, 4 pasos) / CALIDAD.

    Devuelve un `Engine` (imagen, entrada normalizada, clip, vae, modelo).
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

    if turbo_switch is None:
        turbo_switch = g.add(
            "PrimitiveBoolean", [False], title="⚡ TURBO  (false = CALIDAD)", color=ORANGE
        ).out(0)
    sw_model = g.add(
        "ComfySwitchNode",
        [False],
        {"on_false": model_port, "on_true": lora.out(0), "switch": turbo_switch},
        title="Modelo: calidad / turbo",
    )
    steps_q = g.add("PrimitiveInt", [steps_quality, "fixed"], title="Pasos (calidad)")
    steps_t = g.add("PrimitiveInt", [4, "fixed"], title="Pasos (turbo)")
    cfg_q = g.add("PrimitiveFloat", [cfg_quality], title="CFG (calidad)")
    cfg_t = g.add("PrimitiveFloat", [1.0], title="CFG (turbo)")
    sw_steps = g.add(
        "ComfySwitchNode",
        [False],
        {"on_false": steps_q.out(0), "on_true": steps_t.out(0), "switch": turbo_switch},
        title="Pasos",
    )
    sw_cfg = g.add(
        "ComfySwitchNode",
        [False],
        {"on_false": cfg_q.out(0), "on_true": cfg_t.out(0), "switch": turbo_switch},
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
    return Engine(
        dec.out(0), fit_port, clip.out(0), vae.out(0), sw_model.out(0), sw_steps.out(0), sw_cfg.out(0)
    )


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
        packshot = qwen_edit_engine(
            g, sw_in.out(0), PACKSHOT_POS, PACKSHOT_NEG, seed=815, steps_quality=20, cfg_quality=4.0
        ).image
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
        motor_a = qwen_edit_engine(
            g,
            sw_in.out(0),
            LIFESTYLE_POS,
            LIFESTYLE_NEG,
            seed=2024,
            image2=ref.out(0),
            steps_quality=20,
            cfg_quality=4.0,
        )
        qwen_raw, qwen_fitted = motor_a.image, motor_a.fitted

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
        retoque = qwen_edit_engine(
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
        edited, fitted = retoque.image, retoque.fitted

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
# 10 · Estudio de producto — todo en uno, gratis, con selector de categoría
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
    "packshot_fondo_blanco": _packshot(
        "seamless pure white studio cyclorama (#FFFFFF), completely clean, no props, no text, no watermark.",
        "large softbox key light from the upper left, soft fill from the right, subtle rim light "
        "separating the edges from the background, no blown highlights, no colour cast.",
    ),
    "packshot_fondo_gris_degradado": _packshot(
        "light grey seamless gradient background, brighter behind the product, darker towards the corners.",
        "large softbox key light from the upper left, soft fill from the right, rim light on the edges, "
        "smooth gradient falloff.",
    ),
    "packshot_fondo_color_pastel": _packshot(
        "seamless solid pastel sand background (#E8DCC8), completely uniform, no texture, no props.",
        "soft frontal key light with a gentle gradient, low contrast, editorial catalogue look.",
    ),
    "packshot_superficie_reflejo": _packshot(
        "product standing on a glossy white acrylic surface with a soft mirror reflection below it, "
        "seamless white backdrop behind.",
        "two large strip softboxes at both sides creating clean vertical highlights, soft overhead fill.",
    ),
    "packshot_detalle_macro": (
        "Turn this into a macro detail shot of the product on a seamless pure white background.\n\n"
        "Framing: move in close on the most characteristic part of the product (cap, texture, seam, "
        "label edge), the product fills the frame.\n"
        "Lighting: raking side light that reveals the surface texture, soft fill on the opposite side.\n"
        "Depth: very shallow depth of field, the focus point tack sharp, smooth falloff behind.\n" + PACK_TAIL
    ),
    "lifestyle_bano_marmol": _lifestyle(
        "a bright modern bathroom, white marble countertop with subtle grey veining, soft morning light "
        "through a window on the left, a folded linen towel and a small eucalyptus branch blurred behind."
    ),
    "lifestyle_cocina_nordica": _lifestyle(
        "a light oak kitchen counter, matte white tiles behind, diffused daylight from a large window on "
        "the right, fresh ingredients scattered and blurred in the background."
    ),
    "lifestyle_mesa_terraza": _lifestyle(
        "a wooden terrace table at golden hour, warm low sun from behind creating long soft shadows, "
        "blurred mediterranean garden and sea in the background, empty glasses out of focus."
    ),
    "lifestyle_escritorio_madera": _lifestyle(
        "a walnut desk with a linen notebook and a matte black pen slightly out of focus, warm lamp "
        "light from the upper right mixed with cool window light from the left."
    ),
    "lifestyle_mesita_noche": _lifestyle(
        "a dark wooden nightstand at night, warm candlelight from the left as the only light source, "
        "deep shadows, cosy and intimate atmosphere."
    ),
    "lifestyle_hormigon_minimal": _lifestyle(
        "a raw polished concrete surface, cool overcast daylight from above, deep neutral grey "
        "background, minimal styling, a single hard-edged soft shadow."
    ),
    "lifestyle_exterior_natural": _lifestyle(
        "a flat mossy rock in a forest clearing, dappled sunlight filtering through leaves, soft green "
        "bokeh in the background."
    ),
    "lifestyle_con_foto_referencia": (
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

VISTA_BASE = (
    "Keep the exact same product: same shape, proportions, materials, colours, logo and label text.\n"
    "Keep the same background, the same lighting setup and the same framing and scale.\n"
    "Only the camera angle changes.\n\n"
)
VISTAS = [
    VISTA_BASE + "Rotate the product to a three-quarter view seen from the left, about 35 degrees.",
    VISTA_BASE + "Rotate the product to a three-quarter view seen from the right, about 35 degrees.",
    VISTA_BASE + "Move the camera above the product for a top-down flat-lay view, looking straight down.",
]


def combo(g: Graph, options: list[str], default: str, *, title: str, color: str = ORANGE):
    """Desplegable con opciones escritas por el usuario (nodo `CustomCombo` del núcleo)."""
    values = [default, options.index(default), *options, ""]
    return g.add("CustomCombo", values, title=title, color=color)


def build_estudio():
    g = Graph("10-estudio")

    # ------------------------------------------------------------ panel de control
    with g.group("PANEL DE CONTROL · lo único que tocas", ORANGE):
        note(
            g,
            "# Estudio de producto — todo en uno\n\n"
            "Subes la foto, **eliges la categoría** y ejecutas. Sin costes: todo corre en tu GPU.\n\n"
            "## Los tres mandos\n"
            "| Mando | Qué hace |\n"
            "|---|---|\n"
            "| **▼ CATEGORÍA DE FOTO** | Elige qué foto quieres. Es el mando principal. |\n"
            "| **⚡ TURBO** | `true` = 4 pasos (rápido, para probar). `false` = 20 pasos (toma final). |\n"
            "| **RESCATE** | `true` si la foto del cliente viene mala (móvil, ruido, JPEG, borrosa). |\n\n"
            "Lo demás se configura solo a partir de la categoría:\n"
            "- Categoría que empieza por `packshot` → recorta y pone fondo blanco puro.\n"
            "- Categoría `retoque_zona_marcada` → modo máscara, sólo se regenera lo que pintes.\n\n"
            "## Las 3 vistas del producto\n"
            "Abajo del todo hay un bloque que genera **tres ángulos** del producto ya mejorado. Viene "
            "apagado; para activarlo selecciona el nodo **GUARDAR 3 VISTAS** y pulsa **Ctrl+M**.\n\n"
            "## Los cargadores 2 y 3 se quedan en gris\n"
            "Es correcto: están en bypass para que no tengas que subirles nada. Sólo les quitas el "
            "bypass (Ctrl+B) si eliges `lifestyle_con_foto_referencia` o `retoque_zona_marcada`, y "
            "entonces les subes la foto.\n\n"
            "## Si no ves el desplegable de categoría\n"
            "El nodo `CustomCombo` es reciente: actualiza ComfyUI. Mientras tanto puedes borrar el enlace "
            "que va de **CATEGORÍA** a **PROMPT elegido** y escribir la categoría a mano en el campo "
            "`key` de ese nodo (p. ej. `lifestyle_bano_marmol`).",
            title="LÉEME PRIMERO",
        )
        categoria = combo(g, list(CATALOGO.keys()), "packshot_fondo_blanco", title="▼ CATEGORÍA DE FOTO")
        turbo = g.add("PrimitiveBoolean", [True], title="⚡ TURBO (false = calidad)", color=ORANGE)
        use_rescue = g.add("PrimitiveBoolean", [False], title="RESCATE de foto mala", color=ORANGE)

    # ---------------------------------------------------------------- entradas
    with g.group("ENTRADAS", BLUE):
        note(
            g,
            "### Qué subir\n\n"
            "**1 · PRODUCTO** es la única obligatoria: la foto que te manda el cliente, tal cual.\n\n"
            "Las otras dos vienen **en bypass** (en gris) a propósito: así no tienes que subirles nada "
            "y el grafo valida igual. **Déjalas en bypass** salvo que vayas a usarlas.\n\n"
            "| Cargador | Actívalo (Ctrl+B) sólo para… |\n"
            "|---|---|\n"
            "| **2 · REFERENCIA DE ESCENA** | la categoría `lifestyle_con_foto_referencia` |\n"
            "| **3 · IMAGEN A RETOCAR** | la categoría `retoque_zona_marcada` |\n\n"
            "Al quitarles el bypass te pedirán un archivo (traen puesto un nombre de ejemplo que no "
            "existe): pulsa **elige archivo para subir** y sube el tuyo. En el cargador 3, además, "
            "clic derecho sobre el nodo → *Open in MaskEditor*, pinta encima de lo que no te gusta y "
            "guarda.\n\n"
            "Cuando termines de retocar, vuelve a ponerlos en bypass y sigues con el flujo normal.",
            title="Entradas",
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

    # ---------------------------------------------------------------- catálogo
    with g.group("CATÁLOGO DE CATEGORÍAS", GREY):
        note(
            g,
            "### Cómo funciona la categoría\n\n"
            "El desplegable devuelve una clave; *Extract Text from JSON* saca ese prompt del catálogo y "
            "lo enchufa al motor. Nada más.\n\n"
            "## Añadir categorías tuyas\n"
            "1. Escribe una entrada nueva en el **CATÁLOGO**: `\"mi_categoria\": \"tu prompt\"`.\n"
            "2. Doble clic en el desplegable **CATEGORÍA** para añadir `mi_categoria` a la lista.\n\n"
            "Respeta el prefijo: `packshot…` activa el recorte sobre fondo puro y `retoque…` activa el "
            "modo máscara. Cualquier otro nombre se trata como escena lifestyle.\n\n"
            "El JSON tiene que ser válido (comillas dobles, sin coma final). Si te equivocas, el prompt "
            "sale vacío y la imagen no cambia: esa es la pista.\n\n"
            "Las plantillas largas y el porqué de cada línea están en `docs/PROMPTS.md`.",
            title="Ampliar el catálogo",
        )
        catalogo = g.add(
            "PrimitiveStringMultiline",
            [json.dumps(CATALOGO, ensure_ascii=False, indent=2)],
            title="CATÁLOGO de prompts (JSON)",
        )
        prompt = g.add(
            "JsonExtractString",
            ["", ""],
            {"json_string": catalogo.out(0), "key": categoria.out(0)},
            title="PROMPT elegido",
        )
        negativo = g.add("PrimitiveStringMultiline", [NEGATIVO_COMUN], title="PROMPT ❌ negativo (común)")
        es_packshot = g.add(
            "StringContains",
            ["", "packshot", True],
            {"string": categoria.out(0)},
            title="¿packshot? → recorte automático",
        )
        es_retoque = g.add(
            "StringContains",
            ["", "retoque", True],
            {"string": categoria.out(0)},
            title="¿retoque? → modo máscara",
        )

    # ---------------------------------------------------------------- rescate
    with g.group("RESCATE de foto mala (SeedVR2) · sólo si RESCATE = true", GREEN):
        note(
            g,
            "### Rescate\n\n"
            "SeedVR2 reconstruye detalle real (no es un upscaler que interpola): aguanta fotos de móvil, "
            "con ruido, poca luz o compresión JPEG visible.\n\n"
            "Con `RESCATE = false` no se carga: cero VRAM y cero tiempo.\n\n"
            "Sube el *pre-escalado* a 3x o 4x si la foto es diminuta; bájalo si te quedas sin memoria.",
            title="Rescate",
        )
        base = g.add("ImageScaleToTotalPixels", ["lanczos", 1.0, 16], {"image": prod.out(0)}, title="Normalizar a 1 MP")
        rescued = seedvr2_rescue(g, base.out(0), scale=2.0)
        rescued_fit = g.add("ImageScaleToTotalPixels", ["lanczos", 1.0, 16], {"image": rescued}, title="Volver a 1 MP")
        img_gen = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": base.out(0), "on_true": rescued_fit.out(0), "switch": use_rescue.out(0)},
            title="Producto listo",
        )

    # -------------------------------------------------------- entrada efectiva
    with g.group("PREPARAR ENTRADA Y MÁSCARA", BLUE):
        src = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": img_gen.out(0), "on_true": ret.out(0), "switch": es_retoque.out(0)},
            title="Imagen de partida (producto / imagen a retocar)",
        )
        img_in = g.add(
            "ImageScaleToTotalPixels", ["lanczos", 1.0, 16], {"image": src.out(0)}, title="1 MP proporcional"
        )
        # El cargador 3 vive en bypass, así que su salida MASK no existe hasta que lo actives, y
        # `GrowMask` exige una máscara sí o sí. Las entradas del conmutador son opcionales, de modo
        # que el grafo valida igual; la máscara del producto (vacía si el archivo no lleva alfa)
        # hace de relleno inofensivo mientras no estés retocando.
        mask_src = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": prod.out(1), "on_true": ret.out(1), "switch": es_retoque.out(0)},
            title="Máscara (vacía / la que pintaste)",
        )
        grow = g.add("GrowMask", [16, True], {"mask": mask_src.out(0)}, title="Ampliar selección")
        m_soft = g.add("FeatherMask", [24] * 4, {"mask": grow.out(0)}, title="Suavizar borde")
        note(
            g,
            "### Por qué 1 MP proporcional\n\n"
            "Es la resolución de trabajo del modelo de edición, y al conservar la proporción la máscara "
            "que pintaste en el MaskEditor sigue cuadrando píxel a píxel con la imagen.\n\n"
            "La selección se amplía 16 px y se suaviza 24 px para que el empalme del retoque no se note. "
            "Si se ve el parche, sube ambos valores.\n\n"
            "Mientras la categoría no sea `retoque_zona_marcada`, la máscara no se usa para nada: el "
            "conmutador coge la del producto (vacía) para que el grafo valide con el cargador 3 en "
            "bypass.",
            title="Entrada y máscara",
        )

    # -------------------------------------------------------------- motor
    with g.group("MOTOR · Qwen-Image-Edit 2511 (local, gratis)", PURPLE):
        note(
            g,
            "### El motor\n\n"
            "Qwen-Image-Edit 2511 es el modelo libre que mejor conserva **logotipos y texto de etiqueta**, "
            "que es justo lo que se rompe en fotografía de producto.\n\n"
            "**⚡ TURBO** conmuta entre el LoRA Lightning (4 pasos, CFG 1) y la calidad completa "
            "(20 pasos, CFG 4). Encuadra el prompt en turbo y lanza la final en calidad.\n\n"
            "Si quieres probar **FLUX.2 [klein]** como motor alternativo, está montado en "
            "`02_lifestyle_escena.json`.",
            title="Motor",
        )
        motor = qwen_edit_engine(
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
            turbo_switch=turbo.out(0),
        )
        salida_motor = motor.image

    # ------------------------------------------------------ reintegrar retoque
    with g.group("REINTEGRAR EL RETOQUE (automático)", GREY):
        comp_ret = g.add(
            "ImageCompositeMasked",
            [0, 0, True],
            {"destination": img_in.out(0), "source": salida_motor, "mask": m_soft.out(0)},
            title="Pegar sólo la zona marcada",
        )
        salida = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": salida_motor, "on_true": comp_ret.out(0), "switch": es_retoque.out(0)},
            title="Imagen generada",
        )
        g.add("PreviewImage", [], {"images": salida.out(0)}, title="Previsualizar")

    # ----------------------------------------------------- recorte automático
    with g.group("RECORTE + FONDO PURO · automático si la categoría es packshot", ORANGE):
        note(
            g,
            "### Recorte y fondo garantizado\n\n"
            "El modelo deja un fondo *casi* blanco; los marketplaces suelen exigir **255,255,255 "
            "exacto**. BiRefNet recorta el producto y lo pega sobre un blanco puro generado, con una "
            "sombra de contacto sintética debajo.\n\n"
            "**Ajustes**\n"
            "- `Erosionar borde` `-2` quita el halo; `-4` si aún se ve borde claro.\n"
            "- `color` del fondo: `16777215` = blanco, `15790320` = #F0F0F0.\n"
            "- Sombra: `blend_factor` del nodo *Sombra de contacto*; `0` la quita.\n\n"
            "**PNG transparente**: el nodo *GUARDAR PNG alpha* está silenciado para no escribir archivos "
            "inútiles cuando haces lifestyle. Selecciónalo y pulsa **Ctrl+M** para activarlo.\n\n"
            "> Si la máscara sale al revés, borra el nodo `InvertMask`: la convención depende del modelo "
            "de segmentación que cargues.",
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
        master = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": salida.out(0), "on_true": comp.out(0), "switch": es_packshot.out(0)},
            title="MASTER (foto buena a 1 MP)",
        )

    # ------------------------------------------------------------- entrega
    with g.group("ENTREGA EN ALTA RESOLUCIÓN", RED):
        note(
            g,
            "### Entrega\n\n"
            "Upscaler GAN 4x → reencuadre al lado largo → enfoque sutil. Cambia `2048` por lo que pida "
            "la tienda (1600 / 2400 / 3000).\n\n"
            "Otros modelos que puedes dejar en `models/upscale_models/`: `4x-UltraSharp.safetensors`, "
            "`4x_NMKD-Siax_200k.pth`.",
            title="Entrega",
        )
        up_model = g.add("UpscaleModelLoader", [GAN_UPSCALER], title="Upscaler GAN 4x")
        up = g.add("ImageUpscaleWithModel", [], {"upscale_model": up_model.out(0), "image": master.out(0)})
        fit = g.add("ImageScaleToMaxDimension", ["lanczos", 2048], {"image": up.out(0)}, title="Lado largo 2048 px")
        sharp = g.add("ImageSharpen", [1, 0.8, 0.28], {"image": fit.out(0)}, title="Enfoque final (sutil)")
        g.add("SaveImage", ["estudio/final"], {"images": sharp.out(0)}, title="GUARDAR final")
        g.add("ImageCompare", [], {"image_a": prod.out(0), "image_b": sharp.out(0)}, title="Original / final")

    # --------------------------------------------------------------- 3 vistas
    with g.group("3 VISTAS DEL PRODUCTO · apagado · Ctrl+M en GUARDAR 3 VISTAS", PURPLE):
        note(
            g,
            "# Tres ángulos del mismo producto\n\n"
            "Parte del **MASTER**, es decir de la foto ya rescatada, reiluminada y recortada, y genera "
            "tres vistas nuevas con el mismo fondo y la misma luz. Se guardan juntas en "
            "`output/estudio/vistas/`.\n\n"
            "## Cómo se enciende\n"
            "Selecciona el nodo **GUARDAR 3 VISTAS** y pulsa **Ctrl+M**. Mientras esté silenciado, todo "
            "este bloque no se ejecuta y no te cuesta ni un segundo.\n\n"
            "## Qué ángulos salen\n"
            "1. Tres cuartos desde la izquierda.\n"
            "2. Tres cuartos desde la derecha.\n"
            "3. Cenital (flat lay, desde arriba).\n\n"
            "Cada uno es un cuadro de texto editable: cambia el que quieras por *back view*, "
            "*low angle hero shot*, *45 degrees from above*, lo que necesites.\n\n"
            "## Lo que tienes que saber antes de usarlas\n"
            "El modelo **no conoce las caras del producto que no se ven** en la foto original: las "
            "inventa. En un bote cilíndrico o una caja sencilla el resultado suele colar; en la parte "
            "trasera de una etiqueta con texto, casi nunca. Por eso los tres ángulos por defecto son "
            "giros suaves (±35°) y un cenital, que es lo que menos se inventa.\n\n"
            "Revisa siempre las tres antes de subirlas a la ficha, y si una falla cámbiale el ángulo o "
            "corrígela con la categoría `retoque_zona_marcada`.",
            title="LÉEME antes de activarlo",
        )
        vsrc = g.add(
            "ImageScaleToTotalPixels", ["lanczos", 1.0, 16], {"image": master.out(0)}, title="MASTER a 1 MP"
        )
        vclip, vvae, vmodel = motor.clip, motor.vae, motor.model
        vlat = g.add("VAEEncode", [], {"pixels": vsrc.out(0), "vae": vvae})
        vneg = g.add(
            "TextEncodeQwenImageEditPlus",
            [NEGATIVO_COMUN],
            {"clip": vclip, "vae": vvae, "image1": vsrc.out(0)},
            title="Negativo (vistas)",
        )
        decoded = []
        for i, texto in enumerate(VISTAS, start=1):
            vpos = g.add(
                "TextEncodeQwenImageEditPlus",
                [texto],
                {"clip": vclip, "vae": vvae, "image1": vsrc.out(0)},
                title=f"VISTA {i}",
            )
            vks = g.add(
                "KSampler",
                [1000 + i, "fixed", 20, 4.0, "euler", "simple", 1.0],
                {
                    "model": vmodel,
                    "positive": vpos.out(0),
                    "negative": vneg.out(0),
                    "latent_image": vlat.out(0),
                    # mismos pasos y CFG que el motor principal: el interruptor ⚡ TURBO
                    # también manda aquí
                    "steps": motor.steps,
                    "cfg": motor.cfg,
                },
                title=f"KSampler vista {i}",
            )
            decoded.append(g.add("VAEDecode", [], {"samples": vks.out(0), "vae": vvae}).out(0))
        lote = g.add(
            "BatchImagesNode",
            [],
            {"images.image0": decoded[0], "images.image1": decoded[1], "images.image2": decoded[2]},
            title="Las 3 juntas",
        )
        vup = g.add("ImageUpscaleWithModel", [], {"upscale_model": up_model.out(0), "image": lote.out(0)})
        vfit = g.add("ImageScaleToMaxDimension", ["lanczos", 2048], {"image": vup.out(0)}, title="Lado largo 2048 px")
        g.add(
            "SaveImage",
            ["estudio/vistas/vista"],
            {"images": vfit.out(0)},
            title="GUARDAR 3 VISTAS  (Ctrl+M para activar)",
            mode=MODE_NEVER,
        )

    g.save(os.path.join(OUT, "10_estudio_producto.json"))


# ======================================================================================
# Vídeo tour inmobiliario (Wan 2.2 14B + SeedVR2 + FILM)
# ======================================================================================
# Lo que se repite en todos los movimientos: fidelidad al espacio y cámara de gimbal.
TOUR_BASE = (
    "Real estate video tour of this exact space. Keep the room exactly as in the image: same walls, floor, "
    "ceiling, windows, doors, furniture, decoration and layout. Nothing appears, disappears or changes shape. "
    "Smooth, steady, slow camera movement like a professional gimbal shot, constant speed, no shake. "
    "Natural light, photorealistic, sharp details, straight vertical lines, professional architectural videography."
)

# Clave = lo que ves en el desplegable. Valor = la frase de movimiento (en inglés: Wan la sigue mejor).
MOVIMIENTOS = {
    "avance_lento": "The camera slowly dollies forward into the room, gently getting closer to the centre of the space.",
    "retroceso_revelado": "The camera slowly pulls back, gradually revealing more of the room.",
    "paneo_a_izquierda": "The camera slowly pans from right to left across the room, keeping the horizon perfectly level.",
    "paneo_a_derecha": "The camera slowly pans from left to right across the room, keeping the horizon perfectly level.",
    "travelling_lateral_izquierda": (
        "The camera slides sideways to the left at a constant height, creating gentle parallax between the "
        "furniture in the foreground and the background."
    ),
    "travelling_lateral_derecha": (
        "The camera slides sideways to the right at a constant height, creating gentle parallax between the "
        "furniture in the foreground and the background."
    ),
    "orbita_suave": "The camera makes a slow, subtle arc around the centre of the room, with gentle parallax.",
    "subida_vertical": "The camera slowly rises vertically, showing the room from a slightly higher point of view.",
    "fijo_con_vida": (
        "Static camera, the framing does not change. Only subtle natural movement: sheer curtains moving gently "
        "in the breeze and soft sunlight shifting slightly."
    ),
    "exterior_avance": (
        "Slow, smooth camera move forward towards the building, steady like a drone shot, the architecture "
        "and surroundings stay exactly as in the image."
    ),
    "transicion_foto_a_foto": (
        "The camera moves smoothly and continuously from the first view to the final view of the same space, "
        "like walking slowly through the room with a gimbal."
    ),
}
CATALOGO_MOVIMIENTOS = {k: v + " " + TOUR_BASE for k, v in MOVIMIENTOS.items()}

# El negativo oficial de Wan (en chino, es el que mejor funciona) + lo que estropea un tour inmobiliario.
TOUR_NEG = (
    "色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，"
    "丑陋的，残缺的，畸形的，杂乱的背景，背景人很多，倒着走\n"
    "warped walls, bent straight lines, morphing furniture, objects appearing or disappearing, changing room layout, "
    "duplicated windows, extra doors, people, animals, text, watermark, logo, fast motion, camera shake, jitter, "
    "flicker, fisheye distortion, blurry, low quality"
)


def seedvr2_video_upscale(g: Graph, frames_port, *, scale: float = 1.5):
    """SeedVR2 3B en modo vídeo: reescala todos los frames a la vez, troceando en el tiempo si no cabe."""
    up = g.add("ImageScaleBy", ["lanczos", scale], {"image": frames_port}, title="Escala (1.5 = 720p → 1080p)")
    pre = g.add("SeedVR2Preprocess", [], {"resized_images": up.out(0)})
    vae = g.add("VAELoader", [SEEDVR2_VAE], title="VAE · SeedVR2")
    unet = g.add("UNETLoader", [SEEDVR2_UNET, "default"], title="Modelo · SeedVR2 3B")
    enc = g.add("VAEEncodeTiled", [512, 128, 64, 8], {"pixels": pre.out(0), "vae": vae.out(0)})
    chunk = g.add(
        "SeedVR2TemporalChunk",
        [0, "auto"],
        {"latent": enc.out(0)},
        title="Trocear en el tiempo (auto = según tu VRAM)",
    )
    cond = g.add("SeedVR2Conditioning", [], {"model": unet.out(0), "vae_conditioning": chunk.out(0)})
    ks = g.add(
        "KSampler",
        [0, "fixed", 1, 1.0, "euler", "simple", 1.0],
        {
            "model": unet.out(0),
            "positive": cond.out(0),
            "negative": cond.out(1),
            "latent_image": chunk.out(0),
        },
        title="SeedVR2 · 1 paso",
    )
    merge = g.add(
        "SeedVR2TemporalMerge", [], {"latents": ks.out(0), "temporal_overlap": chunk.out(1)}, title="Unir trozos"
    )
    dec = g.add("VAEDecodeTiled", [512, 128, 64, 8], {"samples": merge.out(0), "vae": vae.out(0)})
    post = g.add(
        "SeedVR2PostProcessing",
        ["lab"],
        {"images": dec.out(0), "original_resized_images": up.out(0)},
        title="Corrección de color (fiel al original)",
    )
    return post.out(0)


def build_video_tour():
    g = Graph("20-video-tour")

    # ------------------------------------------------------------ panel de control
    with g.group("PANEL DE CONTROL · lo único que tocas", ORANGE):
        note(
            g,
            "# Vídeo tour inmobiliario — un plano por ejecución\n\n"
            "Cada ejecución genera **un plano de ~5 s** a partir de **una foto real** del piso. "
            "Haces un plano por foto y los montas en CapCut/DaVinci con música. Todo corre en tu GPU.\n\n"
            "## Tres formas de usarlo\n"
            "| Quieres… | Cómo |\n"
            "|---|---|\n"
            "| **Animar una foto** (lo normal) | Sube la foto en **1 · INICIO** y ejecuta. |\n"
            "| **Ir de una foto a otra del mismo espacio** | Activa **2 · FINAL** (Ctrl+B), sube la segunda "
            "foto y elige `transicion_foto_a_foto`. |\n"
            "| **Alargar un plano** (seguir el movimiento) | Sube en **1 · INICIO** el PNG de "
            "`output/tour/ultimo_frame_…` del plano anterior y repite el mismo movimiento. |\n\n"
            "## Los mandos\n"
            "| Mando | Qué hace |\n"
            "|---|---|\n"
            "| **▼ MOVIMIENTO DE CÁMARA** | El movimiento del plano. Es el mando principal. |\n"
            "| **ESTANCIA** | Una línea describiendo lo que se ve (opcional, ayuda a no inventar). |\n"
            "| **⚡ TURBO** | `true` = 4 pasos (~4-5x más rápido). `false` = 20 pasos. |\n"
            "| **ANCHO / ALTO** | 1280×720 horizontal · 720×1280 vertical · 832×480 si vas justo de VRAM. |\n"
            "| **FRAMES** | 81 = 5 s (a 16 fps). Siempre 4n+1: 49 = 3 s, 65 = 4 s, 81 = 5 s. |\n"
            "| **1080p (SeedVR2)** | Reescala el plano a 1920×1080 con el SeedVR2 que ya tienes. |\n"
            "| **32 fps (FILM)** | Dobla los frames para que los movimientos lentos no vayan a saltos. |\n\n"
            "## Regla de oro\n"
            "**Nunca encadenes habitaciones distintas.** Si le pides ir del salón al baño, la IA se inventa "
            "el pasillo. Salta de estancia con un corte en el montaje, como hace un videógrafo de verdad.\n\n"
            "Salidas en `output/tour/`: el vídeo (`plano_…mp4`) y su último frame (`ultimo_frame_…png`).",
            title="LÉEME PRIMERO",
        )
        movimiento = combo(g, list(CATALOGO_MOVIMIENTOS.keys()), "avance_lento", title="▼ MOVIMIENTO DE CÁMARA")
        estancia = g.add(
            "PrimitiveStringMultiline",
            ["Bright living room with a grey sofa, a wooden coffee table and a large window."],
            title="ESTANCIA (qué se ve, en inglés)",
            color=ORANGE,
        )
        turbo = g.add("PrimitiveBoolean", [True], title="⚡ TURBO (false = calidad)", color=ORANGE)
        ancho = g.add("PrimitiveInt", [1280, "fixed"], title="ANCHO", color=ORANGE)
        alto = g.add("PrimitiveInt", [720, "fixed"], title="ALTO", color=ORANGE)
        frames = g.add("PrimitiveInt", [81, "fixed"], title="FRAMES (81 = 5 s)", color=ORANGE)
        semilla = g.add("PrimitiveInt", [1, "randomize"], title="SEMILLA (fija = repetir plano)", color=ORANGE)
        hd = g.add("PrimitiveBoolean", [False], title="1080p con SeedVR2", color=ORANGE)
        fluido = g.add("PrimitiveBoolean", [True], title="32 fps con FILM", color=ORANGE)

    # ---------------------------------------------------------------- entradas
    with g.group("ENTRADAS", BLUE):
        note(
            g,
            "### Qué subir\n\n"
            "**1 · INICIO** es obligatoria: una foto del piso **o** el `ultimo_frame` del plano anterior "
            "(está en `ComfyUI/output/tour/`; súbelo con *choose file to upload* o arrástralo encima).\n\n"
            "**2 · FINAL** viene **en bypass** (en gris): así el plano es libre y sólo parte de la foto de "
            "inicio. Actívala con **Ctrl+B** cuando quieras que el plano **termine exactamente** en otra foto "
            "real: dos ángulos del mismo salón, la puerta de la terraza y la terraza…\n\n"
            "La foto se recorta al centro para llenar ANCHO×ALTO. Para vertical desde fotos horizontales "
            "se pierde mucho de los lados: mejor genera en horizontal y recorta el reel en el montaje.",
            title="Entradas",
        )
        inicio = g.add("LoadImage", ["foto_inicio.png", "image"], title="1 · INICIO (foto o último frame)")
        final = g.add(
            "LoadImage",
            ["foto_final.png", "image"],
            title="2 · FINAL (opcional · Ctrl+B)",
            mode=MODE_BYPASS,
        )

    # ---------------------------------------------------------------- catálogo
    with g.group("CATÁLOGO DE MOVIMIENTOS", GREY):
        note(
            g,
            "### Cómo sale el prompt\n\n"
            "`ESTANCIA` + el movimiento elegido + una base común que obliga a conservar el espacio "
            "(mismas paredes, muebles y ventanas; nada aparece ni desaparece; cámara de gimbal).\n\n"
            "## Añadir movimientos\n"
            "1. Escribe una entrada nueva en el **CATÁLOGO**: `\"mi_movimiento\": \"frase en inglés\"`.\n"
            "2. Doble clic en el desplegable para añadir `mi_movimiento` a la lista.\n\n"
            "Las entradas del catálogo ya llevan la base de fidelidad al final; cópiala en las tuyas.\n\n"
            "Con **TURBO** el CFG es 1 y el negativo no se usa; sólo cuenta en modo calidad.",
            title="Ampliar el catálogo",
        )
        catalogo = g.add(
            "PrimitiveStringMultiline",
            [json.dumps(CATALOGO_MOVIMIENTOS, ensure_ascii=False, indent=2)],
            title="CATÁLOGO de movimientos (JSON)",
        )
        mov_txt = g.add(
            "JsonExtractString",
            ["", ""],
            {"json_string": catalogo.out(0), "key": movimiento.out(0)},
            title="Movimiento elegido",
        )
        prompt = g.add(
            "StringConcatenate",
            ["", "", "\n\n"],
            {"string_a": estancia.out(0), "string_b": mov_txt.out(0)},
            title="PROMPT ✅ final",
        )
        negativo = g.add("PrimitiveStringMultiline", [TOUR_NEG], title="PROMPT ❌ negativo")

    # ---------------------------------------------------------------- motor
    with g.group("MOTOR · Wan 2.2 14B imagen-a-vídeo (ruido alto → ruido bajo)", PURPLE):
        note(
            g,
            "### Cómo funciona Wan 2.2\n\n"
            "Son **dos modelos** que se pasan el testigo: el de *ruido alto* decide el movimiento y la "
            "composición en los primeros pasos, y el de *ruido bajo* pone el detalle en los últimos.\n\n"
            "| | Pasos | CFG | Cambio de modelo |\n"
            "|---|---|---|---|\n"
            "| ⚡ TURBO (LoRA lightx2v) | 4 | 1 | en el paso 2 |\n"
            "| Calidad | 20 | 3.5 | en el paso 10 |\n\n"
            "Encuadra en turbo; pasa a calidad sólo si el turbo te deja el movimiento raro.\n\n"
            "**Sin memoria suficiente:** baja a 832×480 y activa *1080p con SeedVR2* al final.",
            title="Motor",
        )
        clip = g.add("CLIPLoader", [WAN_CLIP, "wan", "default"], title="Text encoder · umt5-xxl")
        vae = g.add("VAELoader", [WAN_VAE], title="VAE · Wan 2.1")
        pos = g.add("CLIPTextEncode", [""], {"clip": clip.out(0), "text": prompt.out(0)}, title="PROMPT ✅")
        neg = g.add("CLIPTextEncode", [""], {"clip": clip.out(0), "text": negativo.out(0)}, title="PROMPT ❌")
        cond = g.add(
            "WanFirstLastFrameToVideo",
            [1280, 720, 81, 1],
            {
                "positive": pos.out(0),
                "negative": neg.out(0),
                "vae": vae.out(0),
                "start_image": inicio.out(0),
                "end_image": final.out(0),
                "width": ancho.out(0),
                "height": alto.out(0),
                "length": frames.out(0),
            },
            title="Wan · foto inicio (+ foto final)",
        )

        def expert(unet_name: str, lora_name: str, label: str):
            unet = g.add("UNETLoader", [unet_name, "default"], title=f"Modelo · Wan 2.2 14B {label}")
            shift = g.add("ModelSamplingSD3", [5.0], {"model": unet.out(0)}, title=f"Shift 5 · {label}")
            lora = g.add(
                "LoraLoaderModelOnly", [lora_name, 1.0], {"model": shift.out(0)}, title=f"LoRA 4 pasos · {label}"
            )
            return g.add(
                "ComfySwitchNode",
                [False],
                {"on_false": shift.out(0), "on_true": lora.out(0), "switch": turbo.out(0)},
                title=f"{label}: calidad / turbo",
            ).out(0)

        m_high = expert(WAN_HIGH, WAN_LORA_HIGH, "ruido alto")
        m_low = expert(WAN_LOW, WAN_LORA_LOW, "ruido bajo")

        def by_turbo(quality, fast, kind: str, title: str):
            q = g.add(kind, [quality, "fixed"] if kind == "PrimitiveInt" else [quality], title=f"{title} (calidad)")
            t = g.add(kind, [fast, "fixed"] if kind == "PrimitiveInt" else [fast], title=f"{title} (turbo)")
            return g.add(
                "ComfySwitchNode",
                [False],
                {"on_false": q.out(0), "on_true": t.out(0), "switch": turbo.out(0)},
                title=title,
            ).out(0)

        steps = by_turbo(20, 4, "PrimitiveInt", "Pasos")
        split = by_turbo(10, 2, "PrimitiveInt", "Cambio de modelo en el paso")
        cfg = by_turbo(3.5, 1.0, "PrimitiveFloat", "CFG")

        ks_high = g.add(
            "KSamplerAdvanced",
            ["enable", 1, "randomize", 4, 1.0, "euler", "simple", 0, 2, "enable"],
            {
                "model": m_high,
                "positive": cond.out(0),
                "negative": cond.out(1),
                "latent_image": cond.out(2),
                "noise_seed": semilla.out(0),
                "steps": steps,
                "cfg": cfg,
                "end_at_step": split,
            },
            title="Muestreo 1 · ruido alto (movimiento)",
        )
        ks_low = g.add(
            "KSamplerAdvanced",
            ["disable", 0, "fixed", 4, 1.0, "euler", "simple", 2, 10000, "disable"],
            {
                "model": m_low,
                "positive": cond.out(0),
                "negative": cond.out(1),
                "latent_image": ks_high.out(0),
                "steps": steps,
                "cfg": cfg,
                "start_at_step": split,
            },
            title="Muestreo 2 · ruido bajo (detalle)",
        )
        raw = g.add("VAEDecode", [], {"samples": ks_low.out(0), "vae": vae.out(0)}, title="Frames del plano (16 fps)")

    # ---------------------------------------------------------------- acabado
    with g.group("ACABADO · 1080p (SeedVR2) + 32 fps (FILM) + guardar", GREEN):
        note(
            g,
            "### Acabado\n\n"
            "1. **1080p con SeedVR2** (apagado por defecto): el mismo SeedVR2 que usas para las fotos, en "
            "modo vídeo. Trocea el plano en el tiempo si no te cabe en la VRAM. Con el interruptor en "
            "`false` ni se carga.\n"
            "2. **32 fps con FILM**: Wan saca 16 fps y en un travelling lento se nota. FILM inventa un frame "
            "intermedio entre cada par y el plano pasa a 32 fps con la misma duración.\n"
            "3. Se guarda el vídeo en `output/tour/plano_…mp4` y el **último frame** en "
            "`output/tour/ultimo_frame_…png` (a la resolución de Wan, listo para encadenar).\n\n"
            "Si ves parpadeo de color tras SeedVR2, cambia la corrección de color a `none`.",
            title="Acabado",
        )
        upscaled = seedvr2_video_upscale(g, raw.out(0), scale=1.5)
        after_up = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": raw.out(0), "on_true": upscaled, "switch": hd.out(0)},
            title="¿1080p?",
        )
        interp_model = g.add("FrameInterpolationModelLoader", [FILM_INTERP], title="Modelo · FILM")
        interp = g.add(
            "FrameInterpolate", [2], {"interp_model": interp_model.out(0), "images": after_up.out(0)}, title="x2 frames"
        )
        after_fi = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": after_up.out(0), "on_true": interp.out(0), "switch": fluido.out(0)},
            title="¿32 fps?",
        )
        fps16 = g.add("PrimitiveFloat", [16.0], title="fps sin FILM")
        fps32 = g.add("PrimitiveFloat", [32.0], title="fps con FILM")
        fps = g.add(
            "ComfySwitchNode",
            [False],
            {"on_false": fps16.out(0), "on_true": fps32.out(0), "switch": fluido.out(0)},
            title="fps",
        )
        video = g.add("CreateVideo", [16.0], {"images": after_fi.out(0), "fps": fps.out(0)})
        g.add("SaveVideo", ["tour/plano", "auto", "auto"], {"video": video.out(0)}, title="GUARDAR PLANO")
        last = g.add("ImageFromBatch", [-1, 1], {"image": raw.out(0)}, title="Último frame")
        g.add("SaveImage", ["tour/ultimo_frame"], {"images": last.out(0)}, title="GUARDAR ÚLTIMO FRAME")

    g.save(os.path.join(OUT, "20_video_tour_inmobiliario.json"))


def main():
    os.makedirs(OUT, exist_ok=True)
    build_rescue()
    build_packshot()
    build_lifestyle()
    build_retouch()
    build_estudio()
    build_video_tour()
    for f in sorted(os.listdir(OUT)):
        print("escrito:", os.path.join("workflows", f))


if __name__ == "__main__":
    main()
