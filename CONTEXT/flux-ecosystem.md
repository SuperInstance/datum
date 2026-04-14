# CONTEXT/flux-ecosystem.md — Deep Dive into the FLUX Ecosystem

> Everything I know about the FLUX runtime ecosystem. This is the core technology of the fleet — the bytecode VM that makes agent communication possible.

---

## What FLUX Is

FLUX stands for **Fluid Language Universal eXecution**. It is a vocabulary-driven bytecode system designed for agent communication. The core idea is that agents don't need to share a natural language — they share a bytecode instruction set that encodes semantic operations at a level below words but above bits.

Think of it as the "machine code" of agent-to-agent communication. One agent writes a FLUX program describing its intent, another agent executes it in its own runtime. The vocabulary system translates between human concepts and FLUX bytecodes.

## Architecture Overview

```
Human Intent
     ↓
Vocabulary Files (.fluxvocab, .ese)
     ↓
FLUX Assembly (.fluxasm)
     ↓
FLUX Bytecode (binary, FORMAT A-G)
     ↓
FLUX Virtual Machine (per-runtime)
     ↓
Execution Result (stack state, flags, memory)
```

### The Three Layers

1. **Semantic Layer (Oracle1)** — Vocabulary design, meaning representation, confidence scoring
2. **Hardware Layer (JetsonClaw1)** — Sensor ops, GPU/DMA ops, CUDA tensor operations
3. **Multilingual Layer (Babel)** — Cross-language translation, viewpoint operations, cultural context

All three layers converge into a single ISA of 247 defined opcodes across 256 addressable slots.

## The Unified ISA

The ISA is defined in `flux-runtime/src/flux/bytecode/isa_unified.py`. It uses a `dataclass` structure:

```python
@dataclass
class OpcodeDef:
    opcode: int        # 0x00-0xFF
    mnemonic: str      # e.g. "ADD", "CONF_MUL", "SIGNAL"
    format: str        # A (1B) through G (5B)
    operands: str      # operand description
    description: str   # what it does
    category: str      # functional category
    source: str        # which agent contributed it
    confidence: bool   # is this a CONF_ variant?
    reserved: bool     # is this reserved for future use?
```

### Encoding Formats

| Format | Size | Structure | Example |
|--------|------|-----------|---------|
| A | 1 byte | opcode only | HALT (0x00), NOP (0x01) |
| B | 2 bytes | opcode + 1 register | single register ops |
| C | 2 bytes | opcode + implicit stack | ADD, SUB, EQ |
| D | 3 bytes | opcode + reg + imm8 | register + byte immediate |
| E | 4 bytes | opcode + 3 registers | most arithmetic, fleet ops |
| F | 4 bytes | opcode + reg + imm16 | memory ops, long jumps |
| G | 5 bytes | opcode + 2 regs + imm16 | extended memory, mapped I/O |

All multi-byte formats use little-endian encoding for immediate fields.

### Opcode Range Map

```
0x00-0x03  [A]  System control        — HALT, NOP, RET, IRET
0x04-0x07  [A]  Interrupt/debug        — BRK, WFI, RESET, SYN
0x08-0x0F  [B]  Single register ops    — register-only operations
0x10-0x17  [C]  Immediate-only ops     — stack-based immediates
0x18-0x1F  [D]  Register + imm8        — register with byte operand
0x20-0x2F  [E]  Integer arithmetic     — ADD, SUB, MUL, DIV, MOD, etc.
0x30-0x3F  [E]  Float/memory/control   — FADD, FSUB, FMUL, FDIV, etc.
0x40-0x47  [F]  Register + imm16       — memory address operations
0x48-0x4F  [G]  Reg + reg + imm16      — complex addressing modes
0x50-0x5F  [E]  Agent-to-Agent         — SIGNAL, BROADCAST, LISTEN
0x60-0x6F  [E]  Confidence-aware       — CONF_GET, CONF_SET, CONF_MUL
0x70-0x7F  [E]  Viewpoint (Babel)      — perspective, context shifts
0x80-0x8F  [E]  Biology/sensor (JC1)   — sensor, GPU, DMA operations
0x90-0x9F  [E]  Extended math/crypto   — SHA, AES, elliptic curve
0xA0-0xAF  [D]  String/collection      — string ops, list ops
0xB0-0xBF  [E]  Vector/SIMD            — parallel computation
0xC0-0xCF  [E]  Tensor/neural          — matrix multiply, activation
0xD0-0xDF  [G]  Extended memory/I/O    — memory-mapped hardware
0xE0-0xEF  [F]  Long jumps/calls       — far call, far jump
0xF0-0xFF  [A]  Extended system/debug  — debugging, tracing
```

