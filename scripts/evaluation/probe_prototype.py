"""Probe Adam's 2024 FHGFF3 validator prototype (python/gff3-validator.py)."""

import importlib.util
import sys
import traceback

proto, schema, *fixtures = sys.argv[1:]
spec = importlib.util.spec_from_file_location("proto", proto)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
for label, path in (("default (gff.py)", None), ("src/schema/gff.yaml", schema)):
    try:
        validator = module.GFF3Validator(path) if path else module.GFF3Validator()
        print(f"construct with {label}: ok")
    except Exception as error:
        print(f"construct with {label}: {type(error).__name__}: {str(error)[:150]}")
        continue
    for fixture in fixtures:
        try:
            result = validator.validate_file(fixture)
            print(f"  {fixture.rsplit('/', 1)[-1]}: {str(result)[:300]}")
        except Exception as error:
            frame = traceback.extract_tb(error.__traceback__)[-1]
            print(
                f"  {fixture.rsplit('/', 1)[-1]}: {type(error).__name__}: {str(error)[:120]} (line {frame.lineno}: {frame.line})"
            )
