# Phase 3: Image-to-Image Generation

## 🎯 Overview

**Feature:** Image-to-image (img2img) generation - Allow users to upload a reference/seed image that influences the AI generation process.

**Status:** Planning
**Parent Issue:** Roadmap Future Features #1
**Complexity:** Medium
**Estimated PRs:** 4

---

## 📋 What is Image-to-Image Generation?

**Concept:** Instead of generating an image from pure noise, use an existing image as a starting point and transform it according to a text prompt.

**Use Cases:**
1. **Style Transfer:** "Turn this photo into a watercolor painting"
2. **Image Variation:** "Generate variations of this product image"
3. **Enhancement:** "Make this sketch more realistic"
4. **Scene Modification:** "Add sunset lighting to this landscape"

**Key Parameters:**
- **Init Image:** The uploaded reference image
- **Prompt:** Text describing desired transformation
- **Strength:** How much to transform (0.0-1.0)
  - 0.0 = almost identical to original
  - 1.0 = completely new image (like text-to-image)
  - Sweet spot: 0.3-0.7 for transformations

---

## 🏗️ Technical Architecture

### Backend Changes (Python FastAPI)

**1. Stable Diffusion img2img Pipeline**
- Switch from `StableDiffusionPipeline` to `StableDiffusionImg2ImgPipeline`
- Add image preprocessing (resize, convert to tensor)
- Support both pipelines (txt2img AND img2img)

**2. File Upload Handling**
- Accept multipart/form-data requests
- Validate image formats (PNG, JPG, WebP)
- Resize/normalize uploaded images (max 1024x1024)
- Temporary storage for uploaded images

**3. New API Endpoint**
```python
POST /api/generate_img2img
- Accepts: multipart/form-data
- Fields:
  - init_image: File (required)
  - prompt: str (required)
  - negative_prompt: str (optional)
  - strength: float (0.0-1.0, default: 0.75)
  - num_inference_steps: int (default: 50)
  - guidance_scale: float (default: 7.5)
  - seed: int (optional)
```

### Frontend Changes (Rails)

**1. Image Upload Component**
- File input field with drag-and-drop
- Image preview before upload
- Client-side validation (file type, size <10MB)
- Clear/remove uploaded image button

**2. Database Schema**
- Add `init_image_url` column to `images` table
- Add `strength` column (decimal)
- Add `generation_type` enum: 'text_to_image', 'image_to_image'

**3. ActiveStorage Integration**
- Store uploaded seed images
- Serve via Rails Active Storage
- Link to generated images

**4. UI Enhancements**
- Toggle between text-to-image and image-to-image modes
- Strength slider (0.0-1.0) with visual indicator
- Side-by-side preview: original vs. generated

---

## 📐 Incremental Development Plan

Following the **Four-Step Prompt Sequence** from incremental-development-skill.md:

### Phase 3.1: Backend img2img Support (PR #5)

**Objective:** Add image-to-image generation capability to Python backend

**Tasks:**
1. Install additional dependencies
   ```bash
   pip install Pillow  # Already installed
   ```

2. Create new endpoint `/api/generate_img2img`
   - Accept multipart/form-data
   - Validate uploaded image
   - Preprocess image (resize, convert)

3. Add `StableDiffusionImg2ImgPipeline` support
   - Load pipeline on demand
   - Keep text-to-image pipeline
   - Shared model weights

4. Add strength parameter validation (0.0-1.0)

5. Test endpoint with curl:
   ```bash
   curl -X POST http://localhost:8000/api/generate_img2img \
     -F "init_image=@test.jpg" \
     -F "prompt=A watercolor painting" \
     -F "strength=0.75"
   ```

**Files to Create/Modify:**
- `backend/app/main.py` - New endpoint
- `backend/app/models.py` - Add img2img pipeline
- `backend/app/schemas.py` - New request schema
- `backend/requirements.txt` - (No new deps needed)

**Testing Checklist:**
- [ ] Endpoint accepts file uploads
- [ ] Image preprocessing works (resize, format)
- [ ] img2img generation completes successfully
- [ ] Strength parameter affects output correctly
- [ ] Error handling for invalid images
- [ ] Both txt2img and img2img work simultaneously

---

### Phase 3.2: Database & Model Updates (PR #6)

**Objective:** Update Rails database schema to support image-to-image generation

**Tasks:**
1. Create migration to add columns to `images` table:
   ```ruby
   add_column :images, :init_image_url, :string
   add_column :images, :strength, :decimal, precision: 3, scale: 2
   add_column :images, :generation_type, :string, default: 'text_to_image'
   add_index :images, :generation_type
   ```