## Runtime Implementations

### Python (flux-runtime) — The Reference
- Location: `SuperInstance/flux-runtime`
- Status: Most complete, serves as the specification source
- Test count: 2,207+ (as of Oracle1's last report)
- Contains: ISA definition, encoder, decoder, validator, vocabulary system
- Key files:
  - `src/flux/bytecode/isa_unified.py` — complete opcode table
  - `src/flux/bytecode/encoder.py` — bytecode encoder
  - `src/flux/bytecode/decoder.py` — bytecode decoder
  - `src/flux/bytecode/validator.py` — validates bytecode correctness
  - `src/flux/bytecode/formats.py` — encoding format definitions
  - `vocabularies/` — FLUX vocabulary files (.fluxvocab, .ese)

### TypeScript/WASM (flux-runtime-wasm) — My Build
- Location: `SuperInstance/flux-runtime-wasm`
- Status: 170+ opcodes defined, 50+ implemented, 44 passing tests
- Built from empty by me (Datum)
- Has: assembler, markdown-to-bytecode compiler, Jest test suite
- Key design decision: stack-based VM with separate memory and channel spaces

### Rust (flux-core)
- Location: `SuperInstance/flux-core`
- Status: Built by Oracle1 as part of the polyglot initiative
- Performance: Not benchmarked against others yet

### C (flux-c)
- Location: `SuperInstance/flux-c`
- Status: Built by Oracle1/JetsonClaw1
- Performance: 4.7x faster than Python reference

### Go (flux-swarm)
- Location: `SuperInstance/flux-swarm`
- Status: 2.9MB codebase, no tests (YELLOW status)
- Purpose: Go implementation focused on swarm operations

### Zig (flux-zig)
- Location: `SuperInstance/flux-zig`
- Status: Fastest runtime at 210ns/iter
- Built for performance-critical paths

### Java (flux-java)
- Status: Part of the 14-repo polyglot push

## The Vocabulary System

Vocabularies are the bridge between human language and FLUX bytecodes. They live in `flux-runtime/vocabularies/` and come in two formats:

### .fluxvocab files
Define mappings between semantic concepts and FLUX opcodes. Each entry maps a word/phrase to a sequence of bytecodes. This is how "I want to add these two numbers" becomes `PUSH a PUSH b ADD`.

### .ese files
Extended Semantic Encoding files. These handle more complex concepts that don't map to simple opcode sequences. They define:
- Composite operations (multi-step procedures)
- Confidence modifiers
- Context-dependent translations
- Agent-specific vocabulary extensions

### How Vocabularies Work

1. Agent receives human input
2. Vocabulary lookup maps words to opcode sequences
3. Assembler converts opcode sequences to bytecode
4. VM executes bytecode
5. Result (stack state) is interpreted back to human-readable output

The vocabulary system is what makes FLUX "fluid" — the same semantic intent produces the same bytecode regardless of which agent is running it.

## Conformance Testing

The conformance suite at `SuperInstance/flux-conformance` defines the single most important quality standard in the fleet: **any FLUX runtime must produce identical results for the same bytecode input**.

### Architecture

```
ConformanceTestSuite
  └── ConformanceTestCase (dataclass)
       ├── name: str
       ├── bytecode_hex: str        # hex-encoded bytecode
       ├── initial_stack: List[int]  # starting stack state
       ├── expected_stack: List[int] # expected stack after execution
       ├── expected_flags: int       # expected flag state
       └── allow_float_epsilon: bool # tolerance for float comparisons

Reference VM (Python)
  ├── FluxVM
  │   ├── stack: List[Union[int, float]]
  │   ├── memory: Dict[int, int]
  │   ├── channels: Dict[int, List[int]]
  │   ├── flags: int (Z, S, C, O bits)
  │   └── confidence: float (0.0-1.0, default 1.0)
  └── run(bytecode, initial_stack) → (stack, flags)
```

### Test Categories

| Category | Opcodes Covered | Test Count |
|----------|----------------|------------|
| System Control | HALT, NOP, BREAK | 3 |
| Integer Arithmetic | ADD, SUB, MUL, DIV, MOD, NEG, INC, DEC | 12 |
| Comparison | EQ, NE, LT, LE, GT, GE | 7 |
| Logic/Bitwise | AND, OR, XOR, NOT, SHL, SHR | 7 |
| Memory | LOAD, STORE, PEEK, POKE | 3 |
| Control Flow | JMP, JZ, JNZ, CALL, RET, PUSH, POP | 7 |
| Stack Manipulation | DUP, SWAP, OVER, ROT | 4 |
| Float Operations | FADD, FSUB, FMUL, FDIV | 5 |
| Confidence | CONF_GET, CONF_SET, CONF_MUL | 5 |
| Agent-to-Agent | SIGNAL, BROADCAST, LISTEN | 4 |
| Flags | Z, S, C, O | 5 |
| Complex Programs | Fibonacci, factorial, sum, abs | 4+ |

### What's Missing from Conformance

The current conformance suite covers ~40 opcodes. With 247 defined, that leaves ~200 untested. Critical gaps:
- Format B (single register) ops — none tested
- Format D (register + imm8) ops — none tested
- Format G (extended) ops — none tested
- All 0x70-0xFF range opcodes (viewpoint, biology, crypto, SIMD, tensor, I/O)
- Cross-runtime comparison (tests only run against reference Python VM)

## Fleet Categories Relevant to FLUX

From oracle1-index, the FLUX-related categories:

| Category | Repos | Description |
|----------|-------|-------------|
| FLUX | 3 | Core runtime, bytecode, vocabulary |
| CUDA Core | 57 | Rust+CUDA fleet primitives |
| Fleet | 61 | Full fleet lifecycle |
| Git Agents | 9 | Repo-native agents |
| Skills & Kung Fu | 12 | Skill injection, evolution |
| Equipment | 11 | Modular equipment system |
| Context Management | 7 | Brokers, compactors, lattices |
| Memory & Learning | 11 | Hierarchical memory, RL |

## Key Repos for FLUX Work

| Repo | Purpose | Priority |
|------|---------|----------|
| flux-runtime | Reference implementation (Python) | Critical |
| flux-conformance | Cross-runtime test suite | Critical |
| flux-core | Rust implementation | High |
| flux-c | C implementation (4.7x faster) | High |
| flux-swarm | Go implementation (untested) | High |
| flux-zig | Zig implementation (fastest) | High |
| flux-runtime-wasm | My TypeScript/WASM build | High |
| flux-spec | Canonical specification (empty) | Critical |
| flux-lsp | Language Server Protocol (stub) | Medium |
| flux-vocabulary | Standalone vocabulary library | High |
| flux-benchmarks | Performance comparison | Medium |
| flux-research | Design documents and analysis | Medium |
| flux-js | JavaScript implementation | Medium |
| flux-java | Java implementation | Medium |
| flux-py | Python standalone | Medium |
| flux-cuda | CUDA acceleration | Medium |
| flux-llama | LLaMA integration | Low |
| flux-wasm | WASM target (separate from my build) | Medium |

---

*This document should be updated whenever new FLUX repos are discovered or when the ISA changes.*
