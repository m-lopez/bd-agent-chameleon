# Review: agent-name-config

**EDD:** `.planning/edd/0004-agent-name-config.md`
**Reviewer:** edd-reviewer
**Date:** 2026-02-16
**Verdict:** APPROVE WITH CHANGES

## Summary

EDD-0004 proposes adding a required `agent-name` key to role TOML configuration,
decoupling the config lookup key (TOML section header) from the agent identity
passed to Claude CLI via `--agent`. The change is small, well-scoped, and
architecturally sound. The document clearly identifies the four touch points
(models, config manager, launcher, TOML) and provides concrete code examples.
However, the document has gaps in test impact analysis, migration planning, and
documentation updates that should be addressed before implementation.

## Completeness

**Rating: Needs Improvement**

The core design change is well-specified, but several areas are incomplete:

1. **Missing test file coverage.** The EDD identifies `test_config_manager.py`
   and `test_claude_launcher.py` as needing updates, but omits two other files
   that construct `Role` objects directly and will break when `agent_name`
   becomes required:
   - `test_chameleon.py` line 50: `ROLE: Role = Role(name="reviewer", prompt="Review code.", interactive=False)`
   - `test_models.py` lines 86-89 and 97: Role construction and frozen tests.

2. **No Acceptance Criteria section.** EDDs 0001 and 0002 both include a
   checkbox-style Acceptance Criteria section. This EDD should follow the same
   convention to make the implementation verifiable.

3. **No ARCHITECTURE.md update plan.** The architecture doc explicitly states:
   > "Role source is the `role-X` label on the ticket, where X is the role name.
   > The role name is used as the `--agent` value and to look up configuration."

   This sentence becomes inaccurate after the change. The Role table in
   ARCHITECTURE.md also needs an `agent_name` row. The EDD should list
   `doc/ARCHITECTURE.md` as a modified file.

4. **Motivation lacks a concrete example.** The EDD says decoupling "allows role
   authors to choose descriptive config keys without being constrained by valid
   agent names, and vice versa." A concrete example showing when `name` and
   `agent_name` would actually differ would make the motivation compelling
   instead of theoretical. For instance: a TOML section `[pr-review-v2]` mapping
   to `agent-name = "code-reviewer"`.

## Feasibility

**Rating: Strong**

This is a straightforward, mechanical change with clear boundaries:

- The `Role` dataclass gains one field. Since it's `frozen=True`, all
  construction sites are statically identifiable.
- `ConfigManager.load_role()` reads one additional key from the TOML dict.
- `ClaudeLauncher._build_command()` switches one attribute access.
- No protocol changes needed (`SessionLauncher` takes `Role | None`, so
  the protocol signature is unaffected).
- The project uses `mypy --strict`, which will catch any missed construction
  sites at type-check time.

The change is fully implementable within the current architecture. No new
dependencies or structural modifications required.

## Risks

1. **Breaking change with no migration path.** Adding `agent-name` as required
   means existing TOML configs (including `.testing/simple-flow/config.toml`)
   will fail with `KeyError` if not updated simultaneously. The EDD acknowledges
   the TOML update but doesn't frame it as a migration concern. Since this is an
   early-stage project with one known config file, the risk is low, but the EDD
   should explicitly state that all existing configs must be updated atomically
   with the code change.

2. **No validation of `agent-name` values.** The Assumptions section states "No
   validation is needed beyond requiring the key to be present." This is
   reasonable for now, but an empty string or whitespace-only value would pass
   silently and produce a broken `claude --agent ""` invocation. Consider
   documenting this as an accepted risk or adding a simple non-empty assertion.

3. **Three-axis identity could cause confusion.** After this change, a role has
   three identity concepts: the TOML section header (config lookup key), the
   `role-X` label (ticket routing), and `agent-name` (Claude CLI identity). The
   relationship between the first two is implicit (they must match for routing to
   work) while the third is explicit. The EDD should clarify this three-way
   relationship, even if briefly.

4. **Assumption about `--agent` flag is unverified.** The EDD assumes Claude CLI
   accepts arbitrary strings for `--agent`. If this flag expects values matching
   a known agent registry, the decoupling benefit is reduced. This should be
   verified before implementation.

## Recommendation

**APPROVE WITH CHANGES** -- the design is sound and the change is well-scoped.
Address the following before implementation:

### Must Address

1. Add `test_chameleon.py` and `test_models.py` to the list of test files
   requiring updates, with specific notes on which `Role` construction sites
   need the new `agent_name` argument.

2. Add `doc/ARCHITECTURE.md` to the Changes section. At minimum, update the Role
   table and the sentence about role names being used as `--agent` values.

3. Add an Acceptance Criteria section, consistent with EDD-0001 and EDD-0002.
   Suggested criteria:
   - `Role` dataclass has an `agent_name: str` field.
   - `ConfigManager.load_role()` reads `agent-name` from TOML.
   - `ClaudeLauncher._build_command()` uses `role.agent_name` for `--agent`.
   - All TOML configs include `agent-name`.
   - Missing `agent-name` in TOML raises `KeyError`.
   - `make test` passes.
   - `mypy` passes with `--strict`.

### Should Consider

4. Add a concrete motivating example to the Motivation section showing a
   realistic case where `name` and `agent_name` would differ.

5. Note the migration requirement: all existing TOML configs must be updated in
   the same commit as the code change.

6. Briefly clarify the three-way identity relationship (TOML section header,
   `role-X` label, `agent-name`) in the Design Decisions or Assumptions section.

### Minor Nits

7. The Changes section lists `.testing/simple-flow/config.toml` as item 4 but
   the numbered list jumps from the TOML update (4) to Tests (5). Consider
   explicitly numbering the ARCHITECTURE.md update as a separate item.

### Strengths

- The Design Decisions table is excellent -- clear, concise, and well-reasoned.
- Code examples are concrete, correct, and directly implementable.
- The change is appropriately scoped -- small enough to review and implement
  confidently, but with enough context to understand the "why."
- Correctly identifies that `Role.name` is retained for logging and lookup.
