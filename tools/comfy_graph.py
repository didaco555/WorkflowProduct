"""Constructor de grafos ComfyUI en formato workflow (.json de la UI).

El esquema de cada nodo (nombres/orden de entradas, widgets y salidas) está copiado
literalmente del código fuente de ComfyUI (`nodes.py` y `comfy_extras/*.py`) y
contrastado con las plantillas oficiales de `Comfy-Org/workflow_templates`.

Uso:
    g = Graph()
    img = g.add("LoadImage", ["producto.png", "image"])
    esc = g.add("ImageScaleToTotalPixels", ["lanczos", 1.0, 16], {"image": img.out(0)})
    g.save("salida.json")
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

# --------------------------------------------------------------------------------------
# Tabla de esquemas
#   inputs  : entradas por enlace  -> (nombre, tipo, opcional)
#   widgets : widgets en orden     -> (nombre, tipo)   [tipo se usa si se convierte a entrada]
#   outputs : salidas en orden     -> (nombre, tipo)
# --------------------------------------------------------------------------------------

SCHEMAS: dict[str, dict] = {
    # ---- entrada / salida -------------------------------------------------------------
    "LoadImage": {
        "inputs": [],
        "widgets": [("image", "COMBO"), ("upload", "COMBO")],
        "outputs": [("IMAGE", "IMAGE"), ("MASK", "MASK")],
    },
    "SaveImage": {
        "inputs": [("images", "IMAGE", False)],
        "widgets": [("filename_prefix", "STRING")],
        "outputs": [],
    },
    "PreviewImage": {
        "inputs": [("images", "IMAGE", False)],
        "widgets": [],
        "outputs": [],
    },
    "MaskPreview": {
        "inputs": [("mask", "MASK", False)],
        "widgets": [],
        "outputs": [],
    },
    "ImageCompare": {
        "inputs": [("image_a", "IMAGE", True), ("image_b", "IMAGE", True)],
        "widgets": [],
        "outputs": [],
    },
    "MarkdownNote": {"inputs": [], "widgets": [("text", "STRING")], "outputs": []},
    "Note": {"inputs": [], "widgets": [("text", "STRING")], "outputs": []},

    # ---- escalado / utilidades de imagen ----------------------------------------------
    "ImageScale": {
        "inputs": [("image", "IMAGE", False)],
        "widgets": [("upscale_method", "COMBO"), ("width", "INT"), ("height", "INT"), ("crop", "COMBO")],
        "outputs": [("IMAGE", "IMAGE")],
    },
    "ImageScaleBy": {
        "inputs": [("image", "IMAGE", False)],
        "widgets": [("upscale_method", "COMBO"), ("scale_by", "FLOAT")],
        "outputs": [("IMAGE", "IMAGE")],
    },
    "ImageScaleToTotalPixels": {
        "inputs": [("image", "IMAGE", False)],
        "widgets": [("upscale_method", "COMBO"), ("megapixels", "FLOAT"), ("resolution_steps", "INT")],
        "outputs": [("IMAGE", "IMAGE")],
    },
    "ImageScaleToMaxDimension": {
        "inputs": [("image", "IMAGE", False)],
        "widgets": [("upscale_method", "COMBO"), ("largest_size", "INT")],
        "outputs": [("IMAGE", "IMAGE")],
    },
    "GetImageSize": {
        "inputs": [("image", "IMAGE", False)],
        "widgets": [],
        "outputs": [("width", "INT"), ("height", "INT"), ("batch_size", "INT")],
    },
    "EmptyImage": {
        "inputs": [],
        "widgets": [("width", "INT"), ("height", "INT"), ("batch_size", "INT"), ("color", "INT")],
        "outputs": [("IMAGE", "IMAGE")],
    },
    "ImageBlur": {
        "inputs": [("image", "IMAGE", False)],
        "widgets": [("blur_radius", "INT"), ("sigma", "FLOAT")],
        "outputs": [("IMAGE", "IMAGE")],
    },
    "ImageSharpen": {
        "inputs": [("image", "IMAGE", False)],
        "widgets": [("sharpen_radius", "INT"), ("sigma", "FLOAT"), ("alpha", "FLOAT")],
        "outputs": [("IMAGE", "IMAGE")],
    },
    "ImageBlend": {
        "inputs": [("image1", "IMAGE", False), ("image2", "IMAGE", False)],
        "widgets": [("blend_factor", "FLOAT"), ("blend_mode", "COMBO")],
        "outputs": [("IMAGE", "IMAGE")],
    },
    "ImageInvert": {
        "inputs": [("image", "IMAGE", False)],
        "widgets": [],
        "outputs": [("IMAGE", "IMAGE")],
    },
    "ImageCompositeMasked": {
        "inputs": [("destination", "IMAGE", False), ("source", "IMAGE", False), ("mask", "MASK", True)],
        "widgets": [("x", "INT"), ("y", "INT"), ("resize_source", "BOOLEAN")],
        "outputs": [("IMAGE", "IMAGE")],
    },
    "BatchImagesNode": {
        # entradas autogrow: images.image0, images.image1, ... y un hueco libre al final
        "inputs": [
            ("images.image0", "IMAGE", False),
            ("images.image1", "IMAGE", False),
            ("images.image2", "IMAGE", True),
            ("images.image3", "IMAGE", True),
        ],
        "widgets": [],
        "outputs": [("IMAGE", "IMAGE")],
    },
    "JoinImageWithAlpha": {
        "inputs": [("image", "IMAGE", False), ("alpha", "MASK", False)],
        "widgets": [],
        "outputs": [("IMAGE", "IMAGE")],
    },

    # ---- máscaras ----------------------------------------------------------------------
    "InvertMask": {"inputs": [("mask", "MASK", False)], "widgets": [], "outputs": [("MASK", "MASK")]},
    "MaskToImage": {"inputs": [("mask", "MASK", False)], "widgets": [], "outputs": [("IMAGE", "IMAGE")]},
    "GrowMask": {
        "inputs": [("mask", "MASK", False)],
        "widgets": [("expand", "INT"), ("tapered_corners", "BOOLEAN")],
        "outputs": [("MASK", "MASK")],
    },
    "FeatherMask": {
        "inputs": [("mask", "MASK", False)],
        "widgets": [("left", "INT"), ("top", "INT"), ("right", "INT"), ("bottom", "INT")],
        "outputs": [("MASK", "MASK")],
    },

    # ---- quitar fondo (núcleo de ComfyUI, BiRefNet / RMBG) ------------------------------
    "LoadBackgroundRemovalModel": {
        "inputs": [],
        "widgets": [("bg_removal_name", "COMBO")],
        "outputs": [("bg_model", "BACKGROUND_REMOVAL")],
    },
    "RemoveBackground": {
        "inputs": [("bg_removal_model", "BACKGROUND_REMOVAL", False), ("image", "IMAGE", False)],
        "widgets": [],
        "outputs": [("mask", "MASK")],
    },

    # ---- carga de modelos ---------------------------------------------------------------
    "UNETLoader": {
        "inputs": [],
        "widgets": [("unet_name", "COMBO"), ("weight_dtype", "COMBO")],
        "outputs": [("MODEL", "MODEL")],
    },
    "CLIPLoader": {
        "inputs": [],
        "widgets": [("clip_name", "COMBO"), ("type", "COMBO"), ("device", "COMBO")],
        "outputs": [("CLIP", "CLIP")],
    },
    "VAELoader": {"inputs": [], "widgets": [("vae_name", "COMBO")], "outputs": [("VAE", "VAE")]},
    "LoraLoaderModelOnly": {
        "inputs": [("model", "MODEL", False)],
        "widgets": [("lora_name", "COMBO"), ("strength_model", "FLOAT")],
        "outputs": [("MODEL", "MODEL")],
    },
    "UpscaleModelLoader": {
        "inputs": [],
        "widgets": [("model_name", "COMBO")],
        "outputs": [("UPSCALE_MODEL", "UPSCALE_MODEL")],
    },
    "ImageUpscaleWithModel": {
        "inputs": [("upscale_model", "UPSCALE_MODEL", False), ("image", "IMAGE", False)],
        "widgets": [],
        "outputs": [("IMAGE", "IMAGE")],
    },

    # ---- VAE ------------------------------------------------------------------------------
    "VAEEncode": {
        "inputs": [("pixels", "IMAGE", False), ("vae", "VAE", False)],
        "widgets": [],
        "outputs": [("LATENT", "LATENT")],
    },
    "VAEDecode": {
        "inputs": [("samples", "LATENT", False), ("vae", "VAE", False)],
        "widgets": [],
        "outputs": [("IMAGE", "IMAGE")],
    },
    "VAEEncodeTiled": {
        "inputs": [("pixels", "IMAGE", False), ("vae", "VAE", False)],
        "widgets": [("tile_size", "INT"), ("overlap", "INT"), ("temporal_size", "INT"), ("temporal_overlap", "INT")],
        "outputs": [("LATENT", "LATENT")],
    },
    "VAEDecodeTiled": {
        "inputs": [("samples", "LATENT", False), ("vae", "VAE", False)],
        "widgets": [("tile_size", "INT"), ("overlap", "INT"), ("temporal_size", "INT"), ("temporal_overlap", "INT")],
        "outputs": [("IMAGE", "IMAGE")],
    },

    # ---- condicionamiento / muestreo --------------------------------------------------------
    "CLIPTextEncode": {
        "inputs": [("clip", "CLIP", False)],
        "widgets": [("text", "STRING")],
        "outputs": [("CONDITIONING", "CONDITIONING")],
    },
    "ConditioningZeroOut": {
        "inputs": [("conditioning", "CONDITIONING", False)],
        "widgets": [],
        "outputs": [("CONDITIONING", "CONDITIONING")],
    },
    "TextEncodeQwenImageEditPlus": {
        "inputs": [
            ("clip", "CLIP", False),
            ("vae", "VAE", True),
            ("image1", "IMAGE", True),
            ("image2", "IMAGE", True),
            ("image3", "IMAGE", True),
        ],
        "widgets": [("prompt", "STRING")],
        "outputs": [("CONDITIONING", "CONDITIONING")],
    },
    "FluxKontextImageScale": {
        "inputs": [("image", "IMAGE", False)],
        "widgets": [],
        "outputs": [("IMAGE", "IMAGE")],
    },
    "FluxKontextMultiReferenceLatentMethod": {
        "inputs": [("conditioning", "CONDITIONING", False)],
        "widgets": [("reference_latents_method", "COMBO")],
        "outputs": [("CONDITIONING", "CONDITIONING")],
    },
    "ReferenceLatent": {
        "inputs": [("conditioning", "CONDITIONING", False), ("latent", "LATENT", True)],
        "widgets": [],
        "outputs": [("CONDITIONING", "CONDITIONING")],
    },
    "ModelSamplingAuraFlow": {
        "inputs": [("model", "MODEL", False)],
        "widgets": [("shift", "FLOAT")],
        "outputs": [("MODEL", "MODEL")],
    },
    "CFGNorm": {
        "inputs": [("model", "MODEL", False)],
        "widgets": [("strength", "FLOAT"), ("pre_cfg", "BOOLEAN")],
        "outputs": [("patched_model", "MODEL")],
    },
    "DifferentialDiffusion": {
        "inputs": [("model", "MODEL", False)],
        "widgets": [],
        "outputs": [("MODEL", "MODEL")],
    },
    "SetLatentNoiseMask": {
        "inputs": [("samples", "LATENT", False), ("mask", "MASK", False)],
        "widgets": [],
        "outputs": [("LATENT", "LATENT")],
    },
    "KSampler": {
        "inputs": [
            ("model", "MODEL", False),
            ("positive", "CONDITIONING", False),
            ("negative", "CONDITIONING", False),
            ("latent_image", "LATENT", False),
        ],
        "widgets": [
            ("seed", "INT"),
            ("control_after_generate", "COMBO"),
            ("steps", "INT"),
            ("cfg", "FLOAT"),
            ("sampler_name", "COMBO"),
            ("scheduler", "COMBO"),
            ("denoise", "FLOAT"),
        ],
        "outputs": [("LATENT", "LATENT")],
    },
    "KSamplerSelect": {"inputs": [], "widgets": [("sampler_name", "COMBO")], "outputs": [("SAMPLER", "SAMPLER")]},
    "RandomNoise": {
        "inputs": [],
        "widgets": [("noise_seed", "INT"), ("control_after_generate", "COMBO")],
        "outputs": [("NOISE", "NOISE")],
    },
    "CFGGuider": {
        "inputs": [("model", "MODEL", False), ("positive", "CONDITIONING", False), ("negative", "CONDITIONING", False)],
        "widgets": [("cfg", "FLOAT")],
        "outputs": [("GUIDER", "GUIDER")],
    },
    "SamplerCustomAdvanced": {
        "inputs": [
            ("noise", "NOISE", False),
            ("guider", "GUIDER", False),
            ("sampler", "SAMPLER", False),
            ("sigmas", "SIGMAS", False),
            ("latent_image", "LATENT", False),
        ],
        "widgets": [],
        "outputs": [("output", "LATENT"), ("denoised_output", "LATENT")],
    },
    "EmptyFlux2LatentImage": {
        "inputs": [],
        "widgets": [("width", "INT"), ("height", "INT"), ("batch_size", "INT")],
        "outputs": [("LATENT", "LATENT")],
    },
    "Flux2Scheduler": {
        "inputs": [],
        "widgets": [("steps", "INT"), ("width", "INT"), ("height", "INT")],
        "outputs": [("SIGMAS", "SIGMAS")],
    },

    # ---- SeedVR2 (restauración / reescalado) -------------------------------------------------
    "SeedVR2Preprocess": {
        "inputs": [("resized_images", "IMAGE", False)],
        "widgets": [],
        "outputs": [("images", "IMAGE")],
    },
    "SeedVR2Conditioning": {
        "inputs": [("model", "MODEL", False), ("vae_conditioning", "LATENT", False)],
        "widgets": [],
        "outputs": [("positive", "CONDITIONING"), ("negative", "CONDITIONING")],
    },
    "SeedVR2PostProcessing": {
        "inputs": [("images", "IMAGE", False), ("original_resized_images", "IMAGE", False)],
        "widgets": [("color_correction_method", "COMBO")],
        "outputs": [("images", "IMAGE")],
    },

    "SeedVR2TemporalChunk": {
        # parte el latente de vídeo en trozos que quepan en VRAM; la salida `latents` es una lista
        "inputs": [("latent", "LATENT", False)],
        "widgets": [("temporal_overlap", "INT"), ("chunking_mode", "COMBO")],
        "outputs": [("latents", "LATENT"), ("temporal_overlap", "INT")],
    },
    "SeedVR2TemporalMerge": {
        "inputs": [("latents", "LATENT", False), ("temporal_overlap", "INT", False)],
        "widgets": [],
        "outputs": [("latent", "LATENT")],
    },

    # ---- vídeo: Wan 2.2 (comfy_extras/nodes_wan.py) ---------------------------------------------
    "ModelSamplingSD3": {
        "inputs": [("model", "MODEL", False)],
        "widgets": [("shift", "FLOAT")],
        "outputs": [("MODEL", "MODEL")],
    },
    "KSamplerAdvanced": {
        "inputs": [
            ("model", "MODEL", False),
            ("positive", "CONDITIONING", False),
            ("negative", "CONDITIONING", False),
            ("latent_image", "LATENT", False),
        ],
        "widgets": [
            ("add_noise", "COMBO"),
            ("noise_seed", "INT"),
            ("control_after_generate", "COMBO"),
            ("steps", "INT"),
            ("cfg", "FLOAT"),
            ("sampler_name", "COMBO"),
            ("scheduler", "COMBO"),
            ("start_at_step", "INT"),
            ("end_at_step", "INT"),
            ("return_with_leftover_noise", "COMBO"),
        ],
        "outputs": [("LATENT", "LATENT")],
    },
    "WanFirstLastFrameToVideo": {
        "inputs": [
            ("positive", "CONDITIONING", False),
            ("negative", "CONDITIONING", False),
            ("vae", "VAE", False),
            ("clip_vision_start_image", "CLIP_VISION_OUTPUT", True),
            ("clip_vision_end_image", "CLIP_VISION_OUTPUT", True),
            ("start_image", "IMAGE", True),
            ("end_image", "IMAGE", True),
        ],
        "widgets": [("width", "INT"), ("height", "INT"), ("length", "INT"), ("batch_size", "INT")],
        "outputs": [("positive", "CONDITIONING"), ("negative", "CONDITIONING"), ("latent", "LATENT")],
    },
    "ImageFromBatch": {
        "inputs": [("image", "IMAGE", False)],
        "widgets": [("batch_index", "INT"), ("length", "INT")],
        "outputs": [("IMAGE", "IMAGE")],
    },

    # ---- vídeo: interpolación de frames y guardado (comfy_extras/nodes_frame_interpolation.py,
    #      comfy_extras/nodes_video.py) ------------------------------------------------------------
    "FrameInterpolationModelLoader": {
        "inputs": [],
        "widgets": [("model_name", "COMBO")],
        "outputs": [("INTERP_MODEL", "INTERP_MODEL")],
    },
    "FrameInterpolate": {
        "inputs": [("interp_model", "INTERP_MODEL", False), ("images", "IMAGE", False)],
        "widgets": [("multiplier", "INT")],
        "outputs": [("IMAGE", "IMAGE")],
    },
    "CreateVideo": {
        "inputs": [("images", "IMAGE", False), ("audio", "AUDIO", True)],
        "widgets": [("fps", "FLOAT")],
        "outputs": [("VIDEO", "VIDEO")],
    },
    "SaveVideo": {
        "inputs": [("video", "VIDEO", False)],
        "widgets": [("filename_prefix", "STRING"), ("format", "COMBO"), ("codec", "COMBO")],
        "outputs": [("video", "VIDEO")],
    },

    # ---- texto ----------------------------------------------------------------------------------
    "StringConcatenate": {
        "inputs": [],
        "widgets": [("string_a", "STRING"), ("string_b", "STRING"), ("delimiter", "STRING")],
        "outputs": [("STRING", "STRING")],
    },

    # ---- lógica -------------------------------------------------------------------------------
    "ComfySwitchNode": {
        "inputs": [("on_false", "*", True), ("on_true", "*", True)],
        "widgets": [("switch", "BOOLEAN")],
        "outputs": [("output", "*")],
    },
    "PrimitiveBoolean": {"inputs": [], "widgets": [("value", "BOOLEAN")], "outputs": [("BOOLEAN", "BOOLEAN")]},
    "PrimitiveInt": {
        "inputs": [],
        "widgets": [("value", "INT"), ("control_after_generate", "COMBO")],
        "outputs": [("INT", "INT")],
    },
    "PrimitiveFloat": {"inputs": [], "widgets": [("value", "FLOAT")], "outputs": [("FLOAT", "FLOAT")]},
    "PrimitiveStringMultiline": {"inputs": [], "widgets": [("value", "STRING")], "outputs": [("STRING", "STRING")]},

    # ---- selector y texto ----------------------------------------------------------------
    "CustomCombo": {
        # widgets_values = [valor, índice, opción_0, ..., opción_n, ""]  (opciones definidas
        # por el usuario en el frontend; ver plantillas oficiales de Comfy-Org)
        "inputs": [],
        "widgets": [("choice", "COMBO")],
        "outputs": [("STRING", "STRING"), ("INDEX", "INT")],
    },
    "JsonExtractString": {
        "inputs": [],
        "widgets": [("json_string", "STRING"), ("key", "STRING")],
        "outputs": [("STRING", "STRING")],
    },
    "StringContains": {
        "inputs": [],
        "widgets": [("string", "STRING"), ("substring", "STRING"), ("case_sensitive", "BOOLEAN")],
        "outputs": [("contains", "BOOLEAN")],
    },
    "StringCompare": {
        "inputs": [],
        "widgets": [
            ("string_a", "STRING"),
            ("string_b", "STRING"),
            ("mode", "COMBO"),
            ("case_sensitive", "BOOLEAN"),
        ],
        "outputs": [("BOOLEAN", "BOOLEAN")],
    },

}

# Nodos cuyo número de widgets lo define el usuario en el frontend.
VARIADIC_WIDGETS = {"CustomCombo"}

# Nodos que sólo existen en el frontend (no tienen definición en el backend).
FRONTEND_ONLY = {"MarkdownNote", "Note"}

MODE_ALWAYS = 0
MODE_NEVER = 2   # "silenciado" / muted
MODE_BYPASS = 4  # "bypass" (Ctrl+B)


@dataclass
class Port:
    node: "Node"
    slot: int
    type: str


@dataclass
class Node:
    id: int
    type: str
    graph: "Graph"
    widgets: list = field(default_factory=list)
    mode: int = MODE_ALWAYS
    title: str | None = None
    color: str | None = None
    match_type: str | None = None  # para nodos de tipo genérico (ComfySwitchNode)
    inputs: dict = field(default_factory=dict)   # nombre -> link_id
    widget_inputs: dict = field(default_factory=dict)  # nombre -> link_id
    out_links: dict = field(default_factory=dict)      # slot -> [link_id]
    pos: tuple = (0, 0)
    size: tuple = (320, 100)

    def out(self, slot: int = 0) -> Port:
        schema = SCHEMAS[self.type]
        t = schema["outputs"][slot][1]
        if t == "*" and self.match_type:
            t = self.match_type
        return Port(self, slot, t)


class Graph:
    def __init__(self, title: str = "workflow"):
        self.title = title
        self.nodes: list[Node] = []
        self._link_specs: list[dict] = []
        self.groups: list[dict] = []
        self._next_node = 1
        self._next_link = 1
        self._band_y = 40.0
        self._current_group: dict | None = None

    # ---------------- construcción ----------------
    def add(
        self,
        node_type: str,
        widgets: list | None = None,
        inputs: dict | None = None,
        *,
        title: str | None = None,
        mode: int = MODE_ALWAYS,
        color: str | None = None,
        match_type: str | None = None,
    ) -> Node:
        if node_type not in SCHEMAS:
            raise KeyError(f"nodo desconocido: {node_type}")
        n = Node(
            id=self._next_node,
            type=node_type,
            graph=self,
            widgets=list(widgets or []),
            mode=mode,
            title=title,
            color=color,
            match_type=match_type,
        )
        self._next_node += 1
        self.nodes.append(n)
        if self._current_group is not None:
            self._current_group["members"].append(n)
        for name, port in (inputs or {}).items():
            self.connect(port, n, name)
        return n

    def connect(self, src: Port, dst: Node, input_name: str) -> None:
        schema = SCHEMAS[dst.type]
        link_inputs = {i[0]: i[1] for i in schema["inputs"]}
        widget_inputs = {w[0]: w[1] for w in schema["widgets"]}
        if input_name in link_inputs:
            expected = link_inputs[input_name]
        elif input_name in widget_inputs:
            expected = widget_inputs[input_name]
        else:
            raise KeyError(f"{dst.type} no tiene entrada '{input_name}'")

        link_type = src.type
        if expected not in ("*", link_type) and link_type != "*":
            raise TypeError(f"{src.node.type}.{src.slot} ({link_type}) -> {dst.type}.{input_name} ({expected})")
        if expected == "*" and dst.match_type is None:
            dst.match_type = link_type
        if src.type == "*" and src.node.match_type is None:
            src.node.match_type = expected

        lid = self._next_link
        self._next_link += 1
        self._link_specs.append(
            {"id": lid, "src": src.node, "slot": src.slot, "dst": dst, "name": input_name, "type": link_type}
        )
        src.node.out_links.setdefault(src.slot, []).append(lid)
        if input_name in link_inputs:
            dst.inputs[input_name] = lid
        else:
            dst.widget_inputs[input_name] = lid

    def _input_slot_index(self, node: Node, input_name: str) -> int:
        """Índice del socket en el array `inputs` serializado (enlaces primero, luego widgets)."""
        schema = SCHEMAS[node.type]
        names = [i[0] for i in schema["inputs"]]
        if input_name in names:
            return names.index(input_name)
        connected_widgets = [w[0] for w in schema["widgets"] if w[0] in node.widget_inputs]
        return len(names) + connected_widgets.index(input_name)

    # ---------------- disposición ----------------
    def group(self, title: str, color: str = "#3f789e"):
        return _GroupCtx(self, title, color)

    # ---------------- serialización ----------------
    def _node_size(self, n: Node) -> tuple:
        if n.type in ("MarkdownNote", "Note"):
            return (420, 300)
        if n.type == "CustomCombo":
            return (300, 60 + 26 * max(1, len(n.widgets) - 2))
        if n.type in ("CLIPTextEncode", "PrimitiveStringMultiline", "TextEncodeQwenImageEditPlus"):
            base = 200
        else:
            base = 30
        schema = SCHEMAS[n.type]
        n_in = len(schema["inputs"]) + len(n.widget_inputs)
        n_w = len([w for w in schema["widgets"] if w[0] not in n.widget_inputs])
        h = 34 + n_in * 22 + n_w * 26 + base
        if n.type in ("LoadImage",):
            h += 240
        if n.type in ("PreviewImage", "MaskPreview", "ImageCompare"):
            h += 220
        return (340, float(h))

    @property
    def links(self) -> list[list]:
        return [
            [l["id"], l["src"].id, l["slot"], l["dst"].id, self._input_slot_index(l["dst"], l["name"]), l["type"]]
            for l in self._link_specs
        ]

    def to_dict(self) -> dict:
        for n in self.nodes:
            n.size = self._node_size(n)
        self._layout()
        nodes_json = []
        for order, n in enumerate(self.nodes):
            schema = SCHEMAS[n.type]
            inputs = []
            for name, typ, optional in schema["inputs"]:
                entry = {"name": name, "type": typ, "link": n.inputs.get(name)}
                if typ == "*" and n.match_type:
                    entry["type"] = n.match_type
                if optional:
                    entry["shape"] = 7
                inputs.append(entry)
            for wname, wtype in schema["widgets"]:
                if wname in n.widget_inputs:
                    inputs.append(
                        {"name": wname, "type": wtype, "widget": {"name": wname}, "link": n.widget_inputs[wname]}
                    )
            outputs = []
            for slot, (oname, otype) in enumerate(schema["outputs"]):
                t = n.match_type if (otype == "*" and n.match_type) else otype
                outputs.append({"name": oname, "type": t, "slot_index": slot, "links": n.out_links.get(slot, [])})
            data = {
                "id": n.id,
                "type": n.type,
                "pos": [round(n.pos[0], 1), round(n.pos[1], 1)],
                "size": [round(n.size[0], 1), round(n.size[1], 1)],
                "flags": {},
                "order": order,
                "mode": n.mode,
                "inputs": inputs,
                "outputs": outputs,
                "properties": {"Node name for S&R": n.type},
                "widgets_values": n.widgets,
            }
            if n.type in FRONTEND_ONLY:
                data["properties"] = {}
            if n.title:
                data["title"] = n.title
            if n.color:
                data["color"] = n.color
                data["bgcolor"] = n.color
            nodes_json.append(data)

        return {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "workflowproduct/" + self.title)),
            "revision": 0,
            "last_node_id": self._next_node - 1,
            "last_link_id": self._next_link - 1,
            "nodes": nodes_json,
            "links": self.links,
            "groups": [
                {
                    "id": i + 1,
                    "title": g["title"],
                    "bounding": g["bounding"],
                    "color": g["color"],
                    "font_size": 24,
                    "flags": {},
                }
                for i, g in enumerate(self.groups)
                if g.get("bounding")
            ],
            "config": {},
            "extra": {"ds": {"scale": 0.55, "offset": [0, 0]}},
            "version": 0.4,
        }

    def _layout(self) -> None:
        """Coloca cada grupo en una banda horizontal; dentro, en columnas con salto de línea."""
        col_w, gap_x, gap_y, max_cols = 360.0, 30.0, 30.0, 7
        y = 60.0
        placed = set()
        for g in self.groups:
            members = [n for n in g["members"] if n.id not in placed]
            if not members:
                g["bounding"] = None
                continue
            x0, y0 = 60.0, y + 50.0
            cx, cy, row_h, col = x0, y0, 0.0, 0
            max_x = x0
            for n in members:
                if col >= max_cols:
                    col, cx, cy, row_h = 0, x0, cy + row_h + gap_y, 0.0
                n.pos = (cx, cy)
                placed.add(n.id)
                row_h = max(row_h, n.size[1])
                max_x = max(max_x, cx + n.size[0])
                cx += col_w + gap_x
                col += 1
            bottom = cy + row_h
            g["bounding"] = [x0 - 20, y0 - 50, (max_x - x0) + 40, (bottom - y0) + 70]
            y = bottom + 90.0
        for n in self.nodes:
            if n.id not in placed:
                n.pos = (60.0, y)
                y += n.size[1] + 30

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)
            fh.write("\n")


class _GroupCtx:
    def __init__(self, graph: Graph, title: str, color: str):
        self.graph = graph
        self.entry = {"title": title, "color": color, "members": [], "bounding": None}

    def __enter__(self):
        self.graph.groups.append(self.entry)
        self.graph._current_group = self.entry
        return self.entry

    def __exit__(self, *exc):
        self.graph._current_group = None
        return False
