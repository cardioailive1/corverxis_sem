/**
 * The real Skill Compiler pipeline, for `log` modality demonstrations
 * specifically — a structured JSON action sequence (clicks, form fills,
 * API calls, etc.), the modality the design document recommended starting
 * with: exact, structured input, no computer-vision perception problem to
 * solve first.
 *
 * `video` / `screen_recording` / `motion_capture` demonstrations still use
 * the placeholder in processCompilerJob — parsing raw video/screen
 * recordings into structured observations is a genuinely separate,
 * harder computer-vision problem, not solved here. Being explicit about
 * that boundary rather than quietly pretending this pipeline handles
 * everything.
 *
 * Honest test-coverage note: Stage 1 (ingestion) and Stage 5 (compilation)
 * are pure logic, no LLM call — fully tested directly. Stages 2-4
 * (extraction, verification, abstraction) call Claude; their PROMPT
 * CONSTRUCTION is tested directly, but the actual API call/response
 * handling could not be run end-to-end in the environment this was built
 * in (no API key available there) — test this for real before trusting
 * it in production, the same honesty applied to SEM's GRPO training script.
 */

// ── Stage 1: Ingestion — pure logic, no LLM call ────────────────────────────
// A log demonstration file is expected to be a JSON array of steps, each
// with at minimum an `action` field. This validates and normalizes it into
// the common observation-sequence shape every later stage expects,
// regardless of exactly how the source log was formatted.
function ingestLogDemonstration(buffer) {
  let raw;
  try {
    raw = JSON.parse(buffer.toString('utf-8'));
  } catch (err) {
    throw new Error('Log file is not valid JSON: ' + err.message);
  }
  if (!Array.isArray(raw)) {
    throw new Error('Log file must be a JSON array of steps.');
  }
  if (raw.length === 0) {
    throw new Error('Log file contains no steps.');
  }
  return raw.map((step, i) => {
    if (!step || typeof step !== 'object' || !step.action) {
      throw new Error(`Step ${i} is missing a required "action" field.`);
    }
    return {
      index: i,
      action: step.action,
      target: step.target ?? null,
      value: step.value ?? null,
      // Anything else the source log included is preserved, not dropped —
      // later stages that don't need it simply ignore the extra fields.
      raw: step,
    };
  });
}

// ── Stage 2: Causal Extraction — calls Claude ───────────────────────────────
function buildExtractionPrompt(observationSequence) {
  const stepsText = observationSequence.map(s =>
    `${s.index}. action="${s.action}"${s.target ? ` target="${s.target}"` : ''}${s.value ? ` value="${s.value}"` : ''}`
  ).join('\n');
  return `You are analyzing a demonstration of a task, captured as a sequence of steps. Your job is to identify the CAUSAL STRUCTURE — which steps are genuinely necessary for the task to work, and which are likely incidental (specific to this one recording, not the underlying task).

Steps:
${stepsText}

For each step, decide:
- necessary: true if this step's presence, and its position relative to other necessary steps, is required for the task to succeed
- necessary: false if this looks like it could vary without breaking the task (e.g. a specific value that happened to be used this one time)
- depends_on: the index of any OTHER necessary step that must happen before this one, or null if there's no such dependency

Respond with ONLY a JSON array, one object per step, in the form:
[{"index": 0, "necessary": true, "depends_on": null, "reasoning": "<one short sentence>"}, ...]
No other text.`;
}

async function extractCausalStructure(anthropicClient, observationSequence) {
  const prompt = buildExtractionPrompt(observationSequence);
  const msg = await anthropicClient.messages.create({
    model: 'claude-sonnet-4-6', max_tokens: 2000,
    messages: [{ role: 'user', content: prompt }],
  });
  const text = msg.content[0]?.text || '[]';
  const parsed = JSON.parse(text);   // let a malformed response surface as a real error, not a silently wrong empty structure
  return { steps: parsed };
}

