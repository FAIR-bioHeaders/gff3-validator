# Security policy

This repository follows the FAIR-bioHeaders
[security policy](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/SECURITY.md),
including its private reporting addresses and conflict routing. Report suspected
vulnerabilities privately as described there, naming this repository
(`gff3-validator`) and the affected version or commit. Do not open a public
issue for a suspected vulnerability.

The validator reads untrusted files. Crashes, unbounded memory or time on crafted
input, and unescaped content in reports are in scope.

`gff3-validator` 0.1.x is the supported release line.
