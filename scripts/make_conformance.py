"""Write the GFF3 conformance suite (conformance/) and its manifest.

Standard library only. Every case is written out below as the lines of a small
GFF3 file, with the findings a conforming validator reports for it. The
expected findings are taken from the GFF3 1.26 text and the rule catalogue
(rules/catalogue.yaml), not from any validator's output. Output is
deterministic: files are written as bytes with LF line endings (unless a case
says otherwise), and compressed files use stored deflate blocks, mtime 0 and
no file name, so the bytes do not depend on the local zlib build. Rerunning
the script reproduces identical bytes.

    python scripts/make_conformance.py            # rewrite conformance/
    python scripts/make_conformance.py --output DIR

To add a case, add a ``case(...)`` call below, rerun the script and commit the
script together with its output.

Profile cases (``profile_case(...)``, status ``extension:PROFILE``) are kept
apart, under ``profiles/`` and in the manifest's ``profile_cases``, so that
core-only consumers can ignore them. Every profile case is valid GFF3; its
``expected_profile`` says whether it complies with the profile.
"""

import argparse
import json
import shutil
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "conformance"
GENERATED_DIRECTORIES = ("valid", "invalid", "genomes", "profiles")
MANIFEST_VERSION = 1

SPEC = (
    "https://github.com/The-Sequence-Ontology/Specifications/blob/"
    "fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md"
)
CATALOGUE = "https://github.com/FAIR-bioHeaders/gff3-validator/blob/main/docs/rules.md"
QUESTIONS = (
    "https://github.com/FAIR-bioHeaders/gff3-validator/blob/main/docs/"
    "questions-for-SO.md"
)
STATUSES = {
    "spec": "The expected verdict follows from the GFF3 1.26 text.",
    "proposed": "The expected verdict or finding depends on an open question "
    "(open_question); it follows the proposed answer or the current catalogue "
    "behaviour, and may change when the Sequence Ontology group answers.",
    "extension:fhgff3": "FAIR-bioHeaders (FHGFF3) header layer, outside GFF3 " "1.26.",
    "extension:insdc": "Reserved for INSDC GFF3 extension cases (none yet).",
    "extension:agbiodata": "AgBioData GFF3 profile (profile_cases only): the "
    "file is valid GFF3; expected_profile says whether it complies with the "
    "profile.",
}
# The profiles the profile cases use (the same metadata as profiles/*.yaml;
# tests/test_profiles.py checks that they agree).
PROFILES = {
    "agbiodata": {
        "name": "AgBioData GFF3 recommendations",
        "version": "0.1.0-draft",
        "source": "https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/"
        "32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md",
        "license": "CC0-1.0",
        "rules": "https://github.com/FAIR-bioHeaders/gff3-validator/blob/main/"
        "docs/profiles/agbiodata.md",
    },
}
LEVELS = ("error", "warning", "info")
V = "##gff-version 3"


def t(*columns):
    """A feature line, joined with tabs.

    Either nine columns, or one string whose first eight columns are separated
    by spaces (column 9 keeps its spaces), as the specification prints them:
    t("ctg1 . gene 1 90 . + . ID=g1;Note=two words").
    """
    if len(columns) == 1:
        columns = columns[0].split(None, 8)
    assert len(columns) == 9, columns
    return "\t".join(str(column) for column in columns)


def f(rule, level, line):
    """An expected finding: rule id, level and 1-based line (None: whole file)."""
    assert level in LEVELS
    return {"rule": rule, "level": level, "line": line}


CASES = []


def case(
    id,
    verdict,
    lines,
    *,
    section,
    description,
    rule=None,
    findings=(),
    status="spec",
    open_question=None,
    genome=None,
    options=None,
    compression=None,
    ending="\n",
    raw=None,
):
    """Register one case.

    ``lines`` are text lines (encoded as UTF-8 and joined with ``ending``,
    with a final terminator); ``raw`` gives the exact bytes instead.
    """
    assert verdict in ("valid", "invalid")
    assert (status == "proposed") == (open_question is not None), id
    data = raw if raw is not None else "".join(x + ending for x in lines).encode()
    suffix = ".gz" if compression else ""
    entry = {
        "id": id,
        "file": f"{verdict}/{id}.gff3{suffix}",
        "expected": verdict,
        "rule": rule,
        "findings": list(findings),
        "section": section,
        "status": status,
    }
    if open_question:
        entry["open_question"] = open_question
    if compression:
        entry["compression"] = compression
    if genome:
        entry["genome"] = genome
    if options:
        entry["options"] = options
    entry["description"] = description
    CASES.append((entry, data))


# --------------------------------------------------------------------------
# Synthetic genome for the cases that need one (all BIO-* rules).
# --------------------------------------------------------------------------
#
# chr1 (120 bp): a plus-strand CDS 11..30 + 51..69 (ATG at 11, TAA at 67) and
# a minus-strand CDS 81..110 (TTA at 81 is the reverse complement of TAA, CAT
# at 108 that of ATG). Filler C reads as CCC (Pro) on +, GGG (Gly) on -.
# chr2 (60 bp): ATG CCC CCC CCC TGA CCC CCC CCC CCC TAA (1..30): TGA at 13 is
# an in-frame stop unless it is marked as selenocysteine.


def _sequence(length, pieces):
    bases = ["C"] * length
    for start, text in pieces.items():
        bases[start - 1 : start - 1 + len(text)] = text
    assert len(bases) == length
    return "".join(bases)


GENOME_SEQUENCES = {
    "chr1": _sequence(120, {11: "ATG", 67: "TAA", 81: "TTA", 108: "CAT"}),
    "chr2": _sequence(60, {1: "ATG", 13: "TGA", 28: "TAA"}),
}
GENOME = "genomes/genome.fa"
GENOME_GZ = "genomes/genome.fa.gz"


def fasta(sequences, width=60):
    lines = []
    for name, sequence in sequences.items():
        lines.append(f">{name}")
        lines += [sequence[i : i + width] for i in range(0, len(sequence), width)]
    return "".join(line + "\n" for line in lines).encode()


# --------------------------------------------------------------------------
# Compression without zlib's compressor: stored deflate blocks.
# --------------------------------------------------------------------------


def stored_deflate(data):
    blocks, size = [], 0xFFFF
    chunks = [data[i : i + size] for i in range(0, len(data), size)] or [b""]
    for index, chunk in enumerate(chunks):
        final = 1 if index == len(chunks) - 1 else 0
        blocks.append(struct.pack("<BHH", final, len(chunk), len(chunk) ^ 0xFFFF))
        blocks.append(chunk)
    return b"".join(blocks)


def gzip_member(data, extra=None):
    """One gzip member: no file name, mtime 0, OS 255 (unknown)."""
    flags = 4 if extra is not None else 0
    head = b"\x1f\x8b\x08" + bytes([flags]) + b"\0\0\0\0" + b"\0\xff"
    if extra is not None:
        head += struct.pack("<H", len(extra)) + extra
    trailer = struct.pack("<II", zlib.crc32(data) & 0xFFFFFFFF, len(data))
    return head + stored_deflate(data) + trailer


def gzip_bytes(data):
    return gzip_member(data)


def bgzf_bytes(data):
    """BGZF: gzip members of at most 64 KiB with a BC extra field, then EOF."""
    members = []
    for i in range(0, max(len(data), 1), 0xFF00):
        chunk = data[i : i + 0xFF00]
        body = gzip_member(chunk, extra=b"BC\x02\x00\x00\x00")
        size = len(body) - 1
        body = body[:16] + struct.pack("<H", size) + body[18:]
        members.append(body)
    eof = bytes.fromhex("1f8b08040000000000ff0600424302001b0003000000000000000000")
    return b"".join(members) + eof


# --------------------------------------------------------------------------
# Valid files
# --------------------------------------------------------------------------

