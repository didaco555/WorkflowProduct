# Modelos a descargar

Todos son gratuitos y de pesos abiertos. Los enlaces salen de las plantillas oficiales de
ComfyUI (`Comfy-Org/workflow_templates`), así que son los archivos empaquetados que espera el
núcleo de ComfyUI.

Tamaño total con las variantes recomendadas: **~45 GB**. Puedes empezar sólo con el bloque de
Qwen-Image-Edit + BiRefNet + RealESRGAN (~30 GB) y añadir el resto después.

## Dónde va cada cosa

```
📂 ComfyUI/
└── 📂 models/
    ├── 📂 diffusion_models/
    │   ├── qwen_image_edit_2511_fp8mixed.safetensors
    │   ├── flux-2-klein-9b-fp8.safetensors
    │   └── seedvr2_3b_int8_convrot.safetensors
    ├── 📂 text_encoders/
    │   ├── qwen_2.5_vl_7b_fp8_scaled.safetensors
    │   └── qwen_3_8b_fp8mixed.safetensors
    ├── 📂 vae/
    │   ├── qwen_image_vae.safetensors
    │   ├── flux2-vae.safetensors
    │   └── seedvr2_ema_vae_fp16.safetensors
    ├── 📂 loras/
    │   └── Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors
    ├── 📂 background_removal/
    │   └── birefnet.safetensors
    └── 📂 upscale_models/
        └── RealESRGAN_x4plus.safetensors
```

## 1 · Qwen-Image-Edit 2511 — motor principal (obligatorio)

Modelo de edición por instrucciones. Es el que mejor conserva **logotipos y texto de etiqueta**,
que es exactamente lo que se rompe en fotografía de producto.

- `diffusion_models/` → [qwen_image_edit_2511_fp8mixed.safetensors](https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors)
- `text_encoders/` → [qwen_2.5_vl_7b_fp8_scaled.safetensors](https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors)
- `vae/` → [qwen_image_vae.safetensors](https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors)
- `loras/` → [Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors](https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning/resolve/main/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors) *(el modo ⚡ TURBO)*

**Variantes del modelo principal** (cambia el nombre en el nodo `UNETLoader`):

| Archivo | VRAM aprox. | Notas |
|---|---|---|
| `qwen_image_edit_2511_bf16.safetensors` | 24 GB+ | máxima calidad, [enlace](https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_2511_bf16.safetensors) |
| `qwen_image_edit_2511_fp8mixed.safetensors` | ~16 GB | **recomendado** |
| `qwen_image_edit_2511_int8_convrot.safetensors` | ~12 GB | [enlace](https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_2511_int8_convrot.safetensors) |

**LoRA opcional de reiluminación** (para un control de luz más agresivo en packshot):
[Qwen-Image-Edit-2509-Relight.safetensors](https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/loras/Qwen-Image-Edit-2509-Relight.safetensors) → `loras/`.
Se añade con un nodo `LoraLoaderModelOnly` extra antes del `KSampler`.

## 2 · FLUX.2 [klein] 9B destilado — motor alternativo de lifestyle

Apache-2.0, 4 pasos. Va en el workflow `02`, como motor alternativo para lifestyle.
El workflow `10` no lo usa, así que puedes saltarte esta descarga si sólo vas a usar ese.

