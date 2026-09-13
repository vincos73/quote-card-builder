#!/usr/bin/env python3
"""Small heuristic comparison of Cover across three fictional identities."""
from pathlib import Path
import json, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render_quote_card as proof
import rasterize
import inspect_render

OUT = ROOT / "output/cover-identity-test"
TEXT = "Le idee prendono forma quando inizi a sperimentare."
LINES = ["Le idee prendono", "forma quando", "inizi a", "sperimentare."]
FONT_DIR = Path("/System/Library/Fonts/Supplemental")
PROFILES = [
    ("studio-editoriale", "Studio editoriale", "#F3EBDD", "#241E1A", "#C85A2B", "Georgia", "Georgia.ttf", "Georgia Bold.ttf"),
    ("laboratorio-digitale", "Laboratorio digitale", "#101C36", "#FFFFFF", "#28D7E8", "Arial", "Arial.ttf", "Arial Bold.ttf"),
    ("atelier-botanico", "Atelier botanico", "#F2EBDD", "#183D2B", "#B65C3A", "Trebuchet MS", "Trebuchet MS.ttf", "Trebuchet MS Bold.ttf"),
]

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cards = []
    for slug, name, bg, primary, accent, family, regular, bold in PROFILES:
        for seed in range(3):
            data = {"schema_version":"0.2", "state":"contenuto_approvato", "content":{"text":TEXT,"lines":LINES,"transformation":"AI_GENERATED","evidence_status":"UNVERIFIED","use_quotation_marks":False,"emphasis":"","styles":[],"styles_customized":False,"attribution":{"label":name.upper(),"role":"author"},"alt_text":""}, "direction":"editorial", "presentation":{"logo_mode":"hidden","graphic_mode":"auto","graphic_variant":"cover","graphic_seed":seed}, "canvas":{"width":1440,"height":1800}, "brand":{"name":name,"colors":{"primary":primary,"accent":accent,"background":bg,"text":primary},"font":{"family":family,"regular_path":str(FONT_DIR/regular),"bold_path":str(FONT_DIR/bold)}}, "source":{"label":"Test dimostrativo"}}
            svg = proof.render_svg(data, ROOT / "scripts", "editorial", render_options=data["presentation"])
            defects = inspect_render.inspect_render(svg, "editorial", 1440, 1800)
            if defects: raise RuntimeError(f"{name} seed {seed}: {defects}")
            stem = f"{slug}-seed-{seed}"
            svg_path = OUT / (stem + ".svg"); svg_path.write_text(svg, encoding="utf-8")
            png_path = OUT / (stem + ".png")
            rasterize.rasterize(svg_path, png_path, 1440, 1800, node=Path("/Users/vincos/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"), node_modules=Path("/Users/vincos/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules"))
            svg_path.unlink()
            cards.append((name, seed, png_path))
    # 3 columns (identity), 3 rows (shared seed), labels remain outside cards.
    cell_w, cell_h, label_h = 480, 600, 66
    sheet = Image.new("RGB", (3*cell_w, 3*(cell_h+label_h)), "#D8D2C7")
    draw = ImageDraw.Draw(sheet)
    label_font = ImageFont.truetype(str(FONT_DIR/"Arial.ttf"), 22)
    for i, (name, seed, path) in enumerate(cards):
        # cards are generated profile-major; the board is identity columns x seed rows.
        col, row = i // 3, i % 3
        x, y = col*cell_w, row*(cell_h+label_h)
        thumb = Image.open(path).convert("RGB"); thumb.thumbnail((cell_w, cell_h))
        sheet.paste(thumb, (x, y+label_h))
        draw.text((x+14, y+12), f"{name} · seed {seed}", fill="#171717", font=label_font)
    sheet.save(OUT / "cover-identity-test-board.png")
    (OUT / "review-manifest.json").write_text(json.dumps({"text":TEXT,"direction":"editorial","graphic_variant":"cover","seeds":[0,1,2],"identities":[p[1] for p in PROFILES],"cards":9}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (OUT / "README.md").write_text("""# Cover identity test\n\nProva visiva euristica: nove card con la stessa frase, composizione, direzione `editorial`, motivo `presentation.graphic_variant=cover` e seed condivisi 0, 1, 2.\n\nProfili fittizi: **Studio editoriale** (crema, inchiostro, arancio, Georgia); **Laboratorio digitale** (blu notte, bianco, ciano, Arial); **Atelier botanico** (avorio, verde bosco, terracotta, Trebuchet MS). I colori sono pieni e il contrasto del testo è almeno 4.5:1.\n\nValutazione: il confronto serve a osservare se le tre serie si distinguono mantenendo coerenza interna; è una verifica visiva euristica, senza validazione con utenti. Limiti: una sola frase, un solo formato e un singolo motivo; non misura riconoscibilità nel tempo o in feed reali.\n""", encoding="utf-8")
    print(f"created {len(cards)} cards and board in {OUT}")
if __name__ == "__main__": main()