CANONICAL = [
    "##gff-version 3.1.26",
    "##sequence-region ctg123 1 1497228",
    t("ctg123 . gene 1000 9000 . + . ID=gene00001;Name=EDEN"),
    t("ctg123 . TF_binding_site 1000 1012 . + . ID=tfbs00001;Parent=gene00001"),
    t("ctg123 . mRNA 1050 9000 . + . ID=mRNA00001;Parent=gene00001;Name=EDEN.1"),
    t("ctg123 . mRNA 1050 9000 . + . ID=mRNA00002;Parent=gene00001;Name=EDEN.2"),
    t("ctg123 . mRNA 1300 9000 . + . ID=mRNA00003;Parent=gene00001;Name=EDEN.3"),
    t("ctg123 . exon 1300 1500 . + . ID=exon00001;Parent=mRNA00003"),
    t("ctg123 . exon 1050 1500 . + . ID=exon00002;Parent=mRNA00001,mRNA00002"),
    t("ctg123 . exon 3000 3902 . + . ID=exon00003;Parent=mRNA00001,mRNA00003"),
    t(
        "ctg123 . exon 5000 5500 . + . ID=exon00004;Parent=mRNA00001,mRNA00002,mRNA00003"
    ),
    t(
        "ctg123 . exon 7000 9000 . + . ID=exon00005;Parent=mRNA00001,mRNA00002,mRNA00003"
    ),
    t("ctg123 . CDS 1201 1500 . + 0 ID=cds00001;Parent=mRNA00001;Name=edenprotein.1"),
    t("ctg123 . CDS 3000 3902 . + 0 ID=cds00001;Parent=mRNA00001;Name=edenprotein.1"),
    t("ctg123 . CDS 5000 5500 . + 0 ID=cds00001;Parent=mRNA00001;Name=edenprotein.1"),
    t("ctg123 . CDS 7000 7600 . + 0 ID=cds00001;Parent=mRNA00001;Name=edenprotein.1"),
    t("ctg123 . CDS 1201 1500 . + 0 ID=cds00002;Parent=mRNA00002;Name=edenprotein.2"),
    t("ctg123 . CDS 5000 5500 . + 0 ID=cds00002;Parent=mRNA00002;Name=edenprotein.2"),
    t("ctg123 . CDS 7000 7600 . + 0 ID=cds00002;Parent=mRNA00002;Name=edenprotein.2"),
    t("ctg123 . CDS 3301 3902 . + 0 ID=cds00003;Parent=mRNA00003;Name=edenprotein.3"),
    t("ctg123 . CDS 5000 5500 . + 1 ID=cds00003;Parent=mRNA00003;Name=edenprotein.3"),
    t("ctg123 . CDS 7000 7600 . + 1 ID=cds00003;Parent=mRNA00003;Name=edenprotein.3"),
    t("ctg123 . CDS 3391 3902 . + 0 ID=cds00004;Parent=mRNA00003;Name=edenprotein.4"),
    t("ctg123 . CDS 5000 5500 . + 1 ID=cds00004;Parent=mRNA00003;Name=edenprotein.4"),
    t("ctg123 . CDS 7000 7600 . + 1 ID=cds00004;Parent=mRNA00003;Name=edenprotein.4"),
]

CANONICAL_BYTES = "".join(line + "\n" for line in CANONICAL).encode()

case(
    "canonical-gene",
    "valid",
    CANONICAL,
    section="The Canonical Gene",
    description="The specification's canonical gene (lines 0 to 24), "
    "tab-separated: multi-parent exons, discontinuous CDS, two CDS on one mRNA.",
)
case(
    "canonical-gene-gzip",
    "valid",
    None,
    raw=gzip_bytes(CANONICAL_BYTES),
    compression="gzip",
    section="The Canonical Gene",
    description="canonical-gene, gzip-compressed (one member). Validate the "
    "decompressed bytes.",
)
case(
    "canonical-gene-bgzf",
    "valid",
    None,
    raw=bgzf_bytes(CANONICAL_BYTES),
    compression="bgzf",
    section="The Canonical Gene",
    description="canonical-gene, BGZF-compressed (multi-member gzip with the "
    "BGZF end-of-file block).",
)
case(
    "minimal",
    "valid",
    [V],
    section="Other Syntax: ##gff-version",
    description="Only the version directive: a file with no features.",
)
case(
    "comments-and-blank-lines",
    "valid",
    [
        V,
        "# a comment line",
        "",
        t("ctg1 . gene 1 90 . + . ID=g1"),
        "",
        "# blank lines are ignored",
        "###",
    ],
    section="The Canonical Gene (comments and blank lines)",
    description="Comment lines and blank lines between features are ignored.",
)
case(
    "multiple-parents",
    "valid",
    [
        V,
        t("ctg1 . gene 1 300 . + . ID=g1"),
        t("ctg1 . mRNA 1 300 . + . ID=t1;Parent=g1"),
        t("ctg1 . mRNA 1 300 . + . ID=t2;Parent=g1"),
        t("ctg1 . exon 1 100 . + . Parent=t1,t2"),
        t("ctg1 . exon 201 300 . + . ID=e2;Parent=t1,t2"),
        "###",
    ],
    section="Column 9: Parent (multiple parents)",
    description="Exons shared by two transcripts list both in one Parent value.",
)
case(
    "discontinuous-features",
    "valid",
    [
        V,
        t("ctg123 . gene 1050 9000 . + . ID=g1"),
        t("ctg123 . mRNA 1050 9000 . + . ID=t1;Parent=g1"),
        t("ctg123 . CDS 1201 1500 . + 0 ID=c1;Parent=t1"),
        t("ctg123 . CDS 3000 3902 . + 0 ID=c1;Parent=t1"),
        t(
            "ctg123 . cDNA_match 1050 1500 5.8e-42 + . ID=match00001;Target=cdna0123 12 462"
        ),
        t(
            "ctg123 . cDNA_match 5000 5500 8.1e-43 + . ID=match00001;Target=cdna0123 463 963"
        ),
        t(
            "ctg123 . cDNA_match 7000 9000 1.4e-40 + . ID=match00001;Target=cdna0123 964 2964"
        ),
    ],
    section="Column 9: ID (discontinuous features); Alignments",
    description="One CDS and one cDNA_match each spread over several lines "
    "sharing an ID, with a separate score and Target per line.",
)
case(
    "forward-references",
    "valid",
    [
        V,
        t("ctg1 . exon 1 90 . + . Parent=t1"),
        t("ctg1 . mRNA 1 90 . + . ID=t1;Parent=g1"),
        t("ctg1 . gene 1 90 . + . ID=g1"),
        "###",
    ],
    section="Other Syntax: ###",
    description="Children before their parents; all resolved before ###.",
)
case(
    "polycistronic-derives-from",
    "valid",
    [
        V,
        t("chrX . gene 100 900 . + . ID=gene01"),
        t("chrX . mRNA 100 900 . + . ID=mRNA01;Parent=gene01"),
        t("chrX . CDS 200 400 . + 0 ID=cds01;Parent=mRNA01"),
        t("chrX . polypeptide 200 400 . + . Derives_from=cds01"),
        "###",
    ],
    section="Pathological Cases: polycistronic transcripts",
    description="A polypeptide derives from a CDS (Derives_from, not Parent).",
)
case(
    "circular-genome",
    "valid",
    [
        V,
        "##sequence-region J02448 1 6407",
        t("J02448 GenBank region 1 6407 . + . ID=J02448;Name=J02448;Is_circular=true"),
        t("J02448 GenBank CDS 6006 7238 . + 0 ID=geneII;Name=II;Note=protein II"),
    ],
    section="Circular Genomes; Other Syntax: ##sequence-region",
    description="Gene II of phage f1 crosses the origin: end = 6407 + 831, "
    "beyond the ##sequence-region, allowed because the landmark is circular.",
)
case(
    "circular-genome-spec-example",
    "valid",
    [
        "##gff-version 3.1.26",
        "# organism Enterobacteria phage f1",
        "# Note Bacteriophage f1, complete genome.",
        t("J02448 GenBank region 1 6407 . + . ID=J02448;Name=J02448;Is_circular=true;"),
        t("J02448 GenBank CDS 6006 7238 . + 0 ID=geneII;Name=II;Note=protein II;"),
    ],
    rule="GFF-ATT-003",
    findings=[f("GFF-ATT-003", "info", 4)],
    status="proposed",
    open_question="Q4",
    section="Circular Genomes",
    description="The specification's circular-genome example as printed, with "
    "column 9 ending in ';' (a note, reported once per file).",
)
case(
    "embedded-fasta",
    "valid",
    [
        V,
        "##sequence-region ctg1 1 120",
        t("ctg1 . gene 1 120 . + . ID=g1"),
        t("ctg1 . mRNA 1 120 . + . ID=t1;Parent=g1"),
        t("ctg1 blastn cDNA_match 11 70 1e-20 + . ID=m1;Target=cdna1 1 60"),
        "##FASTA",
        ">ctg1 the annotated sequence",
        "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT",
        "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT",
        ">cdna1",
        "acgtacgtacgtacgtacgtacgtacgtacgtacgtacgtacgtacgtacgtacgtacgt",
    ],
    section="Other Syntax: ##FASTA",
    description="Features followed by a ##FASTA section with the landmark and "
    "a Target sequence.",
)
case(
    "alignments-gap",
    "valid",
    [
        V,
        t("chr3 . match 1 23 . . . ID=Match1;Target=EST23 1 21;Gap=M8 D3 M6 I1 M6"),
        t(
            "ctg123 . nucleotide_to_protein_match 100 129 . + . ID=match008;Target=p101 1 10;Gap=M3 I1 M2 D1 M4"
        ),
        t(
            "ctg123 . nucleotide_to_protein_match 100 127 . + . ID=match009;Target=p101 1 10;Gap=M3 I1 M2 F1 M4"
        ),
        t(
            "ctg123 . nucleotide_to_protein_match 100 125 . + . ID=match010;Target=p101 1 10;Gap=M3 I1 M2 R1 M4"
        ),
        t(
            "ctg123 . cDNA_match 1050 9000 6.2e-45 + . ID=match00001;Target=cdna0123 12 2964;Gap=M451 D3499 M501 D1499 M2001"
        ),
        t("ctg123 . cDNA_match 1200 9000 . . . ID=cDNA00001"),
        t(
            "ctg123 . match_part 1200 3200 2.2e-30 + . ID=match00002;Parent=cDNA00001;Target=mjm1123.5 5 506;Gap=M301 D1499 M201"
        ),
        t(
            "ctg123 . match_part 7000 9000 7.4e-32 - . ID=match00003;Parent=cDNA00001;Target=mjm1123.3 1 502;Gap=M101 D1499 M401"
        ),
        t("ctg123 . EST_match 1200 1220 . - . ID=match00004;Target=EST%2099 1 21 +"),
    ],
    findings=[f("SO-001", "warning", 3)],
    status="proposed",
    open_question="Q14",
    section="The Gap Attribute; Alignments; Column 9: Target",
    description="The specification's Gap examples (nucleotide, protein with "
    "frameshifts), match/match_part, and a Target with a strand and an escaped "
    "space in its id. The examples' nucleotide_to_protein_match is not an SO "
    "term: one warning for its three lines.",
)
case(
    "percent-encoding",
    "valid",
    [
        V,
        t("scaffold%231 . gene 1 90 . + . ID=g1;Note=50%25 identity"),
        t("ctg1 . gene 1 90 . + . ID=g2;Note=a%3Bb%3Dc%26d%2Ce,second value"),
        t("ctg1 . gene 1 90 . + . ID=g3;Note=tab%09and%0Anewline"),
        t("ctg1 . gene 1 90 . + . ID=g4;Name=café 日本"),
        t(
            "ctg1",
            "my source",
            "gene",
            1,
            90,
            ".",
            "+",
            ".",
            "ID=g5;Note=spaces are fine",
        ),
    ],
    section="Description of the Format: escaping; Column 1: seqid",
    description="Required encodings (%25, the column 9 reserved characters, "
    "tab and newline), a seqid escaping '#', literal UTF-8 and unescaped spaces.",
)
case(
    "attribute-values",
    "valid",
    [
        V,
        t(
            "ctg1 . gene 1 90 1e-10 + . ID=g1;Name=EDEN;Alias=eden,ED1;Note=first,second;Dbxref=EMBL:AA816246,NCBI_gi:10727410;Ontology_term=GO:0046703;my_tag=application value"
        ),
        t("ctg1 . TF_binding_site 5 17 -1.5 ? . ID=b1;Parent=g1"),
        t("ctg1 . region 1 90 0 . . ."),
        t("ctg1 . insertion_site 50 50 . + . ID=ins1"),
    ],
    section="Column 9: attributes; Columns 4 & 5; Column 6; Column 7",
    description="Multi-valued attributes, an application tag, scores, strand "
    "'?', an empty column 9 ('.') and a zero-length feature.",
)
case(
    "directives",
    "valid",
    [
        V,
        "##sequence-region ctg1 1 1000",
        "##species http://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=6239",
        "##genome-build WormBase ws110",
        t("ctg1 . gene 1 1000 . + . ID=g1"),
        "###",
    ],
    section="Other Syntax: directives",
    description="##sequence-region, ##species and ##genome-build in the "
    "specified forms.",
)
case(
    "crlf-line-endings",
    "valid",
    [
        V,
        t("ctg1 . gene 1 90 . + . ID=g1"),
        t("ctg1 . mRNA 1 90 . + . ID=t1;Parent=g1"),
    ],
    ending="\r\n",
    status="proposed",
    open_question="Q2",
    section="Description of the Format: escaping",
    description="CRLF line endings. Accepted (the CR before LF is not treated "
    "as an unescaped control character) pending question 2; the proposed "
    "answer adds one warning per file.",
)

