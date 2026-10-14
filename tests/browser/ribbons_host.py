"""Isolated localhost editor smoke host; no remote host or Codex handoff."""
import argparse
import json
import os
from pathlib import Path
import sys
import shutil

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path, required=True, help='Fresh isolated fixture and evidence directory')
parser.add_argument('--port', type=int, default=0)
parser.add_argument('--node', type=Path, help='Node with Playwright available')
parser.add_argument('--node-modules', type=Path, help='Package directory containing Playwright and sharp')
parser.add_argument('--brand-assets', type=Path, help='Optional v05 assets directory; defaults to committed Barlow and Vincos logo')
args = parser.parse_args()
OUT = args.output_dir.expanduser().resolve()
sys.path.insert(0, str(ROOT / "scripts"))
import card_review_server as SERVER
from visual_grammars import normalize_composition

text = "La tecnologia apre nuove possibilità. Il valore nasce dalle persone che sanno scegliere quali esplorare e come trasformarle in qualcosa di utile."
base = {
    "version": 1, "background_role": "background", "text_role": "text",
    "highlight_role": "accent", "logo_box": {"x": .07, "y": .925, "width": .18, "height": .035},
}
def box(x, y, width, height): return dict(x=x, y=y, width=width, height=height)
def ribbon(id, role, width, points): return dict(id=id, color_role=role, width_ratio=width, points=points)
compositions = [
    {**base, "id": "qa-high-weave", "name": "Intreccio alto",
     "quote_box": box(.08,.35,.84,.40), "author_box": box(.08,.80,.70,.08),
     "ribbons": [
         ribbon("blue", "primary", .12, [[-.12,.05],[.11,.35],[.35,-.02],[.49,.12],[.68,.35],[.85,.06],[1.12,.17]]),
         ribbon("pink", "accent", .095, [[-.10,.21],[.10,.03],[.43,.40],[.61,.20],[.76,-.01],[1.11,.11],[1.01,.32]]),
     ], "crossings": [{"over":"pink","under":"blue","segment":0,"t":.72}]},
    {**base, "id": "qa-side-loops", "name": "Anse laterali",
     "quote_box": box(.27,.12,.64,.53), "author_box": box(.27,.70,.57,.12),
     "ribbons": [
         ribbon("blue", "primary", .105, [[-.12,.05],[.27,.02],[.07,.33],[.12,.49],[.16,.67],[.58,.54],[.66,.77],[.72,1.01],[.28,1.13],[.12,.94]]),
         ribbon("pink", "accent", .08, [[1.12,.29],[.71,.21],[.90,.59],[.85,.71],[.78,.90],[.30,.70],[.14,.86],[.02,.98],[.48,1.02],[.65,1.09]]),
     ], "crossings": [{"over":"blue","under":"pink","segment":1,"t":.70}]},
    {**base, "id": "qa-bottom-loops", "name": "Nastri sul bordo",
     "quote_box": box(.08,.10,.84,.44), "author_box": box(.08,.59,.70,.10),
     "ribbons": [
         ribbon("blue", "primary", .13, [[-.13,.80],[.10,.51],[.47,1.13],[.67,.83],[.88,.50],[1.15,.80],[1.12,1.12]]),
         ribbon("pink", "accent", .09, [[-.11,1.03],[.19,.88],[.29,.58],[.46,.83],[.66,1.12],[.95,.83],[1.12,.74]]),
     ], "crossings": [{"over":"pink","under":"blue","segment":1,"t":.60}]},
]
compositions = [normalize_composition(value) for value in compositions]
if args.brand_assets:
    brand = args.brand_assets.expanduser().resolve()
    fonts = {key:str(brand / "fonts/barlow" / name) for key,name in {
        "regular_path":"Barlow-Regular.ttf", "medium_path":"Barlow-Medium.ttf",
        "bold_path":"Barlow-Bold.ttf", "italic_path":"Barlow-Italic.ttf"}.items()}
    logo = {"dark_path":str(brand / "logo/vincos-lockup-navy.svg"), "light_path":str(brand / "logo/vincos-lockup-white.svg")}
    colors = {"primary":"#3524FF", "accent":"#FF47CA", "background":"#DAFF00", "text":"#072743"}
else:
    fonts = {"regular_path":str(ROOT / "assets/card-editor/fonts/Barlow-Regular.ttf"),
             "bold_path":str(ROOT / "assets/card-editor/fonts/Barlow-Bold.ttf")}
    logo = {"light_path":str(ROOT / "assets/card-editor/vincos-lockup-white.svg")}
    colors = {"primary":"#3524FF", "accent":"#FF47CA", "background":"#072743", "text":"#DAFF00"}
missing = [value for value in [*fonts.values(), *logo.values()] if not Path(value).is_file()]
if missing:
    parser.error('Required embedded brand assets are missing: ' + ', '.join(missing))
manifest = {
    "schema_version":"0.4", "state":"contenuto_approvato", "revision":1,
    "content": {"text":text, "transformation":"AI_GENERATED", "evidence_status":"USER_SUPPLIED",
                "emphasis":"", "styles":[], "styles_customized":True,
                "attribution":{"label":"Autore dimostrativo", "role":"author"}},
    "direction":"editorial",
    "presentation": {"logo_mode":"auto", "graphic_mode":"auto", "graphic_variant":"default",
                     "output_mode":"4x5", "visual_grammar":"ribbons", "composition":compositions[0]},
    "composition_candidates":compositions, "proposal_source":"model",
    "formats":[{"id":"4x5", "width":1440, "height":1800, "lines":[text], "text_scale":1, "vertical_position":"center"}],
    "brand": {"name":"Vincos — palette sperimentale v05",
              "colors":colors, "font":{"family":"Barlow", **fonts}, "logo":logo},
    "source":{"title":"Test locale Nastri", "locator":"user://nastri-smoke"},
    "output":{"basename":"vincos-nastri-smoke"},
}
if OUT.exists() and any(OUT.iterdir()):
    parser.error('Use a fresh empty output directory; existing projects and stores must stay untouched.')
OUT.mkdir(parents=True, exist_ok=True)
manifest_path = OUT / "manifest.json"
if manifest_path.exists():
    parser.error('Use a fresh output directory; this test must not replace an existing project.')
SERVER.atomic_write_json(manifest_path, manifest)
os.environ["QUOTE_CARD_CODEX_BIN"] = str(OUT / "codex-handoff-disabled")
node = args.node or (Path(shutil.which('node')) if shutil.which('node') else None)
modules = args.node_modules
if modules is None:
    modules = next((Path(value) for value in os.environ.get('NODE_PATH','').split(os.pathsep)
                    if value and (Path(value) / 'playwright').is_dir()), None)
server, token = SERVER.create_server(manifest_path, OUT / "session", args.port, node, modules,
                                    profile_store=OUT / "profiles.json", style_store=OUT / "styles.json")
ready = {"url":f"http://127.0.0.1:{server.server_address[1]}/?token={token}", "handoff":"disabled"}
SERVER.atomic_write_json(OUT / "ready.json", ready)
print(json.dumps(ready), flush=True)
try: server.serve_forever(poll_interval=.25)
except KeyboardInterrupt: pass
finally: server.server_close()