// ── Stage 3: Verification — calls Claude, stands in for real perturbation
// testing (sandboxed re-execution isn't available for an arbitrary log
// demonstration — there's no generic sandbox to replay an unknown action
// sequence against). This is a genuine, explicit limitation, not hidden:
// a self-consistency check is a weaker signal than actually re-running the
// procedure and observing the outcome. ────────────────────────────────────
function buildVerificationPrompt(observationSequence, extraction) {
  const stepsText = observationSequence.map(s => `${s.index}. ${s.action}${s.target ? ' ' + s.target : ''}`).join('\n');
  const claimsText = extraction.steps.map(s => `Step ${s.index}: necessary=${s.necessary}, depends_on=${s.depends_on} — "${s.reasoning}"`).join('\n');
  return `Original steps:
${stepsText}

A first-pass analysis proposed this causal structure:
${claimsText}

Check this analysis for internal consistency. Specifically: does any step marked necessary=false actually appear to be a genuine precondition for a LATER step marked necessary=true? If so, that's an error — flag it.

Respond with ONLY a JSON array, one object per step, in the form:
[{"index": 0, "necessary": true, "confidence": "high"|"medium"|"low", "note": "<only if you disagree with the first pass, else empty string>"}, ...]
No other text.`;
}

async function verifyStructure(anthropicClient, observationSequence, extraction) {
  const prompt = buildVerificationPrompt(observationSequence, extraction);
  const msg = await anthropicClient.messages.create({
    model: 'claude-sonnet-4-6', max_tokens: 2000,
    messages: [{ role: 'user', content: prompt }],
  });
  const text = msg.content[0]?.text || '[]';
  const parsed = JSON.parse(text);
  const anyLowConfidence = parsed.some(s => s.confidence === 'low' || s.note);
  return {
    steps: parsed,
    confidence_notes: anyLowConfidence
      ? 'Verification flagged at least one step for human review — see individual step notes.'
      : null,
  };
}

// ── Stage 4: Abstraction — calls Claude ─────────────────────────────────────
function buildAbstractionPrompt(observationSequence, verifiedStructure) {
  const necessarySteps = observationSequence.filter((s, i) =>
    verifiedStructure.steps.find(v => v.index === i)?.necessary
  );
  const stepsText = necessarySteps.map(s =>
    `${s.index}. action="${s.action}"${s.target ? ` target="${s.target}"` : ''}${s.value ? ` value="${s.value}"` : ''}`
  ).join('\n');
  return `Convert these necessary steps into a generalized, reusable procedure by replacing specific values with typed placeholders (e.g. a specific username becomes {{username: string}}, a specific dollar amount becomes {{amount: number}}). Keep target element names as-is unless they're clearly instance-specific IDs.

Steps:
${stepsText}

Respond with ONLY a JSON array in the form:
[{"index": 0, "action": "...", "target": "...", "value": "...", "parameters": {"<name>": "<type>"}}, ...]
No other text.`;
}

async function abstractProcedure(anthropicClient, observationSequence, verifiedStructure) {
  const prompt = buildAbstractionPrompt(observationSequence, verifiedStructure);
  const msg = await anthropicClient.messages.create({
    model: 'claude-sonnet-4-6', max_tokens: 2000,
    messages: [{ role: 'user', content: prompt }],
  });
  const text = msg.content[0]?.text || '[]';
  return { steps: JSON.parse(text) };
}

// ── Stage 5: Compilation — pure logic, no LLM call ──────────────────────────
// Deterministic transformation from the abstracted procedure into the
// demonstration's actual target output format. No ambiguity here — this
// is just reshaping already-verified, already-abstracted data.
function compileToTarget(abstractedProcedure, targetOutput) {
  if (targetOutput === 'agent') {
    return {
      format: 'agent_tool_calls',
      tool_calls: abstractedProcedure.steps.map(s => ({
        tool: s.action, parameters: { target: s.target, value: s.value, ...s.parameters },
      })),
    };
  }
  if (targetOutput === 'checklist') {
    const lines = abstractedProcedure.steps.map((s, i) => {
      const params = s.parameters && Object.keys(s.parameters).length > 0
        ? ` (fill in: ${Object.entries(s.parameters).map(([k, v]) => `${k}: ${v}`).join(', ')})`
        : '';
      return `${i + 1}. ${s.action}${s.target ? ` on "${s.target}"` : ''}${params}`;
    });
    return { format: 'checklist', markdown: lines.join('\n') };
  }
  // 'robot' target isn't meaningful for a log-modality demonstration —
  // there's no physical actuation implied by a UI action log. Surfacing
  // this as a clear error rather than silently producing nonsense output.
  throw new Error(`Target output "${targetOutput}" is not supported for log-modality demonstrations — only "agent" and "checklist" apply.`);
}

module.exports = {
  ingestLogDemonstration,
  buildExtractionPrompt, extractCausalStructure,
  buildVerificationPrompt, verifyStructure,
  buildAbstractionPrompt, abstractProcedure,
  compileToTarget,
};