# Biology: valid files checked against the synthetic genome.
GENES = [
    V,
    "##sequence-region chr1 1 120",
    t("chr1 . gene 1 75 . + . ID=g1"),
    t("chr1 . mRNA 1 75 . + . ID=t1;Parent=g1"),
    t("chr1 . exon 1 30 . + . Parent=t1"),
    t("chr1 . exon 51 75 . + . Parent=t1"),
    t("chr1 . CDS 11 30 . + 0 ID=cds1;Parent=t1"),
    t("chr1 . CDS 51 69 . + 1 ID=cds1;Parent=t1"),
    "###",
    t("chr1 . gene 81 110 . - . ID=g2"),
    t("chr1 . mRNA 81 110 . - . ID=t2;Parent=g2"),
    t("chr1 . CDS 81 110 . - 0 ID=cds2;Parent=t2"),
    "###",
]
case(
    "genes-with-genome",
    "valid",
    GENES,
    genome=GENOME,
    section="The Canonical Gene; Column 8: phase",
    description="A spliced plus-strand CDS (phase 1 on the second segment) "
    "and a minus-strand CDS, with start and stop codons, against the genome.",
)
case(
    "genes-with-gzip-genome",
    "valid",
    GENES,
    genome=GENOME_GZ,
    section="The Canonical Gene; Column 8: phase",
    description="genes-with-genome with a gzip-compressed genome FASTA.",
)
case(
    "partial-cds",
    "valid",
    [
        V,
        t("chr1 . gene 1 75 . + . ID=g1"),
        t("chr1 . mRNA 1 75 . + . ID=t1;Parent=g1"),
        t("chr1 . exon 1 30 . + . Parent=t1"),
        t("chr1 . exon 51 75 . + . Parent=t1"),
        t("chr1 . CDS 14 30 . + 0 ID=cds1;Parent=t1;partial=start"),
        t("chr1 . CDS 51 69 . + 1 ID=cds1;Parent=t1;partial=start"),
        "###",
        t("chr1 . gene 1 75 . + . ID=g2"),
        t("chr1 . mRNA 1 75 . + . ID=t2;Parent=g2"),
        t("chr1 . exon 1 30 . + . Parent=t2"),
        t("chr1 . exon 51 75 . + . Parent=t2"),
        t("chr1 . CDS 11 30 . + 0 ID=cds2;Parent=t2;partial=end"),
        t("chr1 . CDS 51 66 . + 1 ID=cds2;Parent=t2;partial=end"),
        "###",
    ],
    genome=GENOME,
    rule="BIO-011",
    findings=[f("BIO-011", "info", None)],
    status="proposed",
    open_question="Q17; SO-Ontologies#685",
    section="The Canonical Gene NOTE 5; Column 8: phase",
    description="A 5'-partial CDS without a start codon (partial=start) and a "
    "3'-partial CDS without a stop codon (partial=end), the INSDC markers. The "
    "exempted checks are noted as skipped (BIO-011), not reported as problems.",
)
case(
    "selenocysteine-recoded-codon",
    "valid",
    [
        V,
        t("chr2 . gene 1 30 . + . ID=g1"),
        t("chr2 . mRNA 1 30 . + . ID=t1;Parent=g1"),
        t("chr2 . CDS 1 30 . + 0 ID=cds1;Parent=t1"),
        t(
            "chr2 . stop_codon_redefined_as_selenocysteine 13 15 . + . ID=sec1;Parent=cds1;recoded_amino_acid=selenocysteine"
        ),
        "###",
    ],
    findings=[f("SO-009", "info", 5)],
    genome=GENOME,
    status="proposed",
    open_question="Q17; SO-Ontologies#658; Q13",
    section="The Canonical Gene",
    description="An in-frame TGA marked as selenocysteine by a recoded_codon "
    "subtype child of the CDS: no internal stop is reported (the subtype is "
    "outside SOFA, a note).",
)

# --------------------------------------------------------------------------
# One case per implemented catalogue rule. Each invalid case breaks one rule
# and has no other error; findings list every finding, at every level.
# --------------------------------------------------------------------------

