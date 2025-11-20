# Rails Frontend - Incremental Development Prompts

Following the Dragon Wings incremental development methodology, here are the step-by-step prompts for building the Rails frontend.

**Important:** Complete each prompt fully and test before moving to the next. Create one PR per prompt after successful testing.

---

## Phase 2: Rails Frontend Foundation

### Prompt 2.1: Initialize Rails Application

**Objective:** Set up new Rails 7 application with PostgreSQL and Tailwind CSS

**Tasks:**
1. Create new Rails 7 application named `dragon_wings_image_gen_frontend`
2. Configure PostgreSQL as database (development, test, production)
3. Install and configure Tailwind CSS with dark theme defaults
4. Create application layout with header, main content, and footer structure
5. Add root route that redirects to home page
6. Test: Rails server starts successfully on port 3000

**Don't modify:** Python backend code

**Testing Checklist:**
- [ ] `bin/rails server` starts without errors
- [ ] http://localhost:3000 loads successfully
- [ ] Dark background (slate-900) visible
- [ ] No console errors in browser
- [ ] Database creates successfully

---

### Prompt 2.2: Install and Configure Devise

**Objective:** Add user authentication system with Dragon Wings branding

**Context:**
- Application exists at `frontend/`
- Tailwind CSS configured with dark theme
- Reference Dragon Wings AI for styling patterns

**Tasks:**
1. Install Devise gem and run generators
2. Create User model with:
   - Email, password (Devise defaults)
   - Subscription tier enum (free, pro, enterprise)
   - Generation quota (integer, default 10 for free tier)
   - Generations today counter (integer, default 0)
3. Add Devise views and customize for dark theme:
   - Sign in page
   - Sign up page
   - Password reset pages
4. Create shared header partial with:
   - Dragon Wings AI Image Gen logo/title
   - Sign in / Sign up buttons (when logged out)
   - User menu (when logged in)
5. Style Devise forms to match Dragon Wings AI aesthetic
6. Test: User registration, login, and logout flows

**Styling Requirements:**
- Dark theme: bg-slate-900, text-slate-100
- Card-based forms with slate-800 background
- Sky-500 accent color for buttons
- Match Dragon Wings AI spacing and typography

**Testing Checklist:**
- [ ] User can register with email/password
- [ ] User can log in
- [ ] User can log out
- [ ] Validation errors display correctly
- [ ] Flash messages styled for dark mode
- [ ] Header shows correct state (logged in/out)

---

### Prompt 2.3: Create Image Generation Form

**Objective:** Build the main UI for generating images

**Context:**
- User authentication working (Devise)
- Users can log in/out
- No Python API integration yet - just build UI shell

**Tasks:**
1. Create ImagesController with actions:
   - `index` (gallery)
   - `new` (generation form)
   - `create` (submit generation)
   - `show` (view single image)
