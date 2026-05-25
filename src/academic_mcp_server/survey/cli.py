from __future__ import annotations

import argparse
import json
from pathlib import Path

from academic_mcp_server.survey.analysis import analyze_corpus
from academic_mcp_server.survey.enrich import enrich_crossref
from academic_mcp_server.survey.generate import generate_docs

SURVEY_CONFIG_SCHEMA = """
survey_config.json example:
{
  "survey_name": "inFlight_InductivePowerTransfer",
  "target_word": "in-flight IPT",
  "article_number": 290,
  "ledger_number": 291,
  "vault_root": "/home/user/Obsidian",
  "vault_survey_dir": "/home/user/Obsidian/02_HFLab/00_Idea/Survey/MySurvey",
  "python_survey_dir": "/home/user/00_kotaprivate/Program/python_ForObsidian/vault_mirror/02_HFLab/00_Idea/Survey/MySurvey",
  "shared_python_dir": "/home/user/00_kotaprivate/Program/python_ForObsidian/vault_mirror/.python/survey",
  "tags": ["survey", "HFLab"],
  "ledger_tags": ["survey", "HFLab", "ledger"]
}
""".strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Literature survey mirror workflow CLI", epilog=SURVEY_CONFIG_SCHEMA, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_enrich = sub.add_parser("enrich", help="Crossref/OpenAlex enrich for DOI entries")
    p_enrich.add_argument("mirror_dir", type=Path)
    p_enrich.add_argument("--scope", choices=["strong", "all", "collection"], default="strong")


    p_an = sub.add_parser("analyze", help="Quantitative corpus analysis")
    p_an.add_argument("mirror_dir", type=Path)

    p_gen = sub.add_parser("generate", help="Generate Obsidian article and ledger")
    p_gen.add_argument("mirror_dir", type=Path)

    args = parser.parse_args()
    mirror = args.mirror_dir.expanduser().resolve()

    if args.command == "enrich":
        result = enrich_crossref(mirror, scope=args.scope)
        print(json.dumps(result, ensure_ascii=False))
    elif args.command == "analyze":
        result = analyze_corpus(mirror)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "generate":
        result = generate_docs(mirror)
        print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