G = t("ctg1 . gene 1 90 . + . ID=g1")


def one(id, verdict, rule, level, line, section, description, **options):
    """A two-line case: the version line and one feature line."""
    case(
        id,
        verdict,
        [V, line],
        rule=rule,
        findings=[f(rule, level, 2)],
        section=section,
        description=description,
        **options,
    )


# Syntax
case(
    "syn-001-comment-before-version",
    "invalid",
    ["# made by mytool", V, G],
    rule="GFF-SYN-001",
    findings=[f("GFF-SYN-001", "error", 1)],
    section="Other Syntax: ##gff-version",
    description="A comment precedes ##gff-version, which must be the topmost line.",
)
case(
    "syn-001-version-2",
    "invalid",
    ["##gff-version 2", G],
    rule="GFF-SYN-001",
    findings=[f("GFF-SYN-001", "error", 1)],
    section="Other Syntax: ##gff-version",
    description="The version number must begin with 3.",
)
case(
    "syn-001-byte-order-mark",
    "invalid",
    None,
    raw=("\ufeff" + V + "\n" + G + "\n").encode(),
    rule="GFF-SYN-001",
    findings=[f("GFF-SYN-001", "error", 1)],
    status="proposed",
    open_question="Q1",
    section="Other Syntax: ##gff-version",
    description="A UTF-8 byte order mark before ##gff-version.",
)
case(
    "syn-002-repeated-version",
    "invalid",
    [V, G, V],
    rule="GFF-SYN-002",
    findings=[f("GFF-SYN-002", "error", 3)],
    section="Change Log 1.21: the ##gff-version pragma only appears once",
    description="A second ##gff-version line (two files concatenated).",
)
one(
    "syn-003-spaces-not-tabs",
    "invalid",
    "GFF-SYN-003",
    "error",
    "ctg1 . gene 1 90 . + . ID=g1",
    "Description of the Format",
    "Columns separated by spaces instead of tabs.",
)
one(
    "syn-003-eight-columns",
    "invalid",
    "GFF-SYN-003",
    "error",
    "\t".join(["ctg1", ".", "gene", "1", "90", ".", "+", "."]),
    "Description of the Format",
    "A feature line with eight columns.",
)
one(
    "syn-004-empty-column",
    "invalid",
    "GFF-SYN-004",
    "error",
    t("ctg1", "", "gene", 1, 90, ".", "+", ".", "ID=g1"),
    "Description of the Format: undefined fields are replaced with '.'",
    "An empty source column instead of '.'.",
)
one(
    "syn-005-control-character",
    "invalid",
    "GFF-SYN-005",
    "error",
    t("ctg1 . gene 1 90 . + . ID=g1;Note=bell\x07here"),
    "Description of the Format: escaping",
    "An unescaped control character (U+0007) in column 9.",
)
case(
    "syn-006-not-utf8",
    "valid",
    None,
    raw=(V + "\n").encode()
    + t("ctg1 . gene 1 90 . + . ID=g1;Note=caf").encode()
    + b"\xe9\n",
    rule="GFF-SYN-006",
    findings=[f("GFF-SYN-006", "warning", 2)],
    section="Description of the Format: use of UTF-8 is recommended",
    description="A Latin-1 byte (0xE9) in column 9: UTF-8 is recommended, "
    "not required.",
)
one(
    "syn-007-end-of-line-comment",
    "valid",
    "GFF-SYN-007",
    "info",
    t("ctg1 . gene 1 90 . + . ID=g1 # check this"),
    "Other Syntax: end-of-line comments are not allowed",
    "Text that looks like an end-of-line comment; '#' is data, so the ID is "
    "'g1 # check this' (a note only).",
)
one(
    "syn-008-bare-percent",
    "invalid",
    "GFF-SYN-008",
    "error",
    t("ctg1 . gene 1 90 . + . ID=g1;Note=50% identity"),
    "Description of the Format: RFC 3986 percent-encoding",
    "A literal '%' not written as %25.",
)
one(
    "syn-009-over-encoded",
    "valid",
    "GFF-SYN-009",
    "warning",
    t("ctg1 . gene 1 90 . + . ID=g1;Name=EDEN%2D1"),
    "Description of the Format: escaping",
    "'-' encoded as %2D: 'no other characters may be encoded'. A warning "
    "under the proposed answer to question 3.",
    status="proposed",
    open_question="Q3",
)
one(
    "syn-010-seqid-whitespace",
    "invalid",
    "GFF-SYN-010",
    "error",
    t("chr 1", ".", "gene", 1, 90, ".", "+", ".", "ID=g1"),
    "Column 1: seqid",
    "A seqid with an unescaped space.",
)
one(
    "syn-012-undefined-type",
    "invalid",
    "GFF-SYN-012",
    "error",
    t("ctg1 . . 1 90 . + . ID=g1"),
    "Column 3: type",
    "Type '.' (undefined).",
)
one(
    "syn-013-non-integer-coordinates",
    "invalid",
    "GFF-SYN-013",
    "error",
    t("ctg1 . gene 1.0 90 . + . ID=g1"),
    "Columns 4 & 5: start and end",
    "Start written as 1.0.",
)
one(
    "syn-014-zero-start",
    "invalid",
    "GFF-SYN-014",
    "error",
    t("ctg1 . gene 0 90 . + . ID=g1"),
    "Columns 4 & 5: start and end",
    "A 0-based start.",
)
one(
    "syn-015-start-after-end",
    "invalid",
    "GFF-SYN-015",
    "error",
    t("ctg1 . gene 90 1 . - . ID=g1"),
    "Columns 4 & 5: start and end",
    "Start greater than end on the minus strand.",
)
one(
    "syn-016-score-not-a-number",
    "invalid",
    "GFF-SYN-016",
    "error",
    t("ctg1 blastn match 1 90 high + . ID=m1"),
    "Column 6: score",
    "Score 'high'.",
)
one(
    "syn-017-bad-strand",
    "invalid",
    "GFF-SYN-017",
    "error",
    t("ctg1 . gene 1 90 . 1 . ID=g1"),
    "Column 7: strand",
    "Strand '1'.",
)
one(
    "syn-018-bad-phase",
    "invalid",
    "GFF-SYN-018",
    "error",
    t("ctg1 . CDS 1 90 . + 3 ID=c1"),
    "Column 8: phase",
    "Phase 3.",
)
one(
    "syn-019-cds-without-phase",
    "invalid",
    "GFF-SYN-019",
    "error",
    t("ctg1 . CDS 1 90 . + . ID=c1"),
    "Column 8: phase",
    "A CDS with phase '.': the phase is required for all CDS features.",
)
case(
    "syn-019-cds-subtype-without-phase",
    "invalid",
    [V, t("ctg1 . CDS_predicted 1 90 . + . ID=c1")],
    rule="GFF-SYN-019",
    findings=[f("GFF-SYN-019", "error", 2), f("SO-009", "info", 2)],
    status="proposed",
    open_question="Q6",
    section="Column 8: phase",
    description="CDS_predicted, an is_a subtype of CDS, with phase '.' "
    "(CDS_predicted is outside SOFA, a note).",
)
case(
    "syn-020-phase-on-exon",
    "valid",
    [
        V,
        G,
        t("ctg1 . mRNA 1 90 . + . ID=t1;Parent=g1"),
        t("ctg1 . exon 1 90 . + 0 Parent=t1"),
        t("ctg1 . CDS 1 90 . + 0 Parent=t1"),
    ],
    rule="GFF-SYN-020",
    findings=[f("GFF-SYN-020", "warning", 4)],
    status="proposed",
    open_question="Q6",
    section="Column 8: phase",
    description="A phase on an exon; phase is defined only for CDS.",
)

