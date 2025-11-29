# PHASE_4_PROMPT_ENHANCEMENT.md
## Dragon Wings Image Generator - Prompt Enhancement Roadmap

This document contains incremental prompts for improving image generation quality through three focused phases:

- **Phase 4A**: Prompt Assistance (hints + auto-improve)
- **Phase 4B**: Negative Prompt System (backend, invisible to users)
- **Phase 4C**: LoRA Style System (visual style picker)

---

## 🎯 Phase 4A: Prompt Assistance

**Goal:** Help users write better prompts without overwhelming them with a complex wizard.

### Prompt 4A.1: Add Token Counter and Prompt Tips

Add visual feedback showing prompt length and contextual writing tips.

Context:
- Current prompt textarea in `frontend/app/views/images/index.html.erb`
- CLIP tokenizer has 77-token limit (approx 1.3 tokens/word)
- Users don't know when prompts will be truncated

Tasks:
1. Add live token counter below prompt textarea showing "~X/77 tokens"
2. Color coding: green (<60), yellow (60-75), red (>75 with "will be truncated" warning)
3. Add collapsible "Prompt Tips" section with best practices:
   - "Be specific: 'golden retriever puppy' beats 'dog'"
   - "Include style: 'oil painting', 'photograph', '3D render'"
   - "Add lighting: 'golden hour', 'studio lighting', 'dramatic shadows'"
   - "Specify camera: 'close-up', 'wide angle', 'aerial view'"
4. Tips section collapsed by default, toggle with "?" icon

Token calculation: `Math.ceil(wordCount * 1.3)`

Don't modify form submission - just add visual helpers.

---

### Prompt 4A.2: Create Prompt Enhancement Service (Rails)

Build a service that improves weak prompts by adding quality-boosting keywords.

Context:
- Users often write minimal prompts like "a dog"
- Good prompts include style, lighting, quality descriptors
- Service should enhance without completely rewriting

New service: `app/services/prompt_enhancer_service.rb`

Tasks:
1. Create PromptEnhancerService with `enhance(prompt, model_key)` method
2. Detection logic for weak prompts:
   - Very short (< 5 words)
   - Missing quality keywords (detailed, high quality, etc.)
   - Missing style indicators
3. Enhancement rules:
   - If no quality terms: append "highly detailed, high quality"
   - If no lighting terms: append "professional lighting"
   - For photorealistic: append "photograph, photorealistic, 8k"
   - For openjourney: append "mdjrny-v4 style" (model trigger)
4. Return enhanced prompt string
5. Add `needs_enhancement?(prompt)` helper method

Keep enhancements subtle - augment, don't replace user intent.

---

### Prompt 4A.3: Add "Improve Prompt" Button to UI

Add button that applies prompt enhancement with user preview.

Context:
- PromptEnhancerService exists from 4A.2
- Need UI to trigger enhancement
- User should see and approve changes

Tasks:
1. Add "✨ Improve" button next to prompt textarea
2. On click:
   - Send AJAX request to new endpoint with current prompt
   - Receive enhanced version
   - Show modal/popover comparing original vs enhanced
   - "Apply" button replaces textarea content
   - "Cancel" keeps original
3. Create `POST /images/enhance_prompt` endpoint in controller
4. Endpoint calls PromptEnhancerService and returns JSON
5. Disable button if prompt is empty

Button styled as secondary action, positioned at end of textarea row.

---

### Prompt 4A.4: Add Quick Prompt Suggestions

Add clickable suggestion chips for common enhancements.

Context:
- Even with enhance button, users benefit from quick additions
- Chips are faster than typing common terms

Tasks:
1. Add horizontal scrollable row of suggestion chips below textarea:
   - Lighting: "golden hour", "studio lighting", "dramatic shadows", "neon glow"
   - Style: "photorealistic", "oil painting", "watercolor", "digital art"
   - Quality: "highly detailed", "8k resolution", "sharp focus"
   - Camera: "close-up", "wide angle", "aerial view"
2. Clicking chip appends text to prompt (with comma separator)
3. Chip shows checkmark if term already in prompt
4. Chips grouped by category with subtle labels

Chips should be small, horizontal scroll on mobile.

---

## 🎯 Phase 4B: Negative Prompt System

**Goal:** Automatically apply quality-boosting negative prompts without user involvement.

### Prompt 4B.1: Create Negative Prompt Configuration (Python)

Add negative prompt configuration to Python backend.

Context:
- Backend at `backend/app/config.py` has MODEL_CONFIGS
- Negative prompts prevent common artifacts
- Users shouldn't need to manage these

