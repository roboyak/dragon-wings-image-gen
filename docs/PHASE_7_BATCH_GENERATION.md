# Phase 7: Batch Generation

**Goal:** Generate multiple image variations from a single prompt with different seeds, allowing users to explore variations and compare results side-by-side.

**Status:** PLANNING
**Follows:** Incremental Development Skill (4-step sequence, one PR per prompt)
**Agent Assignments:** Phoenix UI, Phoenix Backend, Phoenix QA

---

## Architecture Decision

**Approach:** Parallel Job Creation
- Reuse existing `/api/generate` endpoint (no new batch endpoint needed)
- Create N separate jobs with incremental seeds
- Each job shows individual progress
- Users can favorite/manage each image independently
- Leverages existing polling and progress infrastructure

---

## Prompts

### Prompt 7.1: Add Batch Size Selector UI

**Objective:** Add batch size selection controls to the generation interface (UI only, no backend integration yet).

**Agent:** Phoenix UI
**Branch:** `feature/phase-7-prompt-1-batch-selector`
**PR:** After Phoenix QA approval

**Tasks:**
1. Add "Batch Size" section to the settings panel on image generation page
2. Create toggle button group: [1] [2] [4] images
3. Default selection: 1 (current behavior)
4. Style buttons to match existing design system (same pattern as model selector)
5. Add help text: "Generate multiple variations with different seeds"
6. Buttons should be disabled during generation (no function yet - just visual state)

**Acceptance Criteria:**
- Batch size selector renders in settings panel
- Buttons match existing UI patterns (min-h-8, text-xs, etc.)
- Active state uses primary color
- Help text displays below buttons
- No console errors
- Responsive at all breakpoints

**Don't modify:**
- Any existing form submission logic
- Image generation backend calls
- Current single-image workflow

**Handoff to:** Phoenix QA for visual regression and accessibility testing

---

### Prompt 7.2: Build Pending Images Grid Layout

**Objective:** Create UI layout to display multiple pending images in a grid during batch generation (structure only, no data yet).

**Agent:** Phoenix UI
**Branch:** `feature/phase-7-prompt-2-pending-grid`
**PR:** After Phoenix QA approval

**Tasks:**
1. Modify pending images section to support grid layout (2-column for 2 images, 2x2 for 4 images)
2. Add individual progress card for each pending image with:
   - Placeholder image area
   - Progress bar
   - Percentage text
   - Cancel button (non-functional yet)
3. Add "Generating N images..." header when batch > 1
4. Grid adapts to batch size:
   - 1 image: Current single card layout
   - 2 images: 2-column grid
   - 4 images: 2x2 grid
5. Responsive: Stack vertically on mobile

**Acceptance Criteria:**
- Grid layout renders correctly for 1/2/4 pending images
- Each card has space for progress bar and image
- Layout is responsive (mobile-friendly)
- No layout shift when switching between batch sizes
- Matches existing dark theme and spacing

**Don't modify:**
- Actual image generation logic
- Progress polling mechanism
- Completed images display

**Handoff to:** Phoenix QA for visual testing and responsive checks

---

### Prompt 7.3: Backend Seed Parameter Support

**Objective:** Ensure backend accepts and returns seed values for reproducible generation.

**Agent:** Phoenix Backend
**Branch:** `feature/phase-7-prompt-3-seed-support`
**PR:** After Phoenix QA and Phoenix Red approval

**Tasks:**
1. Verify `/api/generate` endpoint accepts optional `seed` parameter (integer)
2. If seed not provided, generate random seed and store it
3. Pass seed to Stable Diffusion pipeline during generation
4. Store seed in job metadata
5. Include seed in job status response (GET `/api/status/{job_id}`)
6. Include seed in completed image metadata
7. Validate seed is within valid range (0 to 2^32-1)

**Acceptance Criteria:**
- Endpoint accepts seed parameter without errors
- Random seed generated when not provided
- Seed stored and returned in status responses
- Same seed + prompt produces consistent images
- Seed validation prevents invalid values
- No breaking changes to existing generation flow

**Security Notes:**
- Validate seed is integer type
- Clamp seed to safe range
- Don't expose internal random number generator state

**Handoff to:**
- Phoenix QA for API testing
- Phoenix Red for security review of input validation

---

### Prompt 7.4: Connect Batch UI to Backend

**Objective:** Wire batch size selector to create multiple jobs with incremental seeds.

**Agent:** Phoenix Backend + Phoenix UI
**Branch:** `feature/phase-7-prompt-4-batch-submission`
**PR:** After Phoenix QA approval

**Tasks:**
1. Read batch size from form submission (from Prompt 7.1 UI)
2. When batch size > 1, create N separate image records and jobs
3. Generate seeds:
   - If user provided seed: use seed, seed+1, seed+2, seed+3
   - If no seed: generate N random seeds
4. Submit N jobs to backend with incremental seeds
5. Track all job IDs for polling
6. Display all pending images in grid (from Prompt 7.2)
7. Poll all jobs simultaneously and update individual progress bars
8. When each job completes, display image in grid
9. Add batch size parameter to form (default: 1)

**Acceptance Criteria:**
- Selecting batch size 2 creates 2 jobs
- Selecting batch size 4 creates 4 jobs
- Each job has unique seed (incremental or random)
- All jobs show individual progress in grid
- Each image displays when complete
- Existing single-image flow (batch=1) works unchanged
- No duplicate jobs created
- Progress updates in real-time for all images

