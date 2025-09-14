#!/usr/bin/env python3
import os, sys, argparse, json, time, math, re
from pathlib import Path
from dotenv import load_dotenv

# Optional text extraction for docx/pdf
def read_text(path: Path) -> str:
    p = str(path)
    if p.lower().endswith(".docx"):
        import docx2txt
        return docx2txt.process(p) or ""
    if p.lower().endswith(".pdf"):
        from PyPDF2 import PdfReader
        reader = PdfReader(p)
        return "\n".join([page.extract_text() or "" for page in reader.pages])
    return path.read_text(encoding="utf-8")

def chunk(text, max_chars=12000, overlap=500):
    # Soft chunk by paragraphs
    parts = []
    buf = []
    size = 0
    for para in re.split(r"\n{2,}", text):
        if size + len(para) + 2 > max_chars and buf:
            parts.append("\n\n".join(buf))
            buf = [para]
            size = len(para) + 2
        else:
            buf.append(para)
            size += len(para) + 2
    if buf:
        parts.append("\n\n".join(buf))
    # add small overlaps
    out = []
    for i, p in enumerate(parts):
        if i == 0:
            out.append(p)
        else:
            prev = parts[i-1]
            overlap_text = prev[-overlap:]
            out.append(overlap_text + "\n\n" + p)
    return out

def build_messages(defs, template_text, tiltak_text, lang="no", project_meta=None):
    system = {
        "role": "system",
        "content": (
            "Du er en norsk fagkonsulent i ROS (risiko- og sårbarhetsanalyser). "
            "Følg DSB-veiledere og prosjektets mal. Lever bare det ferdige dokumentet, "
            "strukturert etter malen. Vær presis og sporbar."
        ),
    }
    dev = {
        "role": "developer",
        "content": json.dumps({
            "definitions": defs.get("terms", {}),
            "style_guidance": defs.get("style_guidance", []),
            "risk_matrix": defs.get("risk_matrix", {}),
            "language": lang,
            "template_hint": "Fyll ut alle seksjoner i malen. Der det mangler data: skriv 'TBD' og hva som kreves."
        }, ensure_ascii=False)
    }
    user_intro = {
        "role": "user",
        "content": (
            "Her er ROS-malen som skal fylles ut, etterfulgt av tiltaksanalysen. "
            "Analyser tiltaksanalysen, identifiser relevante farer og sårbarheter, "
            "og produser en komplett ROS-rapport som følger malen."
        ),
    }
    template_msg = {"role": "user", "content": f"=== MAL START ===\n{template_text}\n=== MAL SLUTT ==="}
    # chunk tiltak
    chunks = chunk(tiltak_text, max_chars=12000)
    chunk_msgs = [
        {"role": "user", "content": f"[TILTAKSANALYSE DEL {i+1}/{len(chunks)}]\n{c}"}
        for i, c in enumerate(chunks)
    ]
    # Final instruction
    final = {
        "role": "user",
        "content": (
            "Lag nå den ferdige ROS‑analysen i Markdown, på norsk, etter malen. "
            "Ta med risikomatrise(r) og tabell for tiltak med ansvar, frist og status."
        ),
    }
    msgs = [system, dev, user_intro, template_msg] + chunk_msgs + [final]
    if project_meta:
        msgs.insert(2, {"role": "user", "content": f"Prosjektmetadata: {json.dumps(project_meta, ensure_ascii=False)}"})
    return msgs

def main():
    ap = argparse.ArgumentParser(description="Generer ROS‑analyse fra tiltaksanalyse + mal")
    ap.add_argument("--tiltak", required=True, help="Filsti til tiltaksanalyse (TXT/MD/DOCX/PDF)")
    ap.add_argument("--template", required=True, help="Filsti til ROS‑mal (MD)")
    ap.add_argument("--definitions", default="prompts/definitions.no.json", help="Filsti til definisjoner (JSON)")
    ap.add_argument("--lang", default="no", help="Språk (no/en)")
    ap.add_argument("--out", required=True, help="Utfil (MD)")
    ap.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4o"), help="Modellnavn")
    ap.add_argument("--base_url", default=os.getenv("OPENAI_BASE_URL", ""), help="Tilpasset base URL (valgfri)")
    args = ap.parse_args()

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY mangler (sett i .env).", file=sys.stderr)
        sys.exit(2)

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=args.base_url or None)

    defs = json.loads(Path(args.definitions).read_text(encoding="utf-8"))
    template_text = Path(args.template).read_text(encoding="utf-8")
    tiltak_text = read_text(Path(args.tiltak))

    msgs = build_messages(defs, template_text, tiltak_text, lang=args.lang)

    # Call Chat Completions (works across providers using OpenAI SDK)
    resp = client.chat.completions.create(
        model=args.model,
        messages=msgs,
        temperature=0.2,
    )
    content = resp.choices[0].message.content

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    print(f"Wrote: {out_path}")

if __name__ == "__main__":
    main()
