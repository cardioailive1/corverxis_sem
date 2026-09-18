/**
 * Screen recording ingestion for the Skill Compiler — the second real
 * modality, alongside log (see logPipeline.js). Converts a video file into
 * the EXACT SAME observation-sequence shape ingestLogDemonstration()
 * produces ([{index, action, target, value, raw}, ...]) — meaning
 * Stages 2-5 (extraction, verification, abstraction, compilation) already
 * built in logPipeline.js work completely unchanged on the result. This
 * file only ever needs to solve Stage 1: turning raw video into that
 * structured shape.
 *
 * `video` (general/physical-world footage) and `motion_capture`
 * (robotics joint/pose data) remain separate, harder problems, NOT solved
 * here — same honest scoping as log vs. video/motion_capture in
 * processCompilerJob. This module handles `screen_recording` specifically:
 * a UI being interacted with, the modality the design document itself
 * recommended starting with.
 *
 * Frame extraction uses ffmpeg-static (a self-contained npm binary, no
 * system apt-get needed — confirmed working directly, including a real
 * end-to-end test: generated a synthetic video, extracted real frames,
 * confirmed valid images). Per-frame action inference calls Claude's
 * vision API — that part could NOT be tested end-to-end in the
 * environment this was built in (no live API key available there); same
 * honesty boundary as logPipeline.js's Claude-calling stages.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const crypto = require('crypto');
const { execFile } = require('child_process');
const ffmpegPath = require('ffmpeg-static');

const FRAME_INTERVAL_SECONDS = 1;   // 1 frame/sec — reasonable default for UI interactions, which don't change every video frame the way motion does
const MAX_FRAMES = 40;              // hard cap — bounds both ffmpeg's output and the number of Claude calls a single job can trigger

function runFFmpeg(args) {
  return new Promise((resolve, reject) => {
    execFile(ffmpegPath, args, { timeout: 120000 }, (err, stdout, stderr) => {
      if (err) {
        // ffmpeg's stderr includes its full version/build banner ahead of
        // the actual error — keep only the last few lines, which is where
        // the real, useful failure reason actually lives.
        const usefulLines = (stderr || err.message).trim().split('\n').slice(-3).join(' ');
        return reject(new Error(usefulLines));
      }
      resolve(stdout);
    });
  });
}

// ── Stage 1a: extract frames from the video — real, tested, no LLM call ──
async function extractFrames(videoBuffer) {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'osc-frames-'));
  const videoPath = path.join(workDir, 'input.mp4');
  fs.writeFileSync(videoPath, videoBuffer);

  const framePattern = path.join(workDir, 'frame-%04d.jpg');
  try {
    await runFFmpeg(['-y', '-i', videoPath, '-vf', `fps=1/${FRAME_INTERVAL_SECONDS}`, framePattern]);
  } catch (err) {
    fs.rmSync(workDir, { recursive: true, force: true });
    throw new Error(`Could not extract frames from this video — it may be corrupted or in an unsupported format. (${err.message})`);
  }

  let frameFiles = fs.readdirSync(workDir).filter(f => f.startsWith('frame-')).sort();
  if (frameFiles.length === 0) {
    fs.rmSync(workDir, { recursive: true, force: true });
    throw new Error('No frames could be extracted — the video may be empty or unreadable.');
  }
  if (frameFiles.length > MAX_FRAMES) {
    // Evenly downsample rather than just truncating the tail — keeps
    // coverage across the whole recording instead of only its first
    // MAX_FRAMES seconds.
    const step = frameFiles.length / MAX_FRAMES;
    frameFiles = Array.from({ length: MAX_FRAMES }, (_, i) => frameFiles[Math.floor(i * step)]);
  }

  const frames = frameFiles.map(f => fs.readFileSync(path.join(workDir, f)));
  fs.rmSync(workDir, { recursive: true, force: true });
  return frames;
}

// ── Stage 1b: infer the action between each consecutive frame pair ───────
function buildFrameTransitionPrompt() {
  return `These two images are consecutive frames from a screen recording, roughly ${FRAME_INTERVAL_SECONDS} second(s) apart. Identify the single most likely user action that occurred between them (e.g. a click, typing into a field, selecting a menu option, navigating to a new screen).

Respond with ONLY a JSON object in the form:
{"action": "click"|"type"|"navigate"|"select"|"none", "target": "<short description of what was interacted with, e.g. 'submit button', 'search field'>", "value": "<text entered, if action is type, else null>"}

If nothing meaningfully changed between the frames, respond with {"action": "none", "target": null, "value": null}.
No other text.`;
}

async function inferActionBetweenFrames(anthropicClient, frameBefore, frameAfter) {
  const msg = await anthropicClient.messages.create({
    model: 'claude-sonnet-4-6', max_tokens: 300,
    messages: [{ role: 'user', content: [
      { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: frameBefore.toString('base64') } },
      { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: frameAfter.toString('base64') } },
      { type: 'text', text: buildFrameTransitionPrompt() },
    ]}],
  });
  const text = msg.content[0]?.text || '{}';
  return parseJSONResponseLocal(text);
}

// Same markdown-fence-stripping fix already proven necessary in
// logPipeline.js — Claude wrapping JSON in ```json fences is a real,
// confirmed failure mode there, and there's no reason to assume vision
// responses would behave differently. Duplicated here (not imported)
// deliberately, so this module has no hard dependency on logPipeline.js's
// internals — the two ingestion paths only need to agree on the OUTPUT
// shape, not share implementation.
function parseJSONResponseLocal(text) {
  let cleaned = text.trim();
  if (cleaned.startsWith('```')) {
    cleaned = cleaned.replace(/^```(?:json)?\s*/, '').replace(/```\s*$/, '').trim();
  }
  return JSON.parse(cleaned);
}

// ── The full Stage 1 for screen_recording — produces the exact same
// shape ingestLogDemonstration() does, so Stages 2-5 need zero changes. ──
async function ingestScreenRecordingDemonstration(videoBuffer, anthropicClient) {
  const frames = await extractFrames(videoBuffer);
  if (frames.length < 2) {
    throw new Error('Video is too short to infer any actions from — need at least 2 distinct frames.');
  }

  const observationSequence = [];
  for (let i = 0; i < frames.length - 1; i++) {
    let inferred;
    try {
      inferred = await inferActionBetweenFrames(anthropicClient, frames[i], frames[i + 1]);
    } catch (err) {
      // One unparseable/failed frame pair shouldn't kill the whole
      // ingestion — record it as a "none" step rather than aborting,
      // same spirit as processTrainingRun not letting one bad scenario
      // kill an entire training run.
      inferred = { action: 'none', target: null, value: null, _inference_error: err.message };
    }
    if (inferred.action === 'none') continue;   // no meaningful change between these frames — skip, don't pad the sequence with no-ops
    observationSequence.push({
      index: observationSequence.length,
      action: inferred.action,
      target: inferred.target ?? null,
      value: inferred.value ?? null,
      raw: inferred,
    });
  }

  if (observationSequence.length === 0) {
    throw new Error('No meaningful actions could be inferred from this recording — every consecutive frame pair looked unchanged.');
  }
  return observationSequence;
}

module.exports = {
  extractFrames, buildFrameTransitionPrompt, inferActionBetweenFrames,
  ingestScreenRecordingDemonstration, FRAME_INTERVAL_SECONDS, MAX_FRAMES,
};