Tasks:
1. Add to config.py:
   ```python
   BASE_NEGATIVE_PROMPT = (
       "blurry, deformed, distorted, disfigured, extra limbs, extra fingers, "
       "mutated hands, poorly drawn hands, poorly drawn face, mutation, ugly, "
       "bad anatomy, bad proportions, extra eyes, watermark, text, signature, "
       "logo, low quality, lowres, jpeg artifacts, cropped"
   )

   MODEL_NEGATIVE_PROMPTS = {
       "sd-v1-5": "",  # Base only
       "openjourney": "ugly, tiling, poorly drawn hands, out of frame",
       "sdxl": "cartoon, anime, low quality"
   }
   ```
2. Add helper function:
   ```python
   def get_negative_prompt(model_key: str, user_negative: str = None) -> str:
       # Combines: base + model-specific + user additions
   ```
3. Return combined string with proper comma separation

This is config only - don't modify generation yet.

---

### Prompt 4B.2: Apply Negative Prompts in Generation Pipeline

Wire negative prompt system into image generation.

Context:
- Config exists from 4B.1
- Generation in `backend/app/models.py`
- Currently uses user-provided negative_prompt only

Tasks:
1. Update `generate_image()` method:
   - Get full negative from `get_negative_prompt(model_key, user_negative)`
   - Pass to pipeline