2. Update Image model:
   - Add `generation_type` enum: `text_to_image`, `image_to_image`
   - Add validations for `strength` (0.0-1.0)
   - Add scope: `scope :img2img, -> { where(generation_type: 'image_to_image') }`

3. Configure ActiveStorage for init images:
   - Add `has_one_attached :init_image` to Image model
   - Configure storage (local for dev, S3 for production)

4. Update seeds/test data with img2img examples

**Files to Create/Modify:**
- `frontend/db/migrate/YYYYMMDD_add_img2img_to_images.rb`
- `frontend/app/models/image.rb`
- `frontend/config/storage.yml` (if using S3)

**Testing Checklist:**
- [ ] Migration runs successfully
- [ ] New columns present in schema
- [ ] Image model validations work
- [ ] ActiveStorage attachment works
- [ ] Can create img2img records in console

---

### Phase 3.3: UI - Image Upload Component (PR #7)

**Objective:** Build image upload UI without backend integration

**Tasks:**
1. Add mode toggle to `/images` page:
   ```erb
   <div class="mode-toggle">
     <%= radio_button_tag :mode, 'text_to_image', true %>
     <%= label_tag :mode_text_to_image, 'Text to Image' %>

     <%= radio_button_tag :mode, 'image_to_image' %>
     <%= label_tag :mode_image_to_image, 'Image to Image' %>
   </div>
   ```

2. Create file upload section (hidden by default):
   ```erb
   <div id="img2img-section" style="display: none;">
     <div class="upload-area">
       <%= file_field_tag :init_image, accept: 'image/*' %>
       <div class="preview" id="image-preview"></div>
     </div>

     <div class="strength-slider">
       <%= label_tag :strength, 'Transformation Strength' %>
       <%= range_field_tag :strength, 0.75, min: 0, max: 1, step: 0.05 %>
       <span id="strength-value">0.75</span>
     </div>
   </div>
   ```

3. Add JavaScript for:
   - Toggle between modes (show/hide img2img section)
   - File input change handler
   - Image preview (FileReader API)
   - Strength slider value display
   - Client-side validation (file size, type)

4. Style upload area with Dragon Wings theme:
   - Drag-and-drop zone
   - Image preview with delete button
   - Strength slider with visual indicators

**Files to Create/Modify:**
- `frontend/app/views/images/index.html.erb`
- `frontend/app/assets/stylesheets/images.css` (new)
- Add JavaScript to existing `<script>` block

**Testing Checklist:**
- [ ] Mode toggle shows/hides img2img section
- [ ] File upload opens file picker
- [ ] Image preview displays correctly
- [ ] Can remove uploaded image
- [ ] Strength slider updates value display
- [ ] Client-side validation works
- [ ] UI matches Dragon Wings dark theme

---

### Phase 3.4: Integration & End-to-End (PR #8)

**Objective:** Connect Rails frontend to Python img2img backend

**Tasks:**
1. Update `StableDiffusionService`:
   ```ruby
   def self.generate_img2img(init_image:, prompt:, strength: 0.75, **options)
     response = post(
       '/api/generate_img2img',
       body: {
         init_image: init_image,  # File upload
         prompt: prompt,
         strength: strength,
         # ... other params
       },
       headers: { 'Content-Type' => 'multipart/form-data' }
     )
   end
   ```

2. Update `ImagesController#create`:
   - Check `params[:mode]` to determine generation type
   - Handle file upload with ActiveStorage
   - Call appropriate service method (txt2img or img2img)
   - Save init_image_url and strength

3. Update gallery view to show:
   - Generation type badge
   - Init image thumbnail (if img2img)
   - Strength value
   - Side-by-side comparison (before/after)

4. Add show page enhancements:
   - Display original image
   - Show transformation strength
   - "Generate Variation" button (same init image, new seed)

**Files to Modify:**
- `frontend/app/services/stable_diffusion_service.rb`
- `frontend/app/controllers/images_controller.rb`
- `frontend/app/views/images/index.html.erb`
- `frontend/app/views/images/show.html.erb`

**Testing Checklist:**
- [ ] Can upload image and generate img2img
- [ ] Init image stored via ActiveStorage
- [ ] Strength parameter affects output
- [ ] Gallery shows both txt2img and img2img
- [ ] Side-by-side comparison works
- [ ] Real-time polling works for img2img
- [ ] Download includes both original and generated
- [ ] Quota system counts img2img generations
- [ ] Error handling for failed uploads

---

## 🎨 UI/UX Mockup

### Image-to-Image Mode

