#!/usr/bin/env python3
"""
convert_interview.py
────────────────────
Converts SAP Experience Garage synthetic interview transcripts (.docx)
into the canonical S3 bronze JSON schema expected by the recommendation
engine's extract_node.

Usage
-----
  # Single file
  python convert_interview.py transcript.docx

  # Specific output path
  python convert_interview.py transcript.docx --out interviews/out.json

  # Batch — entire folder
  python convert_interview.py --batch ./transcripts/ --out-dir ./json_out/

  # Upload directly to S3 after conversion
  python convert_interview.py transcript.docx --s3-bucket market-trend-exp2

  # Batch + S3
  python convert_interview.py --batch ./transcripts/ --s3-bucket market-trend-exp2

Output schema (matches Interview1_Priya_SideProjectSolver.json)
--------------------------------------------------------------
{
  "interview_id":          "<stem>_<YYYYMMDD>",
  "source_file":           "filename.docx",
  "title":                 "Synthetic User Interview — Transcript",
  "project":               "SAP Experience Garage — AI Platform Innovation ...",
  "synthetic_research_note": "...",
  "metadata": {
    "date":        "[redacted] | YYYY-MM-DD",
    "duration":    "31 min 08 sec",
    "format":      "MS Teams video ...",
    "moderator":   "...",
    "participant": {
      "name":         "...",
      "role":         "...",
      "persona_type": "..."
    }
  },
  "stats": {
    "block_count":       7,
    "total_turns":       81,
    "moderator_turns":   41,
    "participant_turns": 40
  },
  "blocks": [
    {
      "name":  "Warm-up",
      "turns": [
        {
          "speaker":       "moderator | participant",
          "speaker_code":  "M | P",
          "text":          "...",
          "stage_directions": ["laughs", "pauses", ...]
        }
      ]
    }
  ],
  "end_of_transcript": "End of transcript — 31:08"
}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from docx import Document

# ──────────────────────────────────────────────────────────────────────────────
# Regexes
# ──────────────────────────────────────────────────────────────────────────────

# Matches stage directions like "(laughs)" or "(pauses, choosing words)"
STAGE_DIR_RE = re.compile(r"\(([^)]+)\)")

# Matches a speaker prefix at the start of a line, e.g. "M:" or "P:"
SPEAKER_RE = re.compile(r"^([A-Z])\s*:\s*(.*)", re.DOTALL)

# Matches a block heading like "Block 1 — Discovery & Navigation" or "Warm-up"
BLOCK_RE = re.compile(r"^(warm-?up|block\s+\d+\s*[—–-].*|closing)", re.IGNORECASE)

# Metadata key patterns
META_PATTERNS = {
    "date":     re.compile(r"^date\s*:", re.IGNORECASE),
    "duration": re.compile(r"^duration\s*:", re.IGNORECASE),
    "format":   re.compile(r"^format\s*:", re.IGNORECASE),
    "moderator":re.compile(r"^moderator\s*\([^)]*\)\s*:", re.IGNORECASE),
    "participant_name": re.compile(
        r"^participant\s*\([^)]*\)\s*:\s*(.+?)\s*[—–-]", re.IGNORECASE
    ),
    "participant_role": re.compile(
        r"^participant\s*\([^)]*\)\s*:\s*.+?[—–-]\s*(.+)", re.IGNORECASE
    ),
    "persona_type": re.compile(r"^persona\s+type\s*:", re.IGNORECASE),
}

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _extract_stage_directions(text: str) -> tuple[str, list[str]]:
    """
    Remove stage directions from text and return them separately.
    "(laughs)" → stage_directions=["laughs"], removed from text.
    Multi-direction parens like "(pauses, choosing words)" → ["pauses, choosing words"].
    """
    directions = [m.group(1).strip() for m in STAGE_DIR_RE.finditer(text)]
    clean = STAGE_DIR_RE.sub("", text).strip()
    # Collapse multiple spaces left by removal
    clean = re.sub(r"  +", " ", clean).strip()
    return clean, directions


def _clean_value(raw: str) -> str:
    """Strip leading key prefix and surrounding whitespace from a metadata value."""
    # Remove everything up to and including the first ':'
    if ":" in raw:
        raw = raw.split(":", 1)[1]
    return raw.strip()


def _parse_metadata(paragraphs: list[str]) -> dict:
    """
    Scan the header section (before the first block heading) for metadata fields.
    Returns a metadata dict matching the target schema.
    """
    meta: dict = {
        "date": "",
        "duration": "",
        "format": "",
        "moderator": "",
        "participant": {
            "name": "",
            "role": "",
            "persona_type": "",
        },
    }

    for para in paragraphs:
        p = para.strip()

        if META_PATTERNS["date"].match(p):
            meta["date"] = _clean_value(p)

        elif META_PATTERNS["duration"].match(p):
            meta["duration"] = _clean_value(p)

        elif META_PATTERNS["format"].match(p):
            meta["format"] = _clean_value(p)

        elif META_PATTERNS["moderator"].match(p):
            meta["moderator"] = _clean_value(p)

        elif META_PATTERNS["persona_type"].match(p):
            meta["participant"]["persona_type"] = _clean_value(p)

        elif re.match(r"^participant\s*\([^)]*\)\s*:", p, re.IGNORECASE):
            # e.g. "Participant (P): Priya Raghavan — Developer, SAP Cloud ERP..."
            body = _clean_value(p)
            # Split on em-dash / en-dash / hyphen surrounded by spaces
            parts = re.split(r"\s*[—–-]\s*", body, maxsplit=1)
            if parts:
                meta["participant"]["name"] = parts[0].strip()
            if len(parts) > 1:
                meta["participant"]["role"] = parts[1].strip()

    return meta


def _parse_blocks(paragraphs: list[str]) -> list[dict]:
    """
    Walk paragraphs after the header section, identify block headings and
    speaker turns, and return structured blocks.
    """
    blocks: list[dict] = []
    current_block: dict | None = None
    in_body = False  # True once we've passed the header/metadata section

    for para in paragraphs:
        p = para.strip()
        if not p:
            continue

        # Detect block headings (also marks end of header section)
        if BLOCK_RE.match(p):
            in_body = True
            if current_block is not None:
                blocks.append(current_block)
            current_block = {"name": p, "turns": []}
            continue

        # Skip header/metadata lines
        if not in_body:
            continue

        # Detect "End of transcript" line
        if re.match(r"^end of transcript", p, re.IGNORECASE):
            # Stash for later; don't add as a turn
            if current_block is not None:
                blocks.append(current_block)
                current_block = None
            break

        # Detect speaker turn
        m = SPEAKER_RE.match(p)
        if m and current_block is not None:
            code = m.group(1).upper()
            raw_text = m.group(2).strip()
            clean_text, directions = _extract_stage_directions(raw_text)
            speaker = "moderator" if code == "M" else "participant"
            current_block["turns"].append(
                {
                    "speaker": speaker,
                    "speaker_code": code,
                    "text": clean_text,
                    "stage_directions": directions,
                }
            )

    # Flush last block if loop ended without break
    if current_block is not None:
        blocks.append(current_block)

    return blocks


def _find_end_of_transcript(paragraphs: list[str]) -> str:
    for p in paragraphs:
        if re.match(r"^end of transcript", p.strip(), re.IGNORECASE):
            return p.strip()
    return "End of transcript"


def _count_stats(blocks: list[dict]) -> dict:
    total = sum(len(b["turns"]) for b in blocks)
    mod = sum(
        1 for b in blocks for t in b["turns"] if t["speaker_code"] == "M"
    )
    part = sum(
        1 for b in blocks for t in b["turns"] if t["speaker_code"] != "M"
    )
    return {
        "block_count": len(blocks),
        "total_turns": total,
        "moderator_turns": mod,
        "participant_turns": part,
    }


def _extract_header_fields(paragraphs: list[str]) -> tuple[str, str, str]:
    """
    Return (title, project, synthetic_research_note) from the document header.
    The title is typically the first non-empty paragraph,
    project is second, and the note is the longer disclaimer paragraph.
    """
    title = ""
    project = ""
    note = ""
    non_empty = [p.strip() for p in paragraphs if p.strip()]

    for i, p in enumerate(non_empty):
        if not title and "transcript" in p.lower():
            title = p
        elif not project and "SAP Experience Garage" in p and "AI Platform" in p:
            project = p
        elif not note and ("synthetic" in p.lower() or "persona" in p.lower()):
            note = p

    return title, project, note


# ──────────────────────────────────────────────────────────────────────────────
# Core converter
# ──────────────────────────────────────────────────────────────────────────────

def convert(docx_path: Path) -> dict:
    """
    Parse a .docx interview transcript and return the canonical JSON dict.
    """
    doc = Document(str(docx_path))
    paragraphs = [p.text for p in doc.paragraphs]

    title, project, note = _extract_header_fields(paragraphs)
    metadata = _parse_metadata(paragraphs)
    blocks = _parse_blocks(paragraphs)
    stats = _count_stats(blocks)
    end_line = _find_end_of_transcript(paragraphs)

    # Build interview_id: stem + today's date
    stem = re.sub(r"\s+", "_", docx_path.stem)
    interview_id = f"{stem}_{date.today().strftime('%Y%m%d')}"

    return {
        "interview_id": interview_id,
        "source_file": docx_path.name,
        "title": title,
        "project": project,
        "synthetic_research_note": note,
        "metadata": metadata,
        "stats": stats,
        "blocks": blocks,
        "end_of_transcript": end_line,
    }


# ──────────────────────────────────────────────────────────────────────────────
# S3 upload (optional — only imported when --s3-bucket is passed)
# ──────────────────────────────────────────────────────────────────────────────

def upload_to_s3(local_path: Path, bucket: str) -> None:
    """
    Upload a converted JSON file to the S3 bronze interviews prefix.
    Path pattern: bronze/interviews/dt=YYYY-MM-DD/<filename>
    Requires boto3 and valid AWS credentials (env, profile, or IAM role).
    """
    try:
        import boto3  # type: ignore
    except ImportError:
        print(
            "boto3 not installed. Run: pip install boto3\n"
            "Skipping S3 upload — file saved locally.",
            file=sys.stderr,
        )
        return

    today = date.today().strftime("%Y-%m-%d")
    key = f"bronze/interviews/dt={today}/{local_path.name}"

    s3 = boto3.client("s3")
    s3.upload_file(str(local_path), bucket, key)
    print(f"  ✓ Uploaded → s3://{bucket}/{key}")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def _process_one(
    docx_path: Path,
    out_path: Path | None,
    s3_bucket: str | None,
) -> Path:
    """Convert one file, write JSON, optionally upload. Returns the output path."""
    print(f"Converting: {docx_path.name}")
    record = convert(docx_path)

    if out_path is None:
        out_path = docx_path.with_suffix(".json")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    print(f"  ✓ Written  → {out_path}")

    if s3_bucket:
        upload_to_s3(out_path, s3_bucket)

    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert SAP Experience Garage interview .docx files to JSON."
    )
    # Input — mutually exclusive: single file vs batch folder
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "docx",
        nargs="?",
        metavar="TRANSCRIPT.docx",
        help="Single .docx transcript to convert.",
    )
    input_group.add_argument(
        "--batch",
        metavar="FOLDER",
        help="Folder of .docx files to convert in bulk.",
    )
    # Output
    parser.add_argument(
        "--out",
        metavar="OUTPUT.json",
        help="Output path for single-file mode (default: same name as input, .json).",
    )
    parser.add_argument(
        "--out-dir",
        metavar="FOLDER",
        help="Output folder for batch mode (default: same folder as input).",
    )
    # S3
    parser.add_argument(
        "--s3-bucket",
        metavar="BUCKET",
        help="S3 bucket name. If set, uploads each JSON to bronze/interviews/dt=TODAY/.",
    )

    args = parser.parse_args()

    if args.batch:
        # ── Batch mode ──────────────────────────────────────────────────────
        folder = Path(args.batch)
        if not folder.is_dir():
            print(f"Error: {folder} is not a directory.", file=sys.stderr)
            sys.exit(1)

        files = sorted(folder.glob("*.docx"))
        if not files:
            print(f"No .docx files found in {folder}.", file=sys.stderr)
            sys.exit(1)

        out_dir = Path(args.out_dir) if args.out_dir else folder

        for f in files:
            out_path = out_dir / f.with_suffix(".json").name
            _process_one(f, out_path, args.s3_bucket)

        print(f"\nDone — converted {len(files)} file(s).")

    else:
        # ── Single-file mode ─────────────────────────────────────────────────
        docx_path = Path(args.docx)
        if not docx_path.exists():
            print(f"Error: {docx_path} not found.", file=sys.stderr)
            sys.exit(1)

        out_path = Path(args.out) if args.out else None
        _process_one(docx_path, out_path, args.s3_bucket)


if __name__ == "__main__":
    main()