# Attributes
one(
    "att-001-gtf-style",
    "invalid",
    "GFF-ATT-001",
    "error",
    t("ctg1 . gene 1 90 . + . ID=g1;Name EDEN"),
    "Column 9: attributes",
    "A pair without '=' (GTF style).",
)
one(
    "att-002-empty-tag",
    "invalid",
    "GFF-ATT-002",
    "error",
    t("ctg1 . gene 1 90 . + . ID=g1;=EDEN"),
    "Column 9: attributes",
    "A pair with an empty tag.",
)
one(
    "att-003-empty-pair",
    "valid",
    "GFF-ATT-003",
    "info",
    t("ctg1 . gene 1 90 . + . ID=g1;;Name=EDEN"),
    "Column 9: attributes",
    "An empty pair (';;'); a note only under the proposed answer.",
    status="proposed",
    open_question="Q4",
)
one(
    "att-004-repeated-tag",
    "invalid",
    "GFF-ATT-004",
    "error",
    t("ctg1 . gene 1 90 . + . ID=g1;Note=a;Note=b"),
    "Column 9: multiple attributes of the same type",
    "A tag repeated on one line instead of comma-separated values.",
)
one(
    "att-005-unescaped-reserved",
    "invalid",
    "GFF-ATT-005",
    "error",
    t("ctg1 . gene 1 90 . + . ID=g1;Note=a=b"),
    "Description of the Format: reserved characters in column 9",
    "An unescaped '=' inside a value.",
)
one(
    "att-006-id-with-comma",
    "invalid",
    "GFF-ATT-006",
    "error",
    t("ctg1 . gene 1 90 . + . ID=g1,g2"),
    "Column 9: multiple values",
    "ID is not one of the multi-valued tags, so it cannot hold two values.",
)
one(
    "att-007-unknown-reserved-tag",
    "valid",
    "GFF-ATT-007",
    "warning",
    t("ctg1 . gene 1 90 . + . ID=g1;Gene_biotype=protein_coding"),
    "Column 9: attributes that begin with an uppercase letter are reserved",
    "An upper-case tag that GFF3 does not define.",
    status="proposed",
    open_question="GFF-ATT-007",
)
one(
    "att-008-case-variant-tag",
    "valid",
    "GFF-ATT-008",
    "warning",
    t("ctg1 . exon 1 90 . + . parent=t1"),
    "Column 9: attribute names are case sensitive",
    "'parent' is a legal application tag but differs from the reserved tag "
    "Parent only by case.",
)
one(
    "att-009-quoted-value",
    "valid",
    "GFF-ATT-009",
    "info",
    t('ctg1 . gene 1 90 . + . ID=g1;Note="quoted"'),
    "Column 9: attribute values should not be quoted",
    "A quoted value; the quotes are part of the value (a note only).",
)
one(
    "att-010-target-missing-end",
    "invalid",
    "GFF-ATT-010",
    "error",
    t("ctg1 . cDNA_match 1050 1500 . + . ID=m1;Target=cdna0123 12"),
    "Column 9: Target",
    "A Target without an end coordinate.",
)
one(
    "att-011-sam-style-gap",
    "invalid",
    "GFF-ATT-011",
    "error",
    t("chr3 . match 1 23 . . . ID=m1;Target=EST23 1 21;Gap=8M3D6M"),
    "The Gap Attribute",
    "A SAM-style CIGAR string instead of space-separated operations.",
)
one(
    "att-012-gap-without-target",
    "valid",
    "GFF-ATT-012",
    "warning",
    t("chr3 . match 1 23 . . . ID=m1;Gap=M8 D3 M6 I1 M6"),
    "The Gap Attribute",
    "A Gap with no Target to align to.",
    status="proposed",
    open_question="GFF-ATT-012",
)
one(
    "att-013-gap-length-mismatch",
    "valid",
    "GFF-ATT-013",
    "warning",
    t("chr3 . match 1 30 . . . ID=m1;Target=EST23 1 21;Gap=M8 D3 M6 I1 M6"),
    "The Gap Attribute",
    "Gap covers 23 reference bases but the feature is 30 long.",
    status="proposed",
    open_question="GFF-ATT-013",
)
one(
    "att-014-dbxref-without-dbtag",
    "invalid",
    "GFF-ATT-014",
    "error",
    t("ctg1 . gene 1 90 . + . ID=g1;Dbxref=AA816246"),
    "Ontology Associations and DB Cross References",
    "A Dbxref value without the DBTAG: prefix.",
)
one(
    "att-016-is-circular-yes",
    "valid",
    "GFF-ATT-016",
    "warning",
    t("J02448 . region 1 6407 . + . ID=J02448;Is_circular=yes"),
    "Circular Genomes",
    "Is_circular with a value other than true.",
    status="proposed",
    open_question="GFF-ATT-016",
)

# Directives
case(
    "dir-001-sequence-region-two-fields",
    "invalid",
    [V, "##sequence-region ctg1 1000", G],
    rule="GFF-DIR-001",
    findings=[f("GFF-DIR-001", "error", 2)],
    section="Other Syntax: ##sequence-region",
    description="##sequence-region without a start.",
)
case(
    "dir-002-repeated-sequence-region",
    "invalid",
    [V, "##sequence-region ctg1 1 1000", "##sequence-region ctg1 1 2000", G],
    rule="GFF-DIR-002",
    findings=[f("GFF-DIR-002", "error", 3)],
    section="Other Syntax: ##sequence-region",
    description="Two ##sequence-region directives for one seqid.",
)
case(
    "dir-003-reference-across-resolution",
    "invalid",
    [
        V,
        t("ctg1 . mRNA 1 90 . + . ID=t1;Parent=g1"),
        "###",
        G,
    ],
    rule="GFF-DIR-003",
    findings=[f("GFF-DIR-003", "error", 2)],
    section="Other Syntax: ###",
    description="A Parent that is still unresolved at ### (defined after it).",
)
case(
    "dir-004-feature-after-fasta",
    "invalid",
    [V, "##FASTA", ">ctg1", "ACGTACGTAC", G],
    rule="GFF-DIR-004",
    findings=[f("GFF-DIR-004", "error", 5)],
    section="Other Syntax: ##FASTA",
    description="A feature line inside the FASTA section.",
)
case(
    "dir-005-implied-fasta",
    "valid",
    [V, t("ctg1 . gene 1 10 . + . ID=g1"), ">ctg1", "ACGTACGTAC"],
    rule="GFF-DIR-005",
    findings=[f("GFF-DIR-005", "warning", 3)],
    section="Other Syntax: ##FASTA (implied by a line beginning with >)",
    description="A '>' line starts the FASTA section without ##FASTA "
    "(allowed for backward compatibility).",
)
case(
    "dir-006-fasta-record-without-sequence",
    "valid",
    [
        V,
        t("ctg1 . gene 1 10 . + . ID=g1"),
        "##FASTA",
        ">ctg0",
        ">ctg1",
        "ACGTACGTAC",
    ],
    rule="GFF-DIR-006",
    findings=[f("GFF-DIR-006", "warning", 4)],
    status="proposed",
    open_question="GFF-DIR-006",
    section="Other Syntax: ##FASTA",
    description="A FASTA record with a header and no sequence.",
)
case(
    "dir-007-species-name",
    "valid",
    [V, "##species Caenorhabditis elegans", G],
    rule="GFF-DIR-007",
    findings=[f("GFF-DIR-007", "warning", 2)],
    section="Other Syntax: ##species",
    description="##species with a name rather than the preferred NCBI " "Taxonomy URL.",
)
case(
    "dir-008-genome-build-one-value",
    "valid",
    [V, "##genome-build GRCh38", G],
    rule="GFF-DIR-008",
    findings=[f("GFF-DIR-008", "warning", 2)],
    status="proposed",
    open_question="GFF-DIR-008",
    section="Other Syntax: ##genome-build",
    description="##genome-build without its source.",
)
case(
    "dir-009-feature-ontology",
    "valid",
    [
        V,
        "##feature-ontology http://song.cvs.sourceforge.net/viewvc/*checkout*/"
        "song/ontology/so.obo?revision=1.263",
        G,
    ],
    rule="GFF-DIR-009",
    findings=[f("GFF-DIR-009", "info", 2)],
    section="Other Syntax: ##feature-ontology",
    description="An ontology directive (recorded, not fetched: a note only).",
)
case(
    "dir-010-unknown-directive",
    "valid",
    [V, "##date 2026-10-08", G],
    rule="GFF-DIR-010",
    findings=[f("GFF-DIR-010", "info", 2)],
    section="Other Syntax: application-specific directives are allowed",
    description="An application-specific directive (a note only).",
)