2. Update `generate_image_from_image()` (img2img) same way
3. Log which negative prompts were applied (debug level)
4. If user provided negative_prompt, append to base (don't replace)

User negative prompts ADD to the system ones.

---

### Prompt 4B.3: Remove Negative Prompt Field from UI (Optional)

Simplify UI by hiding the negative prompt field since it's now automatic.

Context:
- Negative prompts now handled automatically
- Advanced users may still want access
- Could move to "Advanced" section

Tasks:
1. Move negative prompt textarea to Advanced Settings section
2. Collapse it by default
3. Add helper text: "System defaults are applied automatically. Add extras here."
4. Pre-populate with empty (system handles defaults)

OR keep as-is if we want users to still have easy access. Discuss with user.

---

## 🎯 Phase 4C: LoRA Style System

**Goal:** Allow users to select curated visual styles powered by LoRA adapters.

### Prompt 4C.1: Create LoRA Configuration (Python)

Set up LoRA adapter configuration in Python backend.

Context:
- Backend uses HuggingFace diffusers with LoRA support
- LoRA files stored in `backend/loras/` directory
- Each style = LoRA file + scale + prompt suffix + negative additions

Tasks:
1. Create `backend/loras/` directory
2. Add to config.py:
   ```python
   STYLE_CONFIGS = {
       "none": {
           "name": "None",
           "description": "No style applied",
           "lora_file": None,
           "lora_scale": 0.0,
           "prompt_suffix": "",
           "negative_additions": "",
           "compatible_models": ["sd-v1-5", "openjourney", "sdxl"]
       },
       "photorealistic": {
           "name": "Photorealistic",
           "description": "Ultra-realistic photography style",
           "lora_file": "photorealistic.safetensors",
           "lora_scale": 0.7,
           "prompt_suffix": "photorealistic, highly detailed, 8k, sharp focus",
           "negative_additions": "cartoon, anime, illustration, painting, drawing",
           "compatible_models": ["sd-v1-5"]
       },
       "cinematic": {
           "name": "Cinematic",
           "description": "Hollywood film aesthetic",
           "lora_file": "cinematic.safetensors",
           "lora_scale": 0.65,
           "prompt_suffix": "cinematic, film still, dramatic lighting, movie scene",
           "negative_additions": "amateur, snapshot, low budget",
           "compatible_models": ["sd-v1-5", "openjourney"]
       },
       "watercolor": {
           "name": "Watercolor",
           "description": "Traditional watercolor painting",
           "lora_file": "watercolor.safetensors",
           "lora_scale": 0.8,
           "prompt_suffix": "watercolor painting, soft edges, artistic",
           "negative_additions": "photorealistic, photograph, 3d render",
           "compatible_models": ["sd-v1-5"]
       },
       "anime": {
           "name": "Anime",
           "description": "Japanese anime style",
           "lora_file": "anime.safetensors",
           "lora_scale": 0.75,
           "prompt_suffix": "anime style, cel shaded, vibrant",
           "negative_additions": "photorealistic, photograph, western",
           "compatible_models": ["sd-v1-5"]
       }
   }
   ```
3. Add helpers:
   - `get_style_config(style_key)` - returns config or None
   - `get_available_styles(model_key)` - returns compatible styles
4. Create `loras/README.md` with instructions for adding LoRA files

---

### Prompt 4C.2: Implement LoRA Loading in Pipeline

Add LoRA loading and application to generation pipeline.

Context:
- Style configs exist from 4C.1
- StableDiffusionModel in `backend/app/models.py`
- Diffusers provides load_lora_weights() method

Tasks:
1. Add to StableDiffusionModel class:
   ```python
   def load_style(self, style_key: str) -> bool:
       # Load LoRA if style has one and file exists

   def unload_style(self):
       # Unload current LoRA
   ```
2. Update `generate_image()`:
   - Accept `style_key` parameter
   - If style_key: load LoRA, apply prompt_suffix, add negative_additions
   - Generate image
   - Unload LoRA
3. Handle missing LoRA files gracefully (log warning, generate without)
4. Apply style's negative_additions to negative prompt

---

### Prompt 4C.3: Update API Schemas for Style

Add style_key to API request/response schemas.

Context:
- LoRA loading works from 4C.2
- API needs to accept and validate style_key

Tasks:
1. Update `GenerateRequest` in schemas.py:
   - Add `style_key: Optional[str] = "none"`
   - Validate against STYLE_CONFIGS keys
2. Update `Img2ImgRequest` same way
3. Add `GET /api/styles` endpoint:
   - Returns available styles with name, description, compatible_models
4. Update generation response to include applied style
5. Add optional `lora_scale` override parameter (default uses config)

---

### Prompt 4C.4: Add Style Selector to Rails UI

Create visual style picker in the settings panel.

Context:
- API accepts style_key from 4C.3
- Need intuitive style selection
- Show compatibility with selected model

Tasks:
1. Add "Style" section to settings panel after model selector
2. Display as clickable cards (not dropdown):
   - Style name
   - One-line description
   - Visual indicator when selected
   - Disabled/grayed if incompatible with current model
3. Cards in 2-column grid (3 on larger screens)
4. "None" option as default
5. Wire to hidden input: `image[style_key]`
6. JavaScript to:
   - Handle selection toggle
   - Update disabled states when model changes
   - Fetch styles from `/api/styles` on page load

Style cards positioned after model, before dimensions.

---

### Prompt 4C.5: Wire Rails to Style API

Connect Rails frontend to Python style API.

Context:
- UI style selector from 4C.4
- API accepts style_key from 4C.3
- Need to pass through Rails

Tasks:
1. Update StableDiffusionService:
   - Add style_key param to generate() and generate_img2img()
2. Update ImagesController:
   - Permit style_key param
   - Pass to service
3. Store style_key in Image metadata
4. Display applied style on image cards in gallery
5. Enable "use same style" when clicking on existing image

---

### Prompt 4C.6: Add LoRA Scale Slider (Advanced)

Allow power users to adjust style intensity.

Context:
- LoRA scale controls style strength
- Default from config is usually good
- Some users want fine control

Tasks:
1. Add "Style Intensity" slider in Advanced Settings:
   - Only visible when style is selected (not "None")
   - Range: 0.0 to 1.0, step 0.05
   - Default: from style config
2. Wire to hidden input: `image[lora_scale]`
3. Pass to API, backend uses if provided (else config default)
4. Store in Image metadata

---

## Summary: Prompt Sequence

| Phase | Prompt | Description | Complexity |
|-------|--------|-------------|------------|
| 4A | 4A.1 | Token counter + prompt tips | Low |
| 4A | 4A.2 | Prompt enhancer service | Medium |
| 4A | 4A.3 | "Improve" button + preview | Medium |
| 4A | 4A.4 | Quick suggestion chips | Low |
| 4B | 4B.1 | Negative prompt config | Low |
| 4B | 4B.2 | Apply negatives in pipeline | Low |
| 4B | 4B.3 | Simplify UI (optional) | Low |
| 4C | 4C.1 | LoRA config registry | Low |
| 4C | 4C.2 | LoRA loading in pipeline | Medium |
| 4C | 4C.3 | API schemas for style | Low |
| 4C | 4C.4 | Style selector UI | Medium |
| 4C | 4C.5 | Wire Rails to style API | Low |
| 4C | 4C.6 | LoRA scale slider | Low |

**Estimated total: 13 prompts across 3 phases**

---

## File Changes by Phase

### Phase 4A: Prompt Assistance
- `frontend/app/views/images/index.html.erb` - Token counter, tips, chips
- `frontend/app/services/prompt_enhancer_service.rb` - NEW
- `frontend/app/controllers/images_controller.rb` - enhance_prompt endpoint
- `frontend/config/routes.rb` - new route

### Phase 4B: Negative Prompts
- `backend/app/config.py` - Negative prompt configs
- `backend/app/models.py` - Apply negatives in generate methods
- `frontend/app/views/images/index.html.erb` - Move negative field (optional)

### Phase 4C: LoRA Styles
- `backend/app/config.py` - STYLE_CONFIGS
- `backend/app/models.py` - LoRA load/unload methods
- `backend/app/schemas.py` - style_key field
- `backend/app/main.py` - /api/styles endpoint
- `backend/loras/` - NEW directory
- `frontend/app/views/images/index.html.erb` - Style cards UI
- `frontend/app/services/stable_diffusion_service.rb` - style_key param
- `frontend/app/controllers/images_controller.rb` - permit style_key

---

*Document Version: 1.0*
*Created: 2025-11-29*
*Approach: Incremental, 3 focused phases*
