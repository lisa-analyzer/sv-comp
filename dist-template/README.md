### JLiSA for SV-COMP

This archive contains the SV-COMP executable of JLiSA, the Java frontend of [LiSA](https://github.com/lisa-analyzer/lisa). It can include two tools:
- JLiSA, the verifier, run by `jlisa check`
- JLiSA-Wit, the violation witness validator, run by `jlisa validate`

`./jlisa components` lists the tools included in this archive, one per line.

#### Requirements
- Java 21 or higher, available as `java` (or through the JAVA_HOME environment variable)

#### Verifying a program

```bash
> ./jlisa check --property "<property-file.prp>" <input-1> <...> <input-N>
```

The last line of the output is the verdict: TRUE (the property holds), FALSE (the property is violated) or UNKNOWN. The results of the analysis, and the violation witness, are written to the folder `outputs/` in the working directory (the witness is `outputs/witness/witness.graphml`).

#### Validating a violation witness

```bash
> ./jlisa validate --witness "<witness-file>" --property "<property-file.prp>" <input-dir-1> <...> <input-dir-N>
```

As for SV-COMP validators, the verdict is about the property, and the last line of the output is one of:
- FALSE: the violation of the witness is reproduced, and the witness is confirmed (the line before it is `Witness Correct`)
- TRUE: the program runs with the values of the witness without the violation, and the witness is rejected as spurious (`Witness Spurious`)
- UNKNOWN: the witness could not be validated (`Could not validate`)

#### Supported properties
The two Java properties of SV-COMP, given as their property files:
- `valid-assert.prp`: no assertion fails
- `no-runtime-exception.prp`: no uncaught runtime exception is thrown

#### Smoketest

```bash
> ./smoketest.sh
```

It runs `jlisa check` (if JLiSA is included) and `jlisa validate` (if JLiSA-Wit is included) on the small programs and witnesses in `test/`, and fails if a verdict differs from the expected one.

#### Version

```bash
> ./jlisa version
```

Developed and maintained by the Software and System Verification (SSV) group @ Università Ca' Foscari Venezia, Italy