# Structure
case(
    "str-001-duplicate-id",
    "invalid",
    [
        V,
        t("ctg1 . gene 1 90 . + . ID=x1"),
        t("ctg1 . mRNA 1 90 . + . ID=x1"),
    ],
    rule="GFF-STR-001",
    findings=[f("GFF-STR-001", "error", 3)],
    section="Column 9: ID",
    description="A gene and an mRNA share an ID, so they are not one feature.",
)
case(
    "str-002-strand-change",
    "valid",
    [
        V,
        t("ctg1 . mRNA 1 90 . + . ID=t1"),
        t("ctg1 . CDS 1 30 . + 0 ID=c1;Parent=t1"),
        t("ctg1 . CDS 61 90 . - 0 ID=c1;Parent=t1"),
    ],
    rule="GFF-STR-002",
    findings=[f("GFF-STR-002", "warning", 4)],
    status="proposed",
    open_question="Q8",
    section="Column 9: ID (discontinuous features)",
    description="The lines of one CDS are on different strands.",
)
case(
    "str-003-parent-change",
    "valid",
    [
        V,
        t("ctg1 . mRNA 1 90 . + . ID=t1"),
        t("ctg1 . mRNA 1 90 . + . ID=t2"),
        t("ctg1 . CDS 1 30 . + 0 ID=c1;Parent=t1"),
        t("ctg1 . CDS 61 90 . + 0 ID=c1;Parent=t2"),
    ],
    rule="GFF-STR-003",
    findings=[f("GFF-STR-003", "warning", 5)],
    status="proposed",
    open_question="Q8",
    section="Column 9: ID (discontinuous features)",
    description="The lines of one CDS name different parents.",
)
case(
    "str-004-unresolved-parent",
    "invalid",
    [V, t("ctg1 . exon 1 90 . + . Parent=mRNA0001")],
    rule="GFF-STR-004",
    findings=[f("GFF-STR-004", "error", 2)],
    section="Parent (part_of) Relationships",
    description="A Parent that names no ID in the file.",
)
case(
    "str-005-unresolved-derives-from",
    "invalid",
    [
        V,
        t("chrX . polypeptide 1 90 . + . ID=p1;Derives_from=cds99"),
    ],
    rule="GFF-STR-005",
    findings=[f("GFF-STR-005", "error", 2)],
    section="Column 9: Derives_from",
    description="A Derives_from that names no ID in the file.",
)
case(
    "str-006-parent-cycle",
    "invalid",
    [
        V,
        t("ctg1 . gene 1 90 . + . ID=a;Parent=b"),
        t("ctg1 . mRNA 1 90 . + . ID=b;Parent=a"),
    ],
    rule="GFF-STR-006",
    findings=[f("GFF-STR-006", "error", 2), f("SO-006", "warning", 2)],
    status="proposed",
    open_question="Q15",
    section="Parent (part_of) Relationships",
    description="Two features that are each other's Parent (a gene is not "
    "part_of an mRNA in SO, a warning).",
)
case(
    "str-007-derives-from-cycle",
    "valid",
    [
        V,
        t("chrX . polypeptide 1 90 . + . ID=p1;Derives_from=p2"),
        t("chrX . polypeptide 1 90 . + . ID=p2;Derives_from=p1"),
    ],
    rule="GFF-STR-007",
    findings=[f("GFF-STR-007", "warning", 2)],
    status="proposed",
    open_question="Q12",
    section="Pathological Cases",
    description="Two features that derive from each other.",
)
case(
    "str-008-outside-sequence-region",
    "invalid",
    [
        V,
        "##sequence-region ctg1 1 1000",
        t("ctg1 . gene 900 1200 . + . ID=g1"),
    ],
    rule="GFF-STR-008",
    findings=[f("GFF-STR-008", "error", 3)],
    section="Other Syntax: ##sequence-region",
    description="A feature extends past its ##sequence-region (not circular).",
)
case(
    "str-009-seqid-without-sequence-region",
    "valid",
    [
        V,
        "##sequence-region ctg1 1 1000",
        G,
        t("ctg2 . gene 1 90 . + . ID=g2"),
    ],
    rule="GFF-STR-009",
    findings=[f("GFF-STR-009", "info", 4)],
    section="Other Syntax: ##sequence-region",
    description="Some seqids have a ##sequence-region and ctg2 has none "
    "(optional; a note only).",
)
case(
    "str-010-seqid-not-in-fasta",
    "valid",
    [
        V,
        t("ctg2 . gene 1 4 . + . ID=g1"),
        "##FASTA",
        ">ctg1",
        "ACGT",
    ],
    rule="GFF-STR-010",
    findings=[f("GFF-STR-010", "warning", 2)],
    section="Other Syntax: ##FASTA",
    description="A ##FASTA section that lacks the landmark of a feature.",
)
case(
    "str-011-beyond-fasta-sequence",
    "invalid",
    [V, G, "##FASTA", ">ctg1", "ACGT"],
    rule="GFF-STR-011",
    findings=[f("GFF-STR-011", "error", 2)],
    section="Other Syntax: ##FASTA; Columns 4 & 5",
    description="A feature ends at 90 on a 4 bp embedded sequence.",
)

# Sequence Ontology (bundled so.obo data-version 2026-08-07)
one(
    "so-001-unknown-type",
    "valid",
    "SO-001",
    "warning",
    t("ctg1 . protein_coding_gene_model 1 90 . + . ID=g1"),
    "Column 3: type",
    "A type that is neither an SO term name nor an accession.",
    status="proposed",
    open_question="Q14",
)
one(
    "so-002-malformed-accession",
    "invalid",
    "SO-002",
    "error",
    t("ctg1 . SO:704 1 90 . + . ID=g1"),
    "Column 3: type",
    "An SO accession type with three digits instead of seven.",
    status="proposed",
    open_question="Q14",
)
one(
    "so-003-not-sequence-feature",
    "valid",
    "SO-003",
    "warning",
    t("ctg1 . coding_sequence_variant 1 90 . + . ID=v1"),
    "Column 3: type; Change Log 1.23",
    "A variant effect term, which is not an is_a descendant of sequence_feature.",
    status="proposed",
    open_question="Q14",
)
one(
    "so-004-obsolete-type",
    "valid",
    "SO-004",
    "warning",
    t("ctg1 . RNA_polymerase_promoter 1 90 . + . ID=p1"),
    "Column 3: type",
    "An obsolete SO term (replaced by promoter).",
    status="proposed",
    open_question="Q13",
)
one(
    "so-005-case-variant",
    "valid",
    "SO-005",
    "warning",
    t("ctg1 . five_prime_utr 1 30 . + . ID=u1"),
    "Column 3: type",
    "A type that differs from the SO label five_prime_UTR only by case.",
    status="proposed",
    open_question="Q14",
)
case(
    "so-006-parent-not-part-of",
    "valid",
    [
        V,
        G,
        t("ctg1 . exon 1 90 . + . ID=e1;Parent=g1"),
        t("ctg1 . mRNA 1 90 . + . ID=t1;Parent=e1"),
    ],
    rule="SO-006",
    findings=[f("SO-006", "warning", 4)],
    status="proposed",
    open_question="Q15",
    section="Parent (part_of) Relationships",
    description="An mRNA whose Parent is an exon: an exon is part of a "
    "transcript, not the reverse.",
)
case(
    "so-006-exon-part-of-gene",
    "valid",
    [
        V,
        G,
        t("ctg1 . mRNA 1 90 . + . ID=t1;Parent=g1"),
        t("ctg1 . exon 1 90 . + . Parent=g1"),
        t("ctg1 . CDS 1 90 . + 0 Parent=t1"),
    ],
    status="proposed",
    open_question="Q15",
    section="The Canonical Gene NOTE 2",
    description="An exon attached directly to its gene, allowed by the "
    "transitivity of part_of.",
)
one(
    "so-008-unknown-ontology-term",
    "valid",
    "SO-008",
    "warning",
    t("ctg1 . mRNA 1 90 . + . ID=t1;Ontology_term=SO:9999999"),
    "Pathological Cases: programmed frameshift",
    "An Ontology_term value with the SO prefix that is not an SO term.",
    status="proposed",
    open_question="Q13",
)
case(
    "so-009-outside-sofa",
    "valid",
    [
        V,
        t("ctg1 . protein_coding_gene 1 90 . + . ID=g1"),
        t("ctg1 . protein_coding_gene 101 190 . + . ID=g2"),
    ],
    rule="SO-009",
    findings=[f("SO-009", "info", 2)],
    status="proposed",
    open_question="Q13",
    section="Column 3: type",
    description="An SO term outside SOFA: one note per type, at its first line.",
)

# Biology (with the genome)
PLUS = [
    t("chr1 . gene 1 75 . + . ID=g1"),
    t("chr1 . mRNA 1 75 . + . ID=t1;Parent=g1"),
    t("chr1 . exon 1 30 . + . Parent=t1"),
    t("chr1 . exon 51 75 . + . Parent=t1"),
]


def cds(start1, end1, start2, end2, phase2, phase1=0):
    return [
        t("chr1", ".", "CDS", start1, end1, ".", "+", phase1, "ID=cds1;Parent=t1"),
        t("chr1", ".", "CDS", start2, end2, ".", "+", phase2, "ID=cds1;Parent=t1"),
    ]