```
┌──────────────────────────────────────────────────────────────┐
│  Mode: ⚪ Text to Image   ⚫ Image to Image                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  📁 Upload Seed Image                                        │
│  ┌────────────────────────────────────┐                     │
│  │   Drag & drop image here          │                     │
│  │   or click to browse               │                     │
│  │                                     │                     │
│  │   [  Preview if uploaded  ]         │                     │
│  └────────────────────────────────────┘                     │
│                                                              │
│  🎚️ Transformation Strength: ━━━━●━━━━ 0.75                │
│     Low (keep original) ←--------→ High (transform more)    │
│                                                              │
│  Prompt:                                                     │
│  ┌────────────────────────────────────┐                     │
│  │ Turn this into a watercolor painting │                   │
│  └────────────────────────────────────┘                     │
│                                                              │
│  [Advanced Settings ▼]                                       │
│                                                              │
│  [ Generate Image ]                                          │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  Recent Generations                                          │
│  ┌─────────┐  ┌─────────┐                                   │
│  │ Before  │  │ After   │  "Watercolor style"               │
│  │ [thumb] │→ │ [thumb] │  Strength: 0.75                   │
│  └─────────┘  └─────────┘  2 minutes ago                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔍 Key Technical Decisions

### 1. **Pipeline Strategy**
**Decision:** Load both txt2img and img2img pipelines, share weights
**Rationale:**
- Avoids switching overhead
- Users may use both modes in same session
- Memory overhead minimal (shared model weights)

### 2. **File Storage**
**Decision:** Use ActiveStorage for init images
**Rationale:**
- Built into Rails
- Easy S3 integration for production
- Automatic variants (thumbnails)
- Already used for generated images

### 3. **Strength Default**
**Decision:** Default strength = 0.75
**Rationale:**
- Sweet spot for transformations
- Not too conservative (0.3-0.5)
- Not too aggressive (0.9-1.0)
- Matches Stable Diffusion community standards

### 4. **Image Size Limits**
**Decision:** Max 1024x1024, resize larger images
**Rationale:**
- CPU generation already slow
- Larger = exponentially slower
- 1024x1024 is SD model max for v1.5
- User can always upscale after

---

## 🧪 Testing Strategy

### Backend Tests (Python)
```python
def test_img2img_generation():
    # Test successful generation
    # Test invalid image format
    # Test strength bounds (0.0-1.0)
    # Test image preprocessing
```

### Frontend Tests (Rails)
```ruby
describe ImagesController do
  context 'img2img generation' do
    it 'creates image with uploaded init_image'
    it 'validates strength parameter'
    it 'rejects invalid file types'
    it 'increments quota for img2img'
  end
end
```

### Integration Tests
- Upload image → generate → verify output
- Test both modes in same session
- Verify storage of init images
- Check quota enforcement

---

## 📊 Success Metrics

**Phase 3 Complete When:**
- [ ] Can upload image and generate img2img
- [ ] Both txt2img and img2img work simultaneously
- [ ] Strength slider affects output visibly
- [ ] Gallery shows before/after comparison
- [ ] No regressions in text-to-image mode
- [ ] All 4 PRs merged
- [ ] End-to-end demo successful

**Performance Targets:**
- img2img generation time: ~30-50% faster than txt2img (fewer steps needed)
- File upload: <1s for images <10MB
- Image preprocessing: <2s

---

## 🚀 Future Enhancements (Phase 4+)

After Phase 3 complete, could add:
- **Inpainting:** Edit specific areas with mask
- **Controlnet:** Pose/edge guidance
- **Batch img2img:** Multiple variations from one seed
- **Style presets:** One-click style transfers
- **Image history:** Compare multiple generations side-by-side

---

## 💡 Why This is a GREAT Idea

### ✅ Pros
1. **High User Value:** Transforms product from "cool toy" to "useful tool"
2. **Competitive Feature:** Matches Midjourney, DALL-E capabilities
3. **Low Risk:** Incremental addition, doesn't break existing features
4. **Well-Documented:** Stable Diffusion img2img is battle-tested
5. **Natural Progression:** Builds on existing text-to-image foundation
6. **Demo Appeal:** Visual before/after is compelling

### ⚠️ Considerations
1. **Storage:** Init images require storage (mitigated: ActiveStorage)
2. **Upload Speed:** Large files take time (mitigated: client-side compression)
3. **Complexity:** More UI elements (mitigated: progressive disclosure)

### 🎯 Recommendation
**GO FOR IT!** This is the perfect next feature following our proven incremental methodology. The 4-PR sequence keeps risk low while delivering high-value functionality.

---

## 📅 Timeline Estimate

Assuming similar velocity to Phase 2.3:

- **PR #5:** Backend img2img support - ~2 hours
- **PR #6:** Database & model updates - ~1 hour
- **PR #7:** UI components - ~2 hours
- **PR #8:** Integration & testing - ~2 hours

**Total:** ~7 hours for complete Phase 3 implementation

**Ready to start?** Begin with Phase 3.1: Backend img2img Support! 🚀
