# Plantillas oficiales de ComfyUI (base de los workflows de LTX-2.5)

Copias sin modificar de las plantillas oficiales de
[Comfy-Org/workflow_templates](https://github.com/Comfy-Org/workflow_templates) (licencia MIT,
© Comfy Org), commit `9b91285` del 26-09-2026:

- `video_ltx2_5_i2v.json` — LTX-2.5 imagen a vídeo (dos etapas con reescalado latente x2)
- `video_ltx2_5_flf2v.json` — LTX-2.5 primer y último frame a vídeo

`tools/build_workflows.py` las carga, les añade el panel de movimientos de cámara, el guardado
del último frame y los prompts de tour inmobiliario, y escribe `workflows/21_…` y `workflows/22_…`.
El motor de dentro (el subgrafo) no se toca, salvo el prompt negativo.
