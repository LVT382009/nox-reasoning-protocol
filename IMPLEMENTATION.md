# NOX (Neural Operational eXpression) - v1 Implementation

## Overview

NOX is a **latency-constrained proof-carrying e-graph compiler** for Hermes Agent that optimizes reasoning while preserving semantic correctness. It compiles natural language reasoning into a dense symbolic representation (NOX IR), optimizes it using bounded equality saturation, and decodes it back to natural language.

## Architecture

**Approach A′.2 — Latency-Constrained Proof-Carrying E-Graph Compiler with Stratified Grammar**

### Pipeline

```
User Query
  ↓
[Parser] BNF → Typed AST (10-15ms budget)
  ↓
[IR Generator] AST → NOX IR with types (5-10ms budget)
  ↓
[Path Classifier] Fast vs Deep path (1ms)
  ↓
  ├─ [Fast Path] Bounded rewrite optimization (15-20ms)
  │   ├─ Bounded rewrite selection (N=20, M=300)
  │   ├─ Limited local e-matching (no full saturation)
  │   ├─ Greedy extraction (no optimal extraction)
  │   ├─ Lightweight certificates (local legality, compositional)
  │   ├─ Adaptive rewrite backoff (disable bad rewrites)
  │   ├─ Rebuild budget (max passes, deferred threshold)
  │   └─ Progressive early stopping (5% improvement threshold)
  │
  └─ [Deep Path] Bounded equality saturation (25-30ms)
      ├─ Rich rewrite rules (N=100, M=2000)
      ├─ Bounded saturation loop
      ├─ Extraction budget (max candidates, timeout, greedy fallback)
      ├─ Full proof certificates (semantic preservation, equivalence)
      ├─ Adaptive rewrite backoff
      ├─ Rebuild budget
      ├─ Progressive early stopping (2% improvement threshold)
      │
      └─ [Rare Diagnostic Mode] SMT verification (offline only)
  ↓
[Abort Controller] Check: cost > gain? proof > benefit? growth > threshold? threatens 100ms?
  ↓ (if abort, fallback)
[Certificate Generator] Proof of semantic preservation (10-15ms budget)
  ↓
[Multi-Layer Verifier] Structural + Semantic + Compression + Determinism + Monotonicity (10-15ms budget)
  ↓
[Decoder] IR → Natural Language (10-20ms budget)
  ↓
Response
```

**Total Budget:** Target <75ms, Hard ceiling 100ms

## Components

### 1. Type System (`types.py`)

- **UncertaintyType:** CERTAIN, PROBABLE, HYPOTHETICAL, VERIFIED, UNVERIFIED, PRESERVED, IMMUTABLE
- **Type preservation rules:** Certainty cannot be downgraded, verification cannot be lost, hypothetical cannot become certain
- **Type-level rewrite legality:** Illegal rewrites are unrepresentable in type system

### 2. AST (`ast.py`)

- **Minimal v1 AST:** Fact, Rule, Inference, Assumption, Evidence, Constraint
- **Typed expressions:** All expressions carry uncertainty types
- **Fast-path detection:** `is_fast_path_statement()` checks if statement is allowed in fast path
- **Cost estimation:** `estimate_expression_cost()` and `estimate_statement_cost()`

### 3. IR (`ir.py`)

- **NOXIR:** E-graph representation with equivalence classes
- **NOXIRNode:** Single node with expression, class_id, cost, proof, tier
- **ProofCertificate:** Proof of semantic preservation (local_legality, compositional, full_semantic)
- **Bounded operations:** `is_bounded()` checks node and class limits
- **Determinism:** Seed-based deterministic operations

### 4. Parser (`parser.py`)

- **Pattern-based parsing:** Matches natural language patterns to NOX statements
- **Fast-path grammar subset:** Only simple facts, rules, inferences in fast path
- **Uncertainty extraction:** Detects uncertainty qualifiers in text
- **Error handling:** Returns ParseResult with errors and warnings

### 5. Rewrite Rules (`rewrite_rules.py`)

- **Stratified tiers:**
  - Tier 0: Always-safe canonicalization (normalize_double_negation, fold_identity_ops)
  - Tier 1: Fast-path rewrites (eliminate_redundant_qualifier, compress_boilerplate_connectors)
  - Tier 2: Deep-path eqsat rewrites (compress_implication_chain)
  - Tier 3: Experimental (disabled by default)
- **Cost metadata:** Each rule has estimated_token_gain, matcher_cost, proof_cost, egraph_growth_risk
- **Adaptive backoff:** Rules with poor performance are automatically disabled
- **Rule registry:** Central registry for all rules

### 6. Optimizer (`optimizer.py`)

