#!/bin/sh
# Re-run the tool comparison in docs/EVALUATION.md on the test fixtures.
# Needs (not installed by this project):
#   conda/mamba env with genometools-genometools=1.6.6 and agat=1.7.0 (bioconda)
#   pip install gff3tool==2.1.0
# Usage: scripts/evaluation/compare_tools.sh OUTDIR
set -u
out=${1:?usage: compare_tools.sh OUTDIR}
here=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$out"
# gff3_QC wants a FASTA; any sequences named ctg1 (100 bp) and ctg123 do.
printf '>ctg1\n%s\n>ctg123\n%s\n' \
  "$(printf 'ACGT%.0s' $(seq 25))" "$(printf 'A%.0s' $(seq 10000))" > "$out/ref.fa"
for f in "$here"/tests/fixtures/valid/*.gff3 "$here"/tests/fixtures/invalid/*.gff3; do
  b=$(basename "$f" .gff3)
  gff3-validate --format json "$f" > "$out/$b.ours.json"; echo "ours $b exit=$?"
  gt gff3validator "$f" > "$out/$b.gt.txt" 2>&1; echo "gt $b exit=$?"
  gt gff3validator -typecheck so "$f" > "$out/$b.gt-so.txt" 2>&1; echo "gt-so $b exit=$?"
  (cd "$out" && agat_convert_sp_gxf2gxf.pl --gff "$f" -o "$b.agat.gff3" > "$b.agat.txt" 2>&1)
  echo "agat $b exit=$?"
  gff3_QC -g "$f" -f "$out/ref.fa" -o "$out/$b.qc.txt" -s "$out/$b.qc.stat" \
    > "$out/$b.qc.log" 2>&1; echo "gff3_QC $b exit=$?"
done
