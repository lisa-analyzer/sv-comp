### JLiSA for SV-COMP

This archive contains the SV-COMP executable of JLiSA, the Java frontend of [LiSA](https://github.com/lisa-analyzer/lisa). It includes two tools, both from the JLiSA package:
- JLiSA, the verifier, run by `jlisa check`
- JLiSA-Wit, the violation witness validator, run by `jlisa validate`

`./jlisa components` lists the tools included in this archive, one per line.

The archive also includes the [z3](https://github.com/Z3Prover/z3) SMT solver (`z3/z3`, with its license in `z3/LICENSE.txt`), that JLiSA uses to verify its warnings, confirming or refuting them.

#### Requirements
- Java 21 or higher, available as `java` (or through the JAVA_HOME environment variable)

#### Verifying a program

```bash
> ./jlisa check --property "<property-file.prp>" <input-1> <...> <input-N>
```

The last line of the output is the verdict: TRUE (the property holds), FALSE (the property is violated) or UNKNOWN. The results of the analysis are written to the folder `outputs/` in the working directory. When the verdict is FALSE because jlisa proves the violation, the violation witness is written to `witness.yml` in the working directory, in version 2.x of the SV-COMP witness format.

JLiSA uses the z3 executable included in the archive; `--z3 <path>` uses another one instead.

With `--bug-finding-fallback`, when jlisa ends with UNKNOWN or fails, the bug-finding mode of JLiSA-Wit looks for inputs that violate the property, running the program, for `--bug-finding-time-limit` seconds (default 120). A violation found gives FALSE, with its witness in `witness.yml`; otherwise the verdict stays UNKNOWN (it is never TRUE):

```bash
> ./jlisa check --bug-finding-fallback --property "<property-file.prp>" <input-dir-1> <...> <input-dir-N>
```

#### Validating a violation witness

```bash
> ./jlisa validate --witness "<witness-file>" --property "<property-file.prp>" <input-dir-1> <...> <input-dir-N>
```

As for SV-COMP validators, the verdict is about the property, and the last line of the output is one of:
- FALSE: the violation of the witness is reproduced, and the witness is confirmed (the line before it is `Witness Correct`)
- TRUE: the program runs with the values of the witness without the violation, and the witness is rejected as spurious (`Witness Spurious`)
- UNKNOWN: the witness could not be validated (`Could not validate`) or is a correctness witness, which is only parsed
- ERROR (invalid witness format): the witness has a version of the witness format other than 2.4 (`Invalid witness format`)
- ERROR (parsing failed): the witness cannot be read, e.g. a GraphML witness or an empty file (`Parsing failed`)
- ERROR (invalid witness type): with `--type violation` or `--type correctness`, the witness is of the other kind (`Invalid witness type`)

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