2. Create Image model (don't migrate yet):
   - user_id (belongs_to :user)
   - prompt (text, required)
   - negative_prompt (text, optional)
   - width, height (integers, default 512)
   - num_inference_steps (integer, default 30)
   - guidance_scale (decimal, default 7.5)
   - seed (integer, optional)
   - job_id (string, from Python API)
   - status (enum: pending, processing, completed, failed)
   - image_url (string)
   - generation_time (decimal)
3. Run migration
4. Create form view at `images/new.html.erb`:
   - Card layout matching Dragon Wings style
   - Prompt textarea (large, prominent)
   - Negative prompt textarea (collapsible "Advanced" section)
   - Parameter controls:
     - Image size dropdown (512x512, 768x768, 1024x1024)
     - Steps slider (10-50, default 30)
     - Guidance scale slider (1-20, default 7.5)
     - Seed input (optional, for reproducibility)
   - Generate button (primary style, sky-500)
5. Add route: `GET /images/new`
6. Add navigation link to "Generate Image" in header
7. Test: Form renders correctly, validation works

**Don't implement yet:**
- Python API calls
- Actual image generation
- Status polling

**Testing Checklist:**
- [ ] Form renders with all fields
- [ ] Navigation link works
- [ ] Form validates prompt presence
- [ ] Sliders work and show values
- [ ] Advanced section expands/collapses
- [ ] Mobile responsive

---

### Prompt 2.4: Create Python API Service

**Objective:** Integrate Rails with Python backend API

**Context:**
- Image generation form exists
- Python backend running on localhost:8000
- Users can submit generation requests (currently does nothing)

**Tasks:**
1. Create `app/services/stable_diffusion_api_service.rb`:
   - Initialize with base URL from ENV (PYTHON_API_URL)
   - Method: `generate_image(params)` - POST to /api/generate
   - Method: `check_status(job_id)` - GET to /api/status/:job_id
   - Method: `health_check` - GET to /api/health
   - Use Faraday or HTTParty gem
   - Handle timeouts and errors
2. Add to Gemfile:
   - `gem "faraday"` or `gem "httparty"`
3. Create `.env.example` with:
   - PYTHON_API_URL=http://localhost:8000
4. Add dotenv-rails gem to development/test group
5. Update ImagesController#create:
   - Call StableDiffusionApiService.generate_image
   - Save Image record with job_id and status='pending'
   - Redirect to status polling page
6. Create `images/show.html.erb`:
   - Show generation status
   - Display parameters used
   - Show "Generating..." message with spinner
7. Test: Submit form, verify API call happens, image record created

**Environment Setup:**
- Add PYTHON_API_URL to .env
- Restart Rails server to load env vars
- Ensure Python backend is running

**Testing Checklist:**
- [ ] Form submission creates Image record
- [ ] API call sent to Python backend
- [ ] job_id stored in database
- [ ] Status page shows "Generating..."
- [ ] Error handling works (backend down)
- [ ] Logs show API request/response

---

### Prompt 2.5: Add Status Polling and Image Display

**Objective:** Poll Python API for generation status and display completed images

**Context:**
- Generation form submits to Python API
- Image records created with job_id
- Status page exists but doesn't update

**Tasks:**
1. Add JavaScript polling to `images/show.html.erb`:
   - Poll `/images/:id/status` every 2 seconds
   - Update status text dynamically
   - Stop polling when status is 'completed' or 'failed'
   - Show image when completed
   - Show error message if failed
2. Add route: `GET /images/:id/status` (JSON endpoint)
3. Update ImagesController#status:
   - Call StableDiffusionApiService.check_status(job_id)
   - Update Image record with latest status
   - If completed:
     - Download image from Python backend
     - Save to Rails storage (ActiveStorage next prompt)
     - Update image_url
   - Return JSON with status and image_url
4. Add Turbo Frame for status updates (optional, for no-JS fallback)
5. Style completed image display:
   - Large image preview
   - Download button
   - Regenerate button (same params, new seed)
   - Share link (future)
6. Test: End-to-end generation flow

**Testing Checklist:**
- [ ] Status polls automatically
- [ ] Status updates in real-time
- [ ] Image displays when complete
- [ ] Download button works
- [ ] Generation time shown
- [ ] Error states handled
- [ ] Polling stops after completion

---

### Prompt 2.6: Add ActiveStorage and Image Gallery

**Objective:** Store images in Rails and build gallery view

**Context:**
- Images generate successfully
- Images currently fetched from Python backend URL
- No permanent storage in Rails yet

**Tasks:**
1. Install and configure ActiveStorage:
   - Run `bin/rails active_storage:install`
   - Run migration
   - Add `has_one_attached :image` to Image model
2. Update ImagesController#status:
   - When image completed, download from Python backend
   - Attach to Image record using ActiveStorage
   - Update image_url to Rails storage URL
3. Create gallery view at `images/index.html.erb`:
   - Grid layout (3-4 columns, responsive)
   - Each card shows:
     - Thumbnail
     - Prompt (truncated)
     - Generation date
     - Click to view full size
   - Pagination (Kaminari gem, 20 per page)
   - Filter: "My Images" (current user only)
4. Add scope to Image model: `scope :recent, -> { order(created_at: :desc) }`
5. Update navigation:
   - "Gallery" link in header
   - Show generation count for current user
6. Add empty state for new users:
   - "No images yet" message
   - "Generate your first image" button
7. Test: Gallery shows user images, pagination works

**Testing Checklist:**
- [ ] Images stored in ActiveStorage
- [ ] Gallery displays thumbnails
- [ ] Pagination works
- [ ] Click image to view full size
- [ ] Empty state shows for new users
- [ ] Mobile responsive grid

---

## Phase 3: Real-time Features

### Prompt 3.1: Add Server-Sent Events for Progress

**Objective:** Stream generation progress from Python backend (future enhancement)

**Context:**
- Basic generation works with polling
- Polling every 2 seconds is inefficient
- Want real-time updates

**Tasks:**
1. Create SSE endpoint in Python backend (modify backend code):
   - Add `/api/generate/stream/:job_id` endpoint
   - Stream progress updates (0%, 25%, 50%, 75%, 100%)
   - Use asyncio and yield for streaming
2. Create SseController in Rails:
   - Proxy SSE stream from Python backend
   - Add authentication check
3. Update JavaScript polling to use EventSource:
   - Replace setInterval with EventSource
   - Listen for progress events
   - Update progress bar in real-time
4. Add progress bar to status page:
   - Animated progress bar (sky-500)
   - Percentage text
   - Estimated time remaining
5. Test: Real-time progress updates

**This is advanced - can be deferred for MVP**

---

## Phase 4: Polish & Production

### Prompt 4.1: Add User Quota System

**Objective:** Enforce generation limits by subscription tier

**Context:**
- Users can generate unlimited images
- Need to add quota tracking
- Free tier: 10/day, Pro: 100/day

**Tasks:**
1. Add methods to User model:
   - `can_generate?` - check if under quota
   - `increment_generation_count!` - track usage
   - `reset_daily_quota!` - reset at midnight (cron job)
2. Update ImagesController#create:
   - Check `current_user.can_generate?`
   - Return error if quota exceeded
   - Increment counter after successful generation
3. Add quota display to header:
   - "5/10 generations today"
   - Progress bar
   - Link to upgrade (future)
4. Add quota exceeded page:
   - Friendly message
   - Show upgrade options
   - Show reset time (midnight)
5. Create rake task: `bin/rails quota:reset_daily`
6. Test: Quota enforcement works, reset task works

**Testing Checklist:**
- [ ] Free users limited to 10/day
- [ ] Quota displays correctly
- [ ] Exceeded message shows
- [ ] Reset task works
- [ ] Pro users have higher limit

---

### Prompt 4.2: Add Error Handling and Loading States

**Objective:** Professional UX with proper error and loading states

**Tasks:**
1. Add loading indicators:
   - Form submit button shows spinner
   - Disable button during generation
   - Status page shows animated loading
2. Improve error messages:
   - User-friendly text for common errors
   - API timeout: "Taking longer than expected..."
   - API down: "Service temporarily unavailable"
   - Bad prompt: Show validation errors
3. Add toast notifications (stimulus-notification):
   - Success: "Image generated!"
   - Error: "Something went wrong"
   - Auto-dismiss after 5 seconds
4. Add retry button on failures
5. Test: All error paths handled gracefully

---

### Prompt 4.3: Mobile Responsiveness

**Objective:** Ensure app works on mobile devices

**Tasks:**
1. Test on mobile viewport (375px, 768px, 1024px)
2. Fix form layout for mobile:
   - Stack sliders vertically
   - Larger touch targets (44px minimum)
   - Hide advanced options by default on mobile
3. Fix gallery layout:
   - 1 column on mobile
   - 2 columns on tablet
   - 3-4 columns on desktop
4. Fix header:
   - Hamburger menu on mobile
   - Collapsible user menu
5. Test on actual devices (iPhone, Android)

---

### Prompt 4.4: Add Tests

**Objective:** Automated test coverage for critical paths

**Tasks:**
1. Model tests (RSpec or Minitest):
   - User quota methods
   - Image validations
   - StableDiffusionApiService
2. Controller tests:
   - Authentication required
   - Form submission
   - Status polling
   - Gallery display
3. System tests (Capybara):
   - User registration → login → generate image → view gallery
   - Quota enforcement flow
4. Achieve 80%+ test coverage
5. Run tests in CI (GitHub Actions)

---

## Development Guidelines

### Before Starting Each Prompt

1. **Create feature branch:**
   ```bash
   git checkout -b feature/prompt-2.1-rails-init
   ```

2. **Verify prerequisites:**
   - Previous prompt completed and tested
   - Python backend running (for integration prompts)
   - All existing features still work

3. **Search for existing code:**
   - Check if similar functionality exists
   - Extend rather than duplicate

### After Completing Each Prompt

1. **Test thoroughly:**
   - Run through testing checklist
   - Test on different browsers
   - Check mobile responsiveness
   - Verify no regressions

2. **Clean up:**
   - Remove debug code
   - Delete commented code
   - Run linter
   - Update comments

3. **Create PR:**
   - Title: "Phase 2 Prompt 2.1: Initialize Rails Application"
   - Include testing checklist results
   - Add screenshots
   - Request review

4. **After merge:**
   - Delete branch
   - Pull latest main
   - Update CLAUDE.md progress tracker

---

## Success Criteria

Each prompt is complete when:
- [ ] All tasks checked off
- [ ] All tests pass (automated + manual)
- [ ] No console errors
- [ ] No regressions in existing features
- [ ] Mobile responsive (where applicable)
- [ ] Dark theme consistent
- [ ] Code reviewed and merged

---

## Quick Reference

### Current Tech Stack
- Rails 7
- Ruby 3.2+
- PostgreSQL
- Tailwind CSS (dark theme)
- Hotwire/Turbo
- Devise (authentication)
- ActiveStorage (images)
- Faraday (HTTP client)

### Python Backend
- URL: http://localhost:8000
- Docs: http://localhost:8000/docs
- Must be running for Prompts 2.4+

### Styling Conventions
- Background: bg-slate-900, bg-slate-800 (cards)
- Text: text-slate-100, text-slate-300
- Accent: sky-500 (buttons, links)
- Cards: rounded-lg, p-6, border border-slate-700
- Buttons: px-4 py-2 rounded-lg font-medium

---

## Next Steps

1. **Start with Prompt 2.1** - Initialize Rails app
2. **Test after each prompt** - Don't skip testing
3. **Create PRs incrementally** - One per prompt
4. **Follow Dragon Wings methodology** - Reference your skills docs

**Ready to begin?** Start with Prompt 2.1 and test thoroughly before moving on!

🐉 **Let's build something amazing!**
