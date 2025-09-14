# ROS‑analyse Generator (Code‑Cloud friendly)

This repo lets you (or a cloud IDE you call “codecloud”) send a *tiltaksanalyse* + a template to an LLM (OpenAI) and get back a structured **ROS‑analyse** in Norwegian.

## Quick start (works in any cloud IDE or locally)

1. **Create a workspace** (Codespaces, Codeanywhere, Coder, etc.).
2. **Download this repo** or clone it, then put your *tiltaksanalyse* file into `data/` (TXT/MD/DOCX/PDF supported via text extraction; MD/TXT recommended).
3. Copy `.env.example` to `.env` and set `OPENAI_API_KEY=...`.
4. (Optional) Edit `prompts/definitions.no.json` and `templates/ros_template.no.md` to fit your org.
5. Install deps and run:
   ```bash
   pip install -r requirements.txt
   python src/ros_gen.py --tiltak data/tiltaksanalyse.sample.no.md --template templates/ros_template.no.md --out out/ROS-rapport.md
   ```
6. Your generated ROS‑analyse appears in `out/`.

> Tip: You can wire this into your CI, or have your “codecloud” agent call `ros_gen.py` after committing new inputs.

## Repo layout

```
ros-pipeline/
├─ data/                    # Put your own tiltaksanalyse files here
├─ templates/               # ROS template(s)
├─ prompts/                 # Domain definitions & guardrails
├─ src/                     # Scripts
├─ out/                     # Generated output
└─ README.md
```

## Notes

- The script **chunks large files** and streams them to the model to avoid token limits.
- Output follows your template sections closely and includes a risk matrix if requested.
- Everything is **Norwegian-first** (prompts and examples), but you can switch language via `--lang`.