**Don't modify:**
- Individual job generation logic
- Progress polling interval
- Image display after completion

**Handoff to:** Phoenix QA for E2E testing and regression testing

---

### Prompt 7.5: Add Batch Completion Features

**Objective:** Polish batch generation with completion notifications and seed display for regeneration.

**Agent:** Phoenix UI
**Branch:** `feature/phase-7-prompt-5-batch-polish`
**PR:** After Phoenix QA final approval

**Tasks:**
1. Add "All images complete!" notification when batch finishes
2. Display seed value on each completed image card (small text, bottom corner)
3. Add "Regenerate with this seed" button on hover (copies seed to form)
4. Ensure batch works with all features:
   - LoRA styles applied to all batch images
   - img2img mode works with batch
   - Inpainting works with batch
5. Add loading state to batch size buttons during generation
6. Clear pending grid when starting new batch

**Acceptance Criteria:**
- Notification appears when all batch images complete
- Seed visible on each image
- Regenerate button copies seed to form
- Batch works with LoRA, img2img, inpainting
- No UX issues (proper loading states, clean transitions)
- All existing features work with batch mode

**Optional Enhancement:**
- Comparison mode: Side-by-side view of batch results with favorite/discard options

**Handoff to:** Phoenix QA for full regression suite and final approval

---

## Testing Strategy

**Phoenix QA Testing Checklist (Per Prompt):**

**Prompt 7.1:**
- [ ] Batch selector renders correctly
- [ ] Buttons match design system
- [ ] Accessible (keyboard navigation, screen reader)
- [ ] Visual regression passes

**Prompt 7.2:**
- [ ] Grid layout correct for 1/2/4 images
- [ ] Responsive on mobile/tablet/desktop
- [ ] No layout shift or overflow issues
- [ ] Visual regression passes

**Prompt 7.3:**
- [ ] API accepts seed parameter
- [ ] Random seed generated when omitted
- [ ] Same seed produces same image
- [ ] Seed validation works
- [ ] No security vulnerabilities (Phoenix Red)

**Prompt 7.4:**
- [ ] Batch of 2 creates 2 jobs
- [ ] Batch of 4 creates 4 jobs
- [ ] Seeds are unique and incremental
- [ ] All progress bars update correctly
- [ ] Each image displays when ready
- [ ] Single image mode still works (batch=1)
- [ ] No duplicate jobs
- [ ] E2E test passes

**Prompt 7.5:**
- [ ] Completion notification appears
- [ ] Seeds display on images
- [ ] Regenerate copies seed to form
- [ ] Batch works with LoRA
- [ ] Batch works with img2img
- [ ] Batch works with inpainting
- [ ] Full regression suite passes
- [ ] Performance acceptable (4 images don't slow UI)

---

## Implementation Workflow

**For Each Prompt:**

1. **Phoenix Prime** routes task to appropriate agent
2. **Agent** (UI/Backend) implements the prompt
3. **Agent** creates branch: `feature/phase-7-prompt-N-description`
4. **Agent** commits changes
5. **Phoenix QA** tests according to checklist
6. **Phoenix Red** reviews (if security-sensitive, like Prompt 7.3)
7. If tests pass → Create PR
8. Merge PR after approval
9. Delete feature branch
10. Update SESSION.md with progress
11. Move to next prompt

**No prompt proceeds until previous prompt's PR is merged.**

---

## File Changes Summary

**Prompt 7.1:**
- `frontend/app/views/images/index.html.erb` - Add batch selector UI

**Prompt 7.2:**
- `frontend/app/views/images/index.html.erb` - Modify pending section for grid

**Prompt 7.3:**
- `backend/app/main.py` - Add seed parameter handling
- `backend/app/schemas.py` - Add seed field validation
- `backend/app/models.py` - Pass seed to SD pipeline

**Prompt 7.4:**
- `frontend/app/controllers/images_controller.rb` - Handle batch submission
- `frontend/app/services/stable_diffusion_service.rb` - Create multiple jobs
- `frontend/app/javascript/controllers/` - Polling for multiple jobs
- `frontend/app/views/images/index.html.erb` - Wire batch UI

**Prompt 7.5:**
- `frontend/app/views/images/index.html.erb` - Notifications, seed display
- `frontend/app/javascript/controllers/` - Regenerate with seed logic

---

## Success Criteria

**Phase 7 is complete when:**
- All 5 prompts implemented and tested
- All PRs merged to main
- Phoenix QA full regression passes
- Users can generate 1, 2, or 4 images in a batch
- Each image has unique seed and shows individual progress
- Seeds are visible and can be reused
- Batch works with LoRA, img2img, and inpainting
- No regressions in existing functionality
- Documentation updated (if needed by Phoenix Docs)

---

## Why This Approach Works

✅ **Incremental** - Each prompt is independently valuable
✅ **Testable** - Clear acceptance criteria per prompt
✅ **Safe** - No big bang integration, easy rollback
✅ **Agent-Friendly** - Clear assignments, no confusion
✅ **Quality-Gated** - QA approval required before next step
✅ **One PR per Prompt** - Clean git history, easy review
✅ **No Code Snippets** - AI chooses best implementation
✅ **Follows All Skills** - Incremental dev + QA + Agent architecture

---

**Ready to start with Prompt 7.1!**