- **Fast path:** Bounded rewrite optimization (N=20, M=300, 15ms budget, 5% threshold)
- **Deep path:** Bounded equality saturation (N=100, M=2000, 30ms budget, 2% threshold)
- **Abort Controller:** Checks cost vs gain, proof cost, time budget
- **Progressive early stopping:** Stops when improvement below threshold or time exhausted
- **Automatic fallback:** Returns original IR if optimization fails

### 7. Verifier (`verifier.py`)

- **Layer 1 - Structural:** Grammar validity, no missing nodes, no broken symbols, no corrupted classes
- **Layer 2 - Semantic:** Type preservation, uncertainty preservation, constraint preservation, no illegal rewrites
- **Layer 3 - Compression:** Compression gain, no over-compression, proof validity, determinism
- **Multi-layer verifier:** Combines all layers with overall result

### 8. Decoder (`decoder.py`)

- **Reversibility guarantee:** `decode(encode(x)) ≈ x` (semantic equivalence)
- **Determinism:** Same IR + same seed → same output
- **Type preservation:** Uncertainty types preserved in decoded text
- **Conservative mode:** Fallback to conservative decoding if reversibility check fails

### 9. Integration (`integration.py`)

- **NOXAgentIntegrator:** Main integration class for Hermes Agent
- **Automatic application:** `apply_nox_validation()` applies NOX to agent responses
- **Path selection:** Automatically chooses fast or deep path based on complexity
- **Fallback handling:** Automatic fallback to original response on any failure
- **Statistics tracking:** Tracks validations, time, savings, failures

## Invariants (Priority Order)

1. **Correctness** (semantic preservation, proof validity, fallback safety)
2. **Latency** (<100ms hard ceiling)
3. **Determinism** (same input → same output)
4. **Monotonic Optimization** (no oscillating transformations)
5. **Bounded Search** (no unbounded expansion/search)
6. **Compression** (consequence, not goal)

## Phase Roadmap

**Phase 1 (v1):**
- ✅ Fast path rewrite optimizer (no saturation)
- ✅ Deep path bounded eqsat
- ✅ Proof-carrying IR (tiered modes)
- ✅ Adaptive rewrite backoff
- ✅ Rebuild budget
- ✅ Automatic fallback
- ✅ <100ms ceiling
- ✅ 30-50% guaranteed safe compression

**Phase 2 (v2):**
- Persistent e-graph state
- Incremental equality maintenance
- Cached proof reuse
- Cross-query rewrite memoization
- 50-65% compression with verified optimizer

**Phase 3:**
- 70% compression only if formal reversibility proof passes

## Usage

### Enable NOX

```bash
/nox enable
```

### Check Status

```bash
/nox status
```

### Disable NOX

```bash
/nox disable
```

### Integration with Hermes Agent

NOX automatically applies to all agent responses when enabled via `/nox enable`. No manual invocation required.

## Performance Targets

**Fast Path (95% of queries):**
- Parser: 10-15ms
- IR Generation: 5-10ms
- Optimization: 15-20ms
- Certificate: 10-15ms
- Verification: 10-15ms
- Decoder: 10-20ms
- **Total: <75ms target, 100ms hard ceiling**

**Deep Path (5% of queries):**
- Same stages with larger budgets
- **Total: <100ms hard ceiling**

## Safety Features

- **Automatic fallback:** Falls back to original response on any failure
- **Abort Controller:** Pre-emptively aborts if cost exceeds benefit
- **Multi-layer verification:** Structural, semantic, and compression checks
- **Type-level legality:** Illegal rewrites unrepresentable in type system
- **Determinism:** Same input always produces same output
- **Proof-carrying IR:** Every transformation includes correctness certificate

## Files

- `types.py` - Type system with uncertainty types
- `ast.py` - Abstract syntax tree definitions
- `ir.py` - Intermediate representation with e-graph
- `parser.py` - Natural language to AST parser
- `rewrite_rules.py` - Stratified rewrite rules with cost metadata
- `optimizer.py` - E-graph optimizer with fast/deep paths
- `verifier.py` - Multi-layer verification system
- `decoder.py` - IR to natural language decoder
- `integration.py` - Hermes Agent integration

## Design Principles

- **Minimal v1:** Don't overdesign; start small and expand
- **Latency-aware grammar:** Fast-path subset by construction
- **Type-safe:** Illegal rewrites unrepresentable in type system
- **Bounded search:** No unbounded expansion or extraction
- **Greedy extraction:** Optimal extraction prohibited in hot path
- **Correctness > Latency > Compression:** Never sacrifice correctness for compression

## References

This implementation draws on:
- Equality saturation (egg, rose compilers)
- Proof-carrying code (CompCert)
- Type-preserving transformations
- Bounded optimization
- Stratified rewrite systems
