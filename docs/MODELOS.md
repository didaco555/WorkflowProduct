# Modelos a descargar

Todos son gratuitos y de pesos abiertos. Los enlaces salen de las plantillas oficiales de
ComfyUI (`Comfy-Org/workflow_templates`), así que son los archivos empaquetados que espera el
núcleo de ComfyUI.

Tamaño total con las variantes recomendadas: **~45 GB** para fotografía de producto. Para vídeo
tour, LTX-2.5 (sección 7, la recomendada) o Wan 2.2 (sección 6, ~36 GB). Puedes empezar sólo con el bloque de
Qwen-Image-Edit + BiRefNet + RealESRGAN (~30 GB) y añadir el resto después.

## Dónde va cada cosa

```
📂 ComfyUI/
└── 📂 models/
    ├── 📂 diffusion_models/
    │   ├── qwen_image_edit_2511_fp8mixed.safetensors
    │   ├── flux-2-klein-9b-fp8.safetensors
    │   ├── seedvr2_3b_int8_convrot.safetensors
    │   ├── wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors   ← vídeo
    │   └── wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors    ← vídeo
    ├── 📂 text_encoders/
    │   ├── qwen_2.5_vl_7b_fp8_scaled.safetensors
    │   ├── qwen_3_8b_fp8mixed.safetensors
    │   └── umt5_xxl_fp8_e4m3fn_scaled.safetensors             ← vídeo
    ├── 📂 vae/
    │   ├── qwen_image_vae.safetensors
    │   ├── flux2-vae.safetensors
    │   ├── seedvr2_ema_vae_fp16.safetensors
    │   └── wan_2.1_vae.safetensors                            ← vídeo
    ├── 📂 loras/
    │   ├── Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors
    │   ├── wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors   ← vídeo
    │   └── wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors    ← vídeo
    ├── 📂 frame_interpolation/
    │   └── film_net_fp16.safetensors                          ← vídeo
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


## 6 · Vídeo: Wan 2.2 14B + FILM

Para el workflow `20_video_tour_inmobiliario.json` (la alternativa a LTX-2.5 de la sección 7). Wan 2.2 imagen-a-vídeo son **dos modelos**
(ruido alto y ruido bajo) que se usan uno detrás de otro; hacen falta los dos. Licencia Apache 2.0.
El método y el porqué de cada ajuste están en [`VIDEO_TOUR.md`](VIDEO_TOUR.md).

- `diffusion_models/` → [wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors) *(~14 GB)*
- `diffusion_models/` → [wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors) *(~14 GB)*
- `text_encoders/` → [umt5_xxl_fp8_e4m3fn_scaled.safetensors](https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors) *(~7 GB)*
- `vae/` → [wan_2.1_vae.safetensors](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors) *(sí, el VAE de 2.1: es el que usa el 14B)*
- `loras/` → [wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors) *(el modo ⚡ TURBO)*
- `loras/` → [wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors)
- `frame_interpolation/` → [film_net_fp16.safetensors](https://huggingface.co/Comfy-Org/frame_interpolation/resolve/main/frame_interpolation/film_net_fp16.safetensors) *(pasa de 16 a 32 fps)*

El reescalado a 1080p usa el **SeedVR2 3B** de la sección 3, que ya tienes.

**VRAM**: cada modelo de 14B ocupa ~14 GB en fp8, pero ComfyUI carga uno y aparca el otro en RAM.
Con 24 GB, 1280×720 va cómodo; con 16 GB, genera a 832×480 y reescala con SeedVR2. Ten 64 GB de RAM
si puedes.

**Alternativa más rápida**: el nodo también acepta modelos RIFE (p. ej. `rife_v4.26.safetensors`,
que la plantilla oficial de ComfyUI lista junto a FILM). Si lo pones en `frame_interpolation/`,
elígelo en el nodo *Modelo · FILM*: es más rápido y en movimientos lentos apenas se nota.

**Actualiza ComfyUI**: los nodos de interpolación (`FrameInterpolate`) y el troceo de SeedVR2 para
vídeo (`SeedVR2TemporalChunk`) son de este año.


## 7 · Vídeo: LTX-2.5 (recomendado para vídeo tour)

Para los workflows `21_video_tour_ltx25.json` (foto → plano) y `22_video_transicion_ltx25.json`
(foto → foto). Es el modelo **gratuito mejor valorado que puedes usar en España** en ComfyUI de
forma nativa: licencia comunitaria de Lightricks, gratis para uso comercial por debajo de 10 M$ de
facturación. El porqué está en [`VIDEO_TOUR.md`](VIDEO_TOUR.md).

> **Antes de descargar:** entra con tu cuenta en
> [huggingface.co/Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5) y acepta la
> licencia. Sin eso, las descargas de ese repositorio fallan.

- `diffusion_models/` → [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors](https://huggingface.co/Lightricks/LTX-2.5/resolve/main/diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors)
- `vae/` → [ltx-2.5-video-vae-bf16.safetensors](https://huggingface.co/Lightricks/LTX-2.5/resolve/main/vae/ltx-2.5-video-vae-bf16.safetensors)
- `vae/` → [ltx-2.5-audio-vae-bf16.safetensors](https://huggingface.co/Lightricks/LTX-2.5/resolve/main/vae/ltx-2.5-audio-vae-bf16.safetensors)
- `text_encoders/` → [gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors](https://huggingface.co/Lightricks/LTX-2.5/resolve/main/text_encoders/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors)
- `text_encoders/` → [gemma4_e2b_it_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/gemma-4/resolve/main/text_encoders/gemma4_e2b_it_int8_convrot.safetensors) *(el “prompt enhance”; va apagado, pero el workflow lo carga igual)*
- `latent_upscale_models/` → [ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors](https://huggingface.co/Lightricks/LTX-2.5/resolve/main/latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors) *(sólo el 21; crea la carpeta si no existe)*

Son los archivos que piden las plantillas oficiales de ComfyUI para LTX-2.5. El modelo va en
**int8 convrot**, el mismo formato que tu SeedVR2, y ComfyUI lo va pasando entre RAM y VRAM.



## 8 · Vídeo: MiniMax H3 y FastVideo FastH3

Para `23_video_tour_minimax_h3.json` (H3 base) y `24_video_tour_fasth3.json` (FastH3, 8 pasos).
Es el modelo abierto mejor valorado en imagen a vídeo, pero **su licencia excluye la UE, Reino Unido,
Corea y EE. UU.**: en España no te cubre. Úsalo bajo tu responsabilidad.

- `diffusion_models/` → [minimax_h3_fl2va_pruned_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors) *(23)*
- `diffusion_models/` → [fastvideo_fasth3_8step_v2_pruned_int8_convrot.safetensors](https://huggingface.co/FastVideo/FastVideo-FastH3-Comfy/resolve/main/diffusion_models/fastvideo_fasth3_8step_v2_pruned_int8_convrot.safetensors) *(24)*
- `text_encoders/` → [qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors)
- `vae/` → [minimax_h3_video_vae_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_video_vae_int8_convrot.safetensors)
- `vae/` → [minimax_h3_audio_vae_fp32.safetensors](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_audio_vae_fp32.safetensors)
- `loras/` → [minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors](https://huggingface.co/lightx2v/Minimax-h3-Turbo/resolve/main/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors) *(sólo el 23: aunque el turbo vaya apagado, el workflow comprueba que el archivo existe)*

Son los archivos de las plantillas oficiales de ComfyUI. Si ya habías abierto esas plantillas, lo
normal es que los tengas todos.



## 9 · Vídeo 2.5D: Depth Anything 3 + DepthFlow (sin IA generativa)

Para `25_video_tour_parallax.json`: la cámara recorre la foto usando su profundidad. No genera
nada, sólo mueve los píxeles de la foto.

- `geometry_estimation/` → [depth_anything_3_mono_large.safetensors](https://huggingface.co/Comfy-Org/Depth-Anything-3/resolve/main/geometry_estimation/depth_anything_3_mono_large.safetensors) *(crea la carpeta si no existe; Depth Anything 3 va en el núcleo de ComfyUI)*
- Paquete de nodos **ComfyUI-Depthflow-Nodes** (de akatz, sobre la librería DepthFlow de
  Tremeschin). Es el único workflow del repositorio con nodos de terceros. Se instala así:
  1. Abre `25_video_tour_parallax.json`: los nodos de DepthFlow salen en rojo.
  2. **Manager → Install Missing Custom Nodes** → instala *ComfyUI-Depthflow-Nodes*.
  3. Reinicia ComfyUI.

  Instala sus dependencias en el Python de ComfyUI, entre ellas `transformers 4.53` y `gradio`.
  Son compatibles con lo que pide el núcleo de ComfyUI (`transformers >= 4.50.3`). Si usas otros
  nodos de terceros que exijan una versión más nueva de `transformers`, alguno podría quejarse.
  DepthFlow renderiza con OpenGL: en Windows con la gráfica de NVIDIA funciona sin más.


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

# vídeo tour (workflow 20)
dl diffusion_models https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors
dl diffusion_models https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors
dl text_encoders    https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors
dl vae              https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors
dl loras            https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors
dl loras            https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors
dl frame_interpolation https://huggingface.co/Comfy-Org/frame_interpolation/resolve/main/frame_interpolation/film_net_fp16.safetensors

# vídeo tour con LTX-2.5 (workflows 21 y 22) — antes acepta la licencia en huggingface.co/Lightricks/LTX-2.5
# y añade a curl tu token:  -H "Authorization: Bearer hf_…"
dl diffusion_models https://huggingface.co/Lightricks/LTX-2.5/resolve/main/diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors
dl vae              https://huggingface.co/Lightricks/LTX-2.5/resolve/main/vae/ltx-2.5-video-vae-bf16.safetensors
dl vae              https://huggingface.co/Lightricks/LTX-2.5/resolve/main/vae/ltx-2.5-audio-vae-bf16.safetensors
dl text_encoders    https://huggingface.co/Lightricks/LTX-2.5/resolve/main/text_encoders/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors
dl text_encoders    https://huggingface.co/Comfy-Org/gemma-4/resolve/main/text_encoders/gemma4_e2b_it_int8_convrot.safetensors
dl latent_upscale_models https://huggingface.co/Lightricks/LTX-2.5/resolve/main/latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors
```

Algunos repositorios de Hugging Face piden aceptar la licencia con la cuenta antes de descargar
(es el caso de los de `black-forest-labs`). Si un `curl` devuelve un archivo de pocos KB, ábrelo:
suele ser el HTML de la página de licencia.
