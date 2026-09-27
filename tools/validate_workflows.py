#!/usr/bin/env python3
"""Valida los workflows generados.

    python3 tools/validate_workflows.py
    python3 tools/validate_workflows.py --comfyui /ruta/a/ComfyUI   # además comprueba que
                                                                    # cada tipo de nodo existe

Comprobaciones estructurales:
  * ids de nodo y de enlace únicos, y `last_node_id` / `last_link_id` coherentes
  * cada enlace apunta a un nodo y a un socket que existen, y el socket lo referencia
  * cada salida declara exactamente los enlaces que salen de ella
  * las entradas obligatorias (no opcionales) están conectadas
  * ninguna entrada obligatoria depende de un nodo en bypass o silenciado
  * `widgets_values` no excede el número de widgets del esquema
  * los tipos de origen y destino de cada enlace coinciden
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from comfy_graph import FRONTEND_ONLY, NODE_PACKS, SCHEMAS, VARIADIC_WIDGETS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOWS = os.path.join(ROOT, "workflows")


def validate_file(path: str) -> list[str]:
    errors: list[str] = []
    wf = json.load(open(path, encoding="utf-8"))

    def err(msg: str) -> None:
        errors.append(f"{os.path.basename(path)}: {msg}")

    # Los subgrafos (plantillas oficiales de ComfyUI) aparecen como nodos cuyo tipo es el id del
    # subgrafo. Su interior no se valida aquí; sí sus enlaces con el resto del grafo.
    subgraph_types = {sg["id"] for sg in (wf.get("definitions") or {}).get("subgraphs", [])}

    nodes = {}
    for n in wf["nodes"]:
        if n["id"] in nodes:
            err(f"id de nodo duplicado {n['id']}")
        nodes[n["id"]] = n
        if n["type"] not in SCHEMAS and n["type"] not in subgraph_types:
            err(f"nodo {n['id']}: tipo desconocido para el validador: {n['type']}")

    if wf["last_node_id"] < max(nodes, default=0):
        err("last_node_id menor que el id de nodo más alto")

    seen_links: dict[int, list] = {}
    for link in wf["links"]:
        lid, src_id, src_slot, dst_id, dst_slot, ltype = link
        if lid in seen_links:
            err(f"id de enlace duplicado {lid}")
        seen_links[lid] = link
        if src_id not in nodes:
            err(f"enlace {lid}: nodo origen {src_id} inexistente")
            continue
        if dst_id not in nodes:
            err(f"enlace {lid}: nodo destino {dst_id} inexistente")
            continue
        src, dst = nodes[src_id], nodes[dst_id]
        outs = src.get("outputs") or []
        if src_slot >= len(outs):
            err(f"enlace {lid}: {src['type']} no tiene salida {src_slot}")
            continue
        if lid not in (outs[src_slot].get("links") or []):
            err(f"enlace {lid}: la salida {src['type']}.{src_slot} no lo declara")
        ins = dst.get("inputs") or []
        if dst_slot >= len(ins):
            err(f"enlace {lid}: {dst['type']} no tiene entrada {dst_slot}")
            continue
        if ins[dst_slot].get("link") != lid:
            err(f"enlace {lid}: la entrada {dst['type']}.{ins[dst_slot]['name']} apunta a {ins[dst_slot].get('link')}")
        out_type, in_type = outs[src_slot].get("type"), ins[dst_slot].get("type")
        # una entrada puede aceptar varios tipos separados por comas (p. ej. "IMAGE,MASK")
        if out_type not in str(in_type).split(",") and "*" not in (out_type, in_type):
            err(f"enlace {lid}: tipos incompatibles {src['type']}.{out_type} -> {dst['type']}.{in_type}")
        if ltype != out_type:
            err(f"enlace {lid}: tipo declarado {ltype} != tipo de la salida {out_type}")

    if wf["last_link_id"] < max(seen_links, default=0):
        err("last_link_id menor que el id de enlace más alto")

    # Un nodo en bypass (mode 4) sólo deja pasar una entrada del mismo tipo que su salida; si no
    # la tiene, la salida desaparece. Uno silenciado (mode 2) nunca produce nada. Si lo que
    # desaparece alimenta una entrada obligatoria, ComfyUI se niega a ejecutar el workflow.
    optional_inputs = {
        (t, i[0]) for t, sch in SCHEMAS.items() for i in sch["inputs"] if i[2]
    }
    # Una entrada de subgrafo es opcional si todo lo que alimenta dentro son entradas opcionales.
    for sg in (wf.get("definitions") or {}).get("subgraphs", []):
        inner = {n["id"]: n for n in sg.get("nodes", [])}
        inner_links = {l["id"]: l for l in sg.get("links", []) if isinstance(l, dict)}
        for sg_in in sg.get("inputs", []):
            targets = []
            for lid in sg_in.get("linkIds") or []:
                l = inner_links.get(lid)
                if not l or l["target_id"] not in inner:
                    continue
                tn = inner[l["target_id"]]
                tin = (tn.get("inputs") or [])[l["target_slot"]]
                targets.append((tn["type"], tin.get("name")))
            if targets and all(t in optional_inputs for t in targets):
                optional_inputs.add((sg["id"], sg_in["name"]))
    for link in wf["links"]:
        lid, src_id, src_slot, dst_id, dst_slot, ltype = link
        src, dst = nodes.get(src_id), nodes.get(dst_id)
        if not src or not dst or src.get("mode", 0) not in (2, 4):
            continue
        if (dst["type"], (dst.get("inputs") or [{}])[dst_slot].get("name")) in optional_inputs:
            continue
        if src.get("mode") == 4 and any(i.get("type") == ltype for i in (src.get("inputs") or [])):
            continue  # el bypass puede dejar pasar una entrada del mismo tipo
        estado = "silenciado" if src.get("mode") == 2 else "en bypass"
        err(f"enlace {lid}: {src['type']} ({estado}) alimenta la entrada obligatoria "
            f"'{(dst.get('inputs') or [{}])[dst_slot].get('name')}' de {dst['type']}")

    for n in wf["nodes"]:
        schema = SCHEMAS.get(n["type"])
        if not schema:
            continue
        declared = {i["name"]: i for i in (n.get("inputs") or [])}
        for name, _typ, optional in schema["inputs"]:
            if name not in declared:
                if not optional:  # las opcionales (p. ej. huecos autogrow) pueden no guardarse
                    err(f"nodo {n['id']} ({n['type']}): falta la entrada '{name}'")
            elif not optional and declared[name].get("link") is None:
                err(f"nodo {n['id']} ({n['type']}): entrada obligatoria '{name}' sin conectar")
        if (n["type"] not in VARIADIC_WIDGETS
                and len(n.get("widgets_values") or []) > len(schema["widgets"])):
            err(f"nodo {n['id']} ({n['type']}): {len(n['widgets_values'])} valores para "
                f"{len(schema['widgets'])} widgets")
        for inp in n.get("inputs") or []:
            if inp.get("link") is not None and inp["link"] not in seen_links:
                err(f"nodo {n['id']} ({n['type']}): entrada '{inp['name']}' apunta al enlace inexistente {inp['link']}")
        for out in n.get("outputs") or []:
            for lid in out.get("links") or []:
                if lid not in seen_links:
                    err(f"nodo {n['id']} ({n['type']}): salida '{out['name']}' declara el enlace inexistente {lid}")

    return errors


def check_node_types_exist(comfyui: str) -> list[str]:
    """Comprueba que cada tipo de nodo usado existe en el código de ComfyUI."""
    sources = []
    for rel in ["nodes.py"]:
        p = os.path.join(comfyui, rel)
        if os.path.isfile(p):
            sources.append(open(p, encoding="utf-8", errors="ignore").read())
    for sub in ("comfy_extras", "comfy_api_nodes"):
        d = os.path.join(comfyui, sub)
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".py"):
                    sources.append(open(os.path.join(d, f), encoding="utf-8", errors="ignore").read())
    blob = "\n".join(sources)
    known = set(re.findall(r'node_id\s*=\s*"([A-Za-z0-9_]+)"', blob))
    known |= set(re.findall(r'"([A-Za-z0-9_]+)"\s*:\s*[A-Za-z_][A-Za-z0-9_]*\s*,', blob))
    missing = []
    for t in sorted(SCHEMAS):
        if t in FRONTEND_ONLY or t in NODE_PACKS:
            continue  # los de paquetes de terceros no están en el núcleo
        if t not in known:
            missing.append(f"tipo de nodo no encontrado en el código de ComfyUI: {t}")
    return missing


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--comfyui", help="ruta a un clon de ComfyUI para verificar los tipos de nodo")
    args = ap.parse_args()

    errors: list[str] = []
    files = sorted(f for f in os.listdir(WORKFLOWS) if f.endswith(".json"))
    if not files:
        print("no hay workflows que validar", file=sys.stderr)
        return 1
    for f in files:
        errs = validate_file(os.path.join(WORKFLOWS, f))
        errors += errs
        print(f"{'FALLO' if errs else '  ok '}  {f}")
    if args.comfyui:
        errors += check_node_types_exist(args.comfyui)

    for e in errors:
        print("  -", e, file=sys.stderr)
    print(f"\n{len(files)} workflows, {len(errors)} problemas")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
