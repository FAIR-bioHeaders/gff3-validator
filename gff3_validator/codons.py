"""NCBI genetic codes (translation tables) for the biology rules.

Each table is written as NCBI publishes it
(https://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi): 64 amino acids
and 64 start flags for the codons in TCAG order (TTT, TTC, TTA, TTG, TCT, ...).
To add a table, add its NCBI id, name, ``AAs`` and ``Starts`` strings below.

Tables 27, 28 and 31 are left out on purpose: in them TAA, TAG or TGA is a
stop or an amino acid depending on context, so stop codons cannot be judged
codon by codon. The table is never inferred from the organism; table 1 is the
default and bacteria, archaea and plastids use table 11.
"""

import re
from typing import FrozenSet, NamedTuple

BASES = "TCAG"
CODONS = [a + b + c for a in BASES for b in BASES for c in BASES]

# id: (name, AAs, Starts)
TABLES = {
    1: (
        "Standard",
        "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG",
        "---M------**--*----M---------------M----------------------------",
    ),
    2: (
        "Vertebrate Mitochondrial",
        "FFLLSSSSYY**CCWWLLLLPPPPHHQQRRRRIIMMTTTTNNKKSS**VVVVAAAADDEEGGGG",
        "----------**--------------------MMMM----------**---M------------",
    ),
    3: (
        "Yeast Mitochondrial",
        "FFLLSSSSYY**CCWWTTTTPPPPHHQQRRRRIIMMTTTTNNKKSSRRVVVVAAAADDEEGGGG",
        "----------**----------------------MM---------------M------------",
    ),
    4: (
        "Mold, Protozoan, and Coelenterate Mitochondrial; Mycoplasma/Spiroplasma",
        "FFLLSSSSYY**CCWWLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG",
        "--MM------**-------M------------MMMM---------------M------------",
    ),
    5: (
        "Invertebrate Mitochondrial",
        "FFLLSSSSYY**CCWWLLLLPPPPHHQQRRRRIIMMTTTTNNKKSSSSVVVVAAAADDEEGGGG",
        "---M------**--------------------MMMM---------------M------------",
    ),
    6: (
        "Ciliate, Dasycladacean and Hexamita Nuclear",
        "FFLLSSSSYYQQCC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG",
        "--------------*--------------------M----------------------------",
    ),
    9: (
        "Echinoderm and Flatworm Mitochondrial",
        "FFLLSSSSYY**CCWWLLLLPPPPHHQQRRRRIIIMTTTTNNNKSSSSVVVVAAAADDEEGGGG",
        "----------**-----------------------M---------------M------------",
    ),
    10: (
        "Euplotid Nuclear",
        "FFLLSSSSYY**CCCWLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG",
        "----------**-----------------------M----------------------------",
    ),
    11: (
        "Bacterial, Archaeal and Plant Plastid",
        "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG",
        "---M------**--*----M------------MMMM---------------M------------",
    ),
    12: (
        "Alternative Yeast Nuclear",
        "FFLLSSSSYY**CC*WLLLSPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG",
        "----------**--*----M---------------M----------------------------",
    ),
    13: (
        "Ascidian Mitochondrial",
        "FFLLSSSSYY**CCWWLLLLPPPPHHQQRRRRIIMMTTTTNNKKSSGGVVVVAAAADDEEGGGG",
        "---M------**----------------------MM---------------M------------",
    ),
    14: (
        "Alternative Flatworm Mitochondrial",
        "FFLLSSSSYYY*CCWWLLLLPPPPHHQQRRRRIIIMTTTTNNNKSSSSVVVVAAAADDEEGGGG",
        "-----------*-----------------------M----------------------------",
    ),
    16: (
        "Chlorophycean Mitochondrial",
        "FFLLSSSSYY*LCC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG",
        "----------*---*--------------------M----------------------------",
    ),
    21: (
        "Trematode Mitochondrial",
        "FFLLSSSSYY**CCWWLLLLPPPPHHQQRRRRIIMMTTTTNNNKSSSSVVVVAAAADDEEGGGG",
        "----------**-----------------------M---------------M------------",
    ),
    22: (
        "Scenedesmus obliquus Mitochondrial",
        "FFLLSS*SYY*LCC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG",
        "------*---*---*--------------------M----------------------------",
    ),
    23: (
        "Thraustochytrium Mitochondrial",
        "FF*LSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG",
        "--*-------**--*-----------------M--M---------------M------------",
    ),
    24: (
        "Rhabdopleuridae Mitochondrial",
        "FFLLSSSSYY**CCWWLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSSKVVVVAAAADDEEGGGG",
        "---M------**-------M---------------M---------------M------------",
    ),
    25: (
        "Candidate Division SR1 and Gracilibacteria",
        "FFLLSSSSYY**CCGWLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG",
        "---M------**-----------------------M---------------M------------",
    ),
    26: (
        "Pachysolen tannophilus Nuclear",
        "FFLLSSSSYY**CC*WLLLAPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG",
        "----------**--*----M---------------M----------------------------",
    ),
    29: (
        "Mesodinium Nuclear",
        "FFLLSSSSYYYYCC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG",
        "--------------*--------------------M----------------------------",
    ),
    30: (
        "Peritrich Nuclear",
        "FFLLSSSSYYEECC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG",
        "--------------*--------------------M----------------------------",
    ),
    32: (
        "Balanophoraceae Plastid",
        "FFLLSSSSYY*WCC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG",
        "---M------*---*----M------------MMMM---------------M------------",
    ),
    33: (
        "Cephalodiscidae Mitochondrial",
        "FFLLSSSSYYY*CCWWLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSSKVVVVAAAADDEEGGGG",
        "---M-------*-------M---------------M---------------M------------",
    ),
}
DEFAULT_TABLE = 1


class CodonTable(NamedTuple):
    id: int
    name: str
    starts: FrozenSet[bytes]
    stops: FrozenSet[bytes]
    # Matches a run of in-frame codons that are not stop codons.
    no_stop: "re.Pattern"


def _no_stop_pattern(stops):
    """A regular expression for one codon that is not in ``stops``.

    Codons with bases other than A, C, G and T (N, IUPAC codes) match, so an
    ambiguous codon is never taken for a stop.
    """
    if not stops:
        return re.compile(b"(?:...)*", re.DOTALL)

    def others(chars):
        return b"[^" + bytes(sorted(set(chars))) + b"]"

    parts = [others(s[0] for s in stops) + b".."]
    for first in sorted({s[0] for s in stops}):
        seconds = {s[1] for s in stops if s[0] == first}
        prefix = bytes([first])
        parts.append(prefix + others(seconds) + b".")
        for second in sorted(seconds):
            thirds = {s[2] for s in stops if s[:2] == prefix + bytes([second])}
            parts.append(prefix + bytes([second]) + others(thirds))
    return re.compile(b"(?:" + b"|".join(parts) + b")*", re.DOTALL)


def table(number: int) -> CodonTable:
    """The NCBI translation table ``number``; ``KeyError`` if not available."""
    name, amino_acids, starts = TABLES[number]
    stops = frozenset(
        codon.encode() for codon, aa in zip(CODONS, amino_acids) if aa == "*"
    )
    start_codons = frozenset(
        codon.encode() for codon, flag in zip(CODONS, starts) if flag == "M"
    )
    return CodonTable(number, name, start_codons, stops, _no_stop_pattern(stops))