case(
    "bio-001-seqid-not-in-genome",
    "invalid",
    [
        V,
        t("chr1 . gene 1 90 . + . ID=g1"),
        t("chrZ . gene 1 90 . + . ID=g2"),
    ],
    genome=GENOME,
    rule="BIO-001",
    findings=[f("BIO-001", "error", 3)],
    section="Column 1: seqid",
    description="A seqid that is not a sequence of the genome.",
)
case(
    "bio-002-beyond-genome",
    "invalid",
    [V, t("chr1 . gene 1 200 . + . ID=g1")],
    genome=GENOME,
    rule="BIO-002",
    findings=[f("BIO-002", "error", 2)],
    section="Columns 4 & 5: start and end",
    description="A feature ends at 200 on the 120 bp chr1.",
)
case(
    "bio-003-sequence-region-longer",
    "valid",
    [
        V,
        "##sequence-region chr1 1 200",
        t("chr1 . gene 1 90 . + . ID=g1"),
    ],
    genome=GENOME,
    rule="BIO-003",
    findings=[f("BIO-003", "warning", 2)],
    section="Other Syntax: ##sequence-region",
    description="##sequence-region claims 200 bp; chr1 has 120.",
)
case(
    "bio-004-inconsistent-phase",
    "valid",
    [V] + PLUS + cds(11, 30, 51, 69, 0),
    genome=GENOME,
    rule="BIO-004",
    findings=[f("BIO-004", "warning", 7), f("BIO-011", "info", None)],
    status="proposed",
    open_question="Q17",
    section="Column 8: phase",
    description="The second CDS segment has phase 0; 20 coding bases before "
    "it make it 1. Stop codons are then not judged (BIO-011).",
)
case(
    "bio-005-cds-outside-exon",
    "valid",
    [V] + PLUS[:3] + [t("chr1 . exon 51 60 . + . Parent=t1")] + cds(11, 30, 51, 69, 1),
    genome=GENOME,
    rule="BIO-005",
    findings=[f("BIO-005", "warning", 7)],
    status="proposed",
    open_question="Q11",
    section="The Canonical Gene",
    description="The second CDS segment (51..69) extends past its exon (51..60).",
)
case(
    "bio-006-no-start-codon",
    "valid",
    [V] + PLUS + cds(14, 30, 51, 69, 1),
    genome=GENOME,
    rule="BIO-006",
    findings=[f("BIO-006", "warning", 6)],
    status="proposed",
    open_question="Q17",
    section="The Canonical Gene NOTE 5",
    description="A CDS that starts with CCC, not a start codon, and is not "
    "marked partial.",
)
case(
    "bio-007-no-stop-codon",
    "valid",
    [V] + PLUS + cds(11, 30, 51, 66, 1),
    genome=GENOME,
    rule="BIO-007",
    findings=[f("BIO-007", "warning", 7)],
    status="proposed",
    open_question="Q17",
    section="The Canonical Gene NOTE 5",
    description="A CDS that ends with CCC, not a stop codon, and is not marked "
    "partial.",
)
case(
    "bio-008-internal-stop",
    "valid",
    [
        V,
        t("chr2 . gene 1 30 . + . ID=g1"),
        t("chr2 . mRNA 1 30 . + . ID=t1;Parent=g1"),
        t("chr2 . CDS 1 30 . + 0 ID=cds1;Parent=t1"),
    ],
    genome=GENOME,
    rule="BIO-008",
    findings=[f("BIO-008", "warning", 4)],
    status="proposed",
    open_question="Q17",
    section="The Canonical Gene",
    description="An in-frame TGA at 13..15 that is not marked as recoded.",
)
case(
    "bio-009-length-not-multiple-of-three",
    "valid",
    [V] + PLUS + cds(11, 30, 51, 68, 1),
    genome=GENOME,
    rule="BIO-009",
    findings=[f("BIO-009", "info", 7)],
    section="Column 8: phase",
    description="38 coding bases (the stop codon is incomplete); the "
    "specification's own canonical gene has such CDS, so a note only.",
)
case(
    "bio-010-strand-mismatch",
    "valid",
    [
        V,
        t("chr1 . gene 1 90 . + . ID=g1"),
        t("chr1 . mRNA 1 90 . - . ID=t1;Parent=g1"),
    ],
    genome=GENOME,
    rule="BIO-010",
    findings=[f("BIO-010", "warning", 3)],
    status="proposed",
    open_question="Q18",
    section="The Canonical Gene",
    description="An mRNA on the opposite strand to its gene.",
)
case(
    "bio-011-cds-without-strand",
    "valid",
    [V, t("chr1 . CDS 11 69 . . 0 ID=c1")],
    genome=GENOME,
    rule="BIO-011",
    findings=[f("BIO-011", "info", None)],
    section="Column 7: strand; Column 8: phase",
    description="A CDS on strand '.' has no 5' end, so its codons cannot be "
    "checked (a note that checks were skipped).",
)

# FAIR-bioHeaders (FHGFF3) header layer: outside GFF3 1.26.
HEADER = [
    V,
    "#~schema: https://raw.githubusercontent.com/FAIR-bioHeaders/"
    "FHR-Specification/main/fhr.json",
    "#~schemaVersion: 1.0",
    G,
]
case(
    "hdr-001-header-required",
    "invalid",
    [V, G],
    options={"require_header": True},
    rule="HDR-001",
    findings=[f("HDR-001", "error", None)],
    status="extension:fhgff3",
    section="FHR-Specification spec 009 FR-001",
    description="No #~ header lines, but the header was required.",
)
case(
    "hdr-002-header-present",
    "valid",
    HEADER,
    rule="HDR-002",
    findings=[f("HDR-002", "info", None)],
    status="extension:fhgff3",
    section="FHR-Specification spec 009 FR-006",
    description="#~ header lines are '#' comments to GFF3; their content is "
    "not validated yet (a note).",
)
case(
    "hdr-003-header-checks-skipped",
    "valid",
    HEADER,
    options={"no_header": True},
    rule="HDR-003",
    findings=[f("HDR-003", "info", None)],
    status="extension:fhgff3",
    section="FHR-Specification spec 009 FR-006",
    description="Header checks switched off (a note that they were skipped).",
)


# --------------------------------------------------------------------------
# Profile cases: valid GFF3 files checked against a profile (--profile).
# A non-compliant case has exactly one profile error rule (its rule); core
# findings (all below error) and profile findings are both complete.
# --------------------------------------------------------------------------

PROFILE_CASES = []


def profile_case(
    id,
    compliant,
    lines,
    *,
    section,
    description,
    rule=None,
    findings=(),
    profile_findings=(),
    profile="agbiodata",
    genome=None,
):
    folder = "compliant" if compliant else "noncompliant"
    entry = {
        "id": id,
        "file": f"profiles/{profile}/{folder}/{id}.gff3",
        "profile": profile,
        "expected": "valid",
        "expected_profile": "compliant" if compliant else "not-compliant",
        "rule": rule,
        "findings": list(findings),
        "profile_findings": list(profile_findings),
        "section": section,
        "status": f"extension:{profile}",
    }
    if genome:
        entry["genome"] = genome
    entry["description"] = description
    PROFILE_CASES.append((entry, "".join(x + "\n" for x in lines).encode()))