- `diffusion_models/` → [flux-2-klein-9b-fp8.safetensors](https://huggingface.co/black-forest-labs/FLUX.2-klein-9b-fp8/resolve/main/flux-2-klein-9b-fp8.safetensors)
- `text_encoders/` → [qwen_3_8b_fp8mixed.safetensors](https://huggingface.co/Comfy-Org/flux2-klein-9B/resolve/main/split_files/text_encoders/qwen_3_8b_fp8mixed.safetensors)
- `vae/` → [flux2-vae.safetensors](https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors)

**Versión ligera 4B** (si tienes poca VRAM): cambia en los cargadores del workflow
`flux-2-klein-9b-fp8.safetensors` → [flux-2-klein-4b-fp8.safetensors](https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8/resolve/main/flux-2-klein-4b-fp8.safetensors)
y `qwen_3_8b_fp8mixed.safetensors` → [qwen_3_4b.safetensors](https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors).

**Decodificador rápido opcional**: [full_encoder_small_decoder.safetensors](https://huggingface.co/black-forest-labs/FLUX.2-small-decoder/resolve/main/full_encoder_small_decoder.safetensors)
→ `vae/`. Es el que usa la plantilla oficial de klein 9B; decodifica más rápido con una pérdida
mínima. Si lo descargas, selecciónalo en el `VAELoader` del motor B.

## 3 · SeedVR2 3B — rescate de fotos malas

- `diffusion_models/` → [seedvr2_3b_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/SeedVR2/resolve/main/diffusion_models/seedvr2_3b_int8_convrot.safetensors)
- `vae/` → [seedvr2_ema_vae_fp16.safetensors](https://huggingface.co/Comfy-Org/SeedVR2/resolve/main/vae/seedvr2_ema_vae_fp16.safetensors)

Variante **7B** si te sobra VRAM y quieres más reconstrucción:
[seedvr2_7b_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/SeedVR2/resolve/main/diffusion_models/seedvr2_7b_int8_convrot.safetensors)
(mismo VAE; cambia el nombre en el `UNETLoader` del grupo *Nivel 0*).

## 4 · BiRefNet — quitar fondo

- `background_removal/` → [birefnet.safetensors](https://huggingface.co/Comfy-Org/BiRefNet/resolve/main/background_removal/birefnet.safetensors)

Lo cargan los nodos del núcleo `Load Background Removal Model` + `Remove Background`. Si pones
otro modelo compatible (RMBG) en esa misma carpeta, aparece en el desplegable.

## 5 · Reescalado GAN

- `upscale_models/` → [RealESRGAN_x4plus.safetensors](https://huggingface.co/Comfy-Org/Real-ESRGAN_repackaged/resolve/main/RealESRGAN_x4plus.safetensors)

Alternativas populares para producto (más “crujientes”): `4x-UltraSharp`, `4x_NMKD-Siax_200k`.
Cualquier archivo que dejes en `upscale_models/` aparece en el desplegable del nodo.

---

## Descarga rápida por línea de comandos

```bash
cd /ruta/a/ComfyUI/models

dl() { mkdir -p "$1" && curl -L --fail -o "$1/$(basename "$2")" "$2"; }

dl diffusion_models https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors
dl text_encoders    https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors
dl vae              https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors
dl loras            https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning/resolve/main/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors
dl background_removal https://huggingface.co/Comfy-Org/BiRefNet/resolve/main/background_removal/birefnet.safetensors
dl upscale_models   https://huggingface.co/Comfy-Org/Real-ESRGAN_repackaged/resolve/main/RealESRGAN_x4plus.safetensors

# opcionales
dl diffusion_models https://huggingface.co/Comfy-Org/SeedVR2/resolve/main/diffusion_models/seedvr2_3b_int8_convrot.safetensors
dl vae              https://huggingface.co/Comfy-Org/SeedVR2/resolve/main/vae/seedvr2_ema_vae_fp16.safetensors
dl diffusion_models https://huggingface.co/black-forest-labs/FLUX.2-klein-9b-fp8/resolve/main/flux-2-klein-9b-fp8.safetensors
dl text_encoders    https://huggingface.co/Comfy-Org/flux2-klein-9B/resolve/main/split_files/text_encoders/qwen_3_8b_fp8mixed.safetensors
dl vae              https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors
```

Algunos repositorios de Hugging Face piden aceptar la licencia con la cuenta antes de descargar
(es el caso de los de `black-forest-labs`). Si un `curl` devuelve un archivo de pocos KB, ábrelo:
suele ser el HTML de la página de licencia.