AGB = "AgBioData recommendations: "
TX = t("ctg1 . mRNA 1 90 . + . ID=t1;Parent=g1")
profile_case(
    "agbiodata-genes-with-genome",
    True,
    GENES,
    genome=GENOME,
    section=AGB + "Modeling hierarchical relationships of a protein-coding gene",
    description="Two gene models written top down (gene, mRNA, exon, CDS), "
    "separated by ###, with start and stop codons and no internal stop: no "
    "core or profile findings.",
)
profile_case(
    "agb-001-ontology-term",
    True,
    [V, t("ctg1 . gene 1 90 . + . ID=g1;Ontology_term=SO:0001217")],
    rule="AGB-001",
    profile_findings=[f("AGB-001", "warning", 2)],
    section=AGB + "Attributes : Ontology_term, Validation",
    description="Ontology_term is used, which the recommendations ask the "
    "validator to warn about.",
)
profile_case(
    "agb-002-go-term-in-dbxref",
    True,
    [V, G, t("ctg1 . mRNA 1 90 . + . ID=t1;Parent=g1;Dbxref=GO:0004381")],
    rule="AGB-002",
    profile_findings=[f("AGB-002", "warning", 3)],
    section=AGB + "Attributes complex metadata / functional annotations, "
    "Best practices",
    description="A GO term given as a Dbxref.",
)
profile_case(
    "agb-003-child-outside-parent",
    True,
    [V, G, t("ctg1 . mRNA 1 120 . + . ID=t1;Parent=g1")],
    rule="AGB-003",
    profile_findings=[f("AGB-003", "warning", 3)],
    section=AGB + "Modeling hierarchical relationships of a protein-coding "
    "gene, Best practices",
    description="An mRNA (1..120) that extends beyond its gene (1..90).",
)
profile_case(
    "agb-004-child-before-parent",
    True,
    [V, TX, G],
    rule="AGB-004",
    profile_findings=[f("AGB-004", "info", 2)],
    section=AGB + "Modeling hierarchical relationships of a protein-coding "
    "gene, Best practices (sort order)",
    description="The mRNA comes before its gene; a forward reference is valid " "GFF3.",
)
profile_case(
    "agb-005-multiple-parents",
    True,
    [
        V,
        G,
        TX,
        t("ctg1 . mRNA 1 90 . + . ID=t2;Parent=g1"),
        t("ctg1 . exon 1 90 . + . ID=e1;Parent=t1,t2"),
    ],
    rule="AGB-005",
    profile_findings=[f("AGB-005", "info", 5)],
    section=AGB + "Modeling hierarchical relationships of a protein-coding "
    "gene, Best practices",
    description="An exon shared by two transcripts through two Parent values.",
)
profile_case(
    "agb-006-polypeptide",
    True,
    [
        V,
        G,
        TX,
        t("ctg1 . CDS 1 90 . + 0 ID=c1;Parent=t1"),
        t("ctg1 . polypeptide 1 90 . + . ID=p1;Derives_from=c1"),
    ],
    rule="AGB-006",
    profile_findings=[f("AGB-006", "info", 5)],
    section=AGB + "Attributes : Derives_from, Best practices",
    description="A polypeptide derived from the CDS, which the recommendations "
    "advise leaving out.",
)
profile_case(
    "agb-007-exon-without-parent",
    True,
    [V, t("ctg1 . exon 1 90 . + . ID=e1")],
    rule="AGB-007",
    profile_findings=[f("AGB-007", "warning", 2)],
    section=AGB + "Modeling hierarchical relationships of a protein-coding "
    "gene, Validation",
    description="An exon without a Parent transcript.",
)
profile_case(
    "agb-008-so-term-name",
    True,
    [V, t("ctg1 . gene 1 90 . + . ID=g1;so_term_name=mRNA")],
    rule="AGB-008",
    profile_findings=[f("AGB-008", "warning", 2)],
    section=AGB + "Type (column 3), Best practice",
    description="so_term_name names mRNA, which is not a kind of gene.",
)
profile_case(
    "agb-009-target-spaces",
    False,
    [V, t("ctg1 blastn match_part 1 90 . + . ID=m1;Target=EST23  1 90 +")],
    rule="AGB-009",
    profile_findings=[f("AGB-009", "error", 2)],
    section=AGB + "Attributes : Target, Gap, Validation",
    description="Two spaces between the target_id and the start; the "
    "recommendations require single spaces.",
)
profile_case(
    "agb-010-ontology-uri",
    True,
    [V, "##feature-ontology http://song.cvs.sourceforge.net/sofa.obo", G],
    rule="AGB-010",
    findings=[f("GFF-DIR-009", "info", 2)],
    profile_findings=[f("AGB-010", "info", 2)],
    section=AGB + "Pragmas, Ontology URIs",
    description="A CVS URL for the feature ontology instead of an OBO PURL.",
)
profile_case(
    "agb-011-species-url",
    True,
    [
        V,
        "##species https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=9606",
        G,
    ],
    rule="AGB-011",
    profile_findings=[f("AGB-011", "info", 2)],
    section=AGB + "Pragmas, Species",
    description="The NCBI Taxonomy URL that GFF3 1.26 prefers; the "
    "recommendations prefer the CURIE NCBITaxon:9606 (which gets the core "
    "warning GFF-DIR-007 instead).",
)
profile_case(
    "agb-012-score-directive",
    True,
    [V, '##Score name="AED";best=low', G],
    rule="AGB-012",
    findings=[f("GFF-DIR-010", "info", 2)],
    profile_findings=[f("AGB-012", "warning", 2)],
    section=AGB + "Score (column 6), Validation",
    description="A ##Score directive without min and max.",
)
profile_case(
    "agb-013-seqid-comma",
    True,
    [V, t("scaffold1,scaffold2 . gene 1 90 . + . ID=g1")],
    rule="AGB-013",
    profile_findings=[f("AGB-013", "warning", 2)],
    section=AGB + "Modeling hierarchical relationships of a protein-coding "
    "gene, Best practices",
    description="A gene split across scaffolds written with two seqids in " "column 1.",
)
profile_case(
    "so-001-raised-to-error",
    False,
    [V, t("ctg1 . gene_model 1 90 . + . ID=g1")],
    rule="SO-001",
    findings=[f("SO-001", "warning", 2)],
    profile_findings=[f("SO-001", "error", 2)],
    section=AGB + "Type (column 3), Validation",
    description="A type that is not an SO term: a core warning, raised to an "
    "error by the profile.",
)
profile_case(
    "bio-008-raised-to-error",
    False,
    [
        V,
        t("chr2 . gene 1 30 . + . ID=g1"),
        t("chr2 . mRNA 1 30 . + . ID=t1;Parent=g1"),
        t("chr2 . CDS 1 30 . + 0 ID=cds1;Parent=t1"),
    ],
    genome=GENOME,
    rule="BIO-008",
    findings=[f("BIO-008", "warning", 4)],
    profile_findings=[f("BIO-008", "error", 4)],
    section=AGB + "Phase (column 8), Validation",
    description="An in-frame TGA: a core warning, raised to an error by the "
    "profile.",
)


def manifest():
    rules = sorted({entry["rule"] for entry, _ in CASES if entry["rule"]})
    return {
        "manifest_version": MANIFEST_VERSION,
        "title": "GFF3 conformance suite",
        "specification": {"title": "GFF3 specification 1.26", "url": SPEC},
        "rule_catalogue": CATALOGUE,
        "questions": QUESTIONS,
        "statuses": STATUSES,
        "levels": {
            "error": "the file is invalid",
            "warning": "probably a mistake; the file stays valid",
            "info": "a note; the file stays valid",
        },
        "rules": rules,
        "cases": [entry for entry, _ in CASES],
        "profiles": PROFILES,
        "profile_rules": sorted(
            {entry["rule"] for entry, _ in PROFILE_CASES if entry["rule"]}
        ),
        "profile_cases": [entry for entry, _ in PROFILE_CASES],
    }


def check_cases():
    seen = set()
    for entry, _ in CASES:
        assert entry["id"] not in seen, entry["id"]
        seen.add(entry["id"])
        errors = {x["rule"] for x in entry["findings"] if x["level"] == "error"}
        if entry["expected"] == "invalid":
            assert errors == {entry["rule"]}, entry["id"]
        else:
            assert not errors, entry["id"]
        if entry["rule"]:
            assert entry["rule"] in {x["rule"] for x in entry["findings"]}, entry["id"]
    for entry, _ in PROFILE_CASES:
        assert entry["id"] not in seen, entry["id"]
        seen.add(entry["id"])
        assert entry["profile"] in PROFILES, entry["id"]
        assert not [x for x in entry["findings"] if x["level"] == "error"], entry["id"]
        errors = {x["rule"] for x in entry["profile_findings"] if x["level"] == "error"}
        if entry["expected_profile"] == "not-compliant":
            assert errors == {entry["rule"]}, entry["id"]
        else:
            assert not errors, entry["id"]
        if entry["rule"]:
            rules = {x["rule"] for x in entry["profile_findings"]}
            assert entry["rule"] in rules, entry["id"]


def write(output):
    check_cases()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name in GENERATED_DIRECTORIES:
        shutil.rmtree(output / name, ignore_errors=True)
        (output / name).mkdir()
    for entry, data in CASES + PROFILE_CASES:
        (output / entry["file"]).parent.mkdir(parents=True, exist_ok=True)
        (output / entry["file"]).write_bytes(data)
    genome = fasta(GENOME_SEQUENCES)
    (output / GENOME).write_bytes(genome)
    (output / GENOME_GZ).write_bytes(gzip_bytes(genome))
    text = json.dumps(manifest(), indent=2, ensure_ascii=False) + "\n"
    (output / "manifest.json").write_bytes(text.encode())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)
    write(args.output)
    print(
        f"wrote {len(CASES)} cases and {len(PROFILE_CASES)} profile cases to "
        f"{args.output}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
