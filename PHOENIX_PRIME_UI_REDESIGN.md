# Phoenix Prime: Image Generator UI Redesign Plan

> **Project:** Dragon Wings Image Generator UI Redesign
> **Style Reference:** SolarDash C2 Design System + Midjourney UX Patterns
> **Created:** 2025-11-28
> **Methodology:** Incremental Development (see `skills/incremental-development-skill.md`)

---

## Vision

Transform the Dragon Wings Image Generator from a functional tool into a **premium image generation experience** by combining:

1. **SolarDash C2 Design System** - Dark theme, typography, color palette, component patterns
2. **Midjourney UX Patterns** - Sidebar navigation, chronological gallery, generation progress indicators, prompt metadata display
3. **Dragon Wings Brand Identity** - Consistent across all Dragon Wings products

---

## Design References

### SolarDash C2 Style Guide
Location: `.dragon-wings/artifacts/screenshots/solardash-styleguide/STYLE_GUIDE.md`

Key patterns to adopt:
- Dark background: `#0d1117` (bg-primary), `#161b22` (bg-secondary)
- Accent cyan: `#22d3ee` for primary actions
- Status colors: green (success), amber (warning), red (error), purple (autonomous)
- 56px fixed header with horizontal nav
- Card-based layouts with 8px border-radius
- JetBrains Mono for code/metrics, Space Grotesk for headings

### Midjourney UI Patterns
Location: `UI_Samples/resized/UI_Midjourney_*.png`

Key patterns to adopt:
- **Left sidebar navigation** with icon + label
- **Centered prompt input** at top (search bar style)
- **Chronological gallery** with date headers (Today, Yesterday, etc.)
- **4-column grid** for image thumbnails
- **Progress indicator** showing generation % complete
- **Right sidebar** for prompt metadata (model, time, aspect ratio)
- **Section grouping**: Create, Edit, Organize | Aesthetics | Community
- **Active nav state** with accent highlight

---

## Current State Analysis

The existing UI (`frontend/app/views/images/index.html.erb`) has:
- SolarDash-inspired header navigation
- Grid-based gallery
- Settings panel on right
- Image-to-image upload panel
- Basic status indicators (queued, generating, complete, failed)

**Gaps to address:**
1. No sidebar navigation (uses top nav only)
2. Gallery lacks date grouping
3. Progress indicators are basic
4. No prompt/metadata detail view
5. Settings panel is hidden by default

---

## Phase Structure

```
Phase 1: Navigation & Layout Shell
Phase 2: Gallery & Grid System
Phase 3: Generation Interface
Phase 4: Polish & Interactions
```

Each phase follows the 4-prompt sequence:
1. Foundation (Infrastructure)
2. Shell (Structure)
3. Data (Functionality)
4. Interaction (Polish)

---

## Phase 1: Navigation & Layout Shell

### Prompt 1.1: Add Sidebar Navigation Component

**Context:**
- Rails 7 app with Tailwind CSS
- Current layout: `app/views/layouts/application.html.erb`
- Main view: `app/views/images/index.html.erb`
- Design system CSS: `app/assets/stylesheets/dragon_wings_design_system.css`

**Tasks:**
1. Create new partial: `app/views/shared/_sidebar.html.erb`
2. Sidebar structure (Midjourney-inspired):
   ```
   +------------------+
   | [Logo]           |
   | Dragon Wings     |
   +------------------+
   | GENERATE         |
   | * Create    [+]  | <- Active (cyan bg)
   | * Edit      [pen]|
   | * Organize [grid]|
   +------------------+
   | LIBRARY          |
   | * Gallery [img]  |
   | * History [clock]|
   | * Favorites [*]  |
   +------------------+
   | SETTINGS         |
   | * Models  [cube] |
   | * Account [user] |
   +------------------+
   | [User Avatar]    |
   | username         |
   +------------------+
   ```
3. Width: 220px fixed
4. Background: `hsl(var(--card))` with right border
5. Icons: Lucide-style SVG icons
6. Active state: cyan pill background
7. Section labels: uppercase, text-xs, muted color
8. Don't modify any existing routes or controllers

**Constraints:**
- Keep existing header for now (will remove in 1.2)
- Sidebar hidden on mobile (hamburger menu)
- Use same color tokens from dragon_wings_design_system.css

**Testing Checklist:**
- [ ] Sidebar renders on desktop
- [ ] Active nav item highlighted
- [ ] Hover states work
- [ ] Mobile: sidebar hidden, hamburger shows
- [ ] No console errors

**QA Screenshot:** Take Playwright screenshot after completion: `sidebar_navigation.png`

---

### Prompt 1.2: Update Layout to Sidebar + Main Content

**Context:**
- Sidebar partial created in 1.1
- Current layout has top header navigation
- Need to transition to sidebar-first layout

**Tasks:**
1. Update `application.html.erb` to use sidebar layout:
   ```
   +--------+----------------------------------+
   | SIDE   |  MAIN CONTENT AREA              |
   | BAR    |  (scrollable)                   |
   |        |                                  |
   | 220px  |  flex-1                         |
   +--------+----------------------------------+
   ```
2. Remove top navigation from header
3. Keep header for: prompt input bar (centered), user quota display
4. Header height: 56px (matches SolarDash)
5. Main content: full height minus header, scrollable
6. Add mobile hamburger menu that opens sidebar as overlay

**Constraints:**
- Don't modify image generation logic
- Keep all existing functionality working
- Settings panel remains on right side

**Testing Checklist:**
- [ ] Layout renders correctly
- [ ] Sidebar visible on desktop
- [ ] Main content scrolls independently
- [ ] Mobile hamburger opens sidebar overlay
- [ ] Prompt input centered in header
- [ ] User quota displays in header

**QA Screenshot:** Take Playwright screenshot: `sidebar_layout_desktop.png`, `sidebar_layout_mobile.png`

---

### Prompt 1.3: Add Prompt Input Bar Component

**Context:**
- Sidebar layout established
- Need Midjourney-style centered prompt bar
- Currently prompt is in a form inside main content

**Tasks:**
1. Create new partial: `app/views/shared/_prompt_bar.html.erb`
2. Design (Midjourney-inspired):
   ```
   +----------------------------------------------+
   | [Spark Icon]  What will you create?     [=] |
   +----------------------------------------------+
   ```
3. Features:
   - Full-width input (max-width: 800px, centered)
   - Left icon: spark/magic wand
   - Right: settings toggle button
   - Placeholder: "What will you create?"
   - Submit on Enter
   - Background: `hsl(var(--background))` with subtle border
   - Border radius: 24px (pill shape)
4. Move settings toggle from main content to prompt bar
5. Keep hidden inputs for model/settings (carry over from current form)

**Constraints:**
- Form must still POST to images_path
- Keep multipart support for img2img
- Mode toggle (Text/Image) moves to settings panel

**Testing Checklist:**
- [ ] Prompt bar renders centered
- [ ] Submit generates image
- [ ] Settings toggle shows/hides panel
- [ ] Keyboard Enter submits
- [ ] Hidden inputs preserve settings

**QA Screenshot:** Take Playwright screenshot: `prompt_bar_component.png`

---

### Prompt 1.4: Add Mobile Navigation Drawer

**Context:**
- Sidebar hidden on mobile
- Need smooth drawer/overlay experience

**Tasks:**
1. Create Stimulus controller: `sidebar_controller.js`
2. Mobile behavior:
   - Hamburger button in header (left side)
   - Tap opens sidebar as slide-in overlay
   - Dark backdrop behind sidebar
   - Tap backdrop or X closes
   - Smooth 200ms transition
3. Tablet (768px-1024px): Sidebar can collapse to icons only
4. Desktop (>1024px): Sidebar always visible

**Constraints:**
- Don't use external libraries (use Stimulus + CSS)
- Preserve all navigation functionality

**Testing Checklist:**
- [ ] Mobile: hamburger visible, sidebar hidden
- [ ] Mobile: tap hamburger opens drawer
- [ ] Mobile: tap backdrop closes drawer
- [ ] Tablet: sidebar collapses to icons
- [ ] Desktop: sidebar always visible
- [ ] Transitions are smooth

**QA Screenshot:** Take Playwright screenshots at 3 breakpoints: `mobile_drawer_open.png`, `tablet_collapsed.png`, `desktop_sidebar.png`

---

## Phase 2: Gallery & Grid System

### Prompt 2.1: Create Date-Grouped Gallery Component

**Context:**
- Current gallery is a flat grid
- Need Midjourney-style date grouping

**Tasks:**
1. Create helper method in `ImagesHelper`:
   ```ruby
   def group_images_by_date(images)
     # Returns: { "Today" => [...], "Yesterday" => [...], "Nov 25, 2025" => [...] }
   end
   ```
2. Update `images/index.html.erb` to render groups:
   ```erb
   <% group_images_by_date(@images).each do |date_label, images| %>
     <div class="date-group">
       <h3 class="date-header"><%= date_label %></h3>
       <div class="image-grid">
         <!-- image cards -->
       </div>
     </div>
   <% end %>
   ```
3. Date header styling:
   - text-sm, font-semibold
   - text-primary color
   - margin-bottom: 12px
   - sticky to top of scroll area

**Constraints:**
- Don't change Image model
- Keep existing image card structure
- Empty state still works

**Testing Checklist:**
- [ ] Images grouped by date
- [ ] "Today" label for today's images
- [ ] "Yesterday" label for yesterday
- [ ] Older dates show "Nov 25, 2025" format
- [ ] Date headers sticky on scroll
- [ ] Empty state shows when no images

**QA Screenshot:** Take Playwright screenshot: `date_grouped_gallery.png`

---

### Prompt 2.2: Improve Image Grid Cards

**Context:**
- Current cards show image + hover overlay
- Need enhanced Midjourney-style cards

**Tasks:**
1. Create new partial: `app/views/images/_card.html.erb`
2. Card structure:
   ```
   +------------------+
   |                  |
   |    [IMAGE]       |
   |                  |
   +------------------+
   | [Status badge]   | <- Only if not complete
   +------------------+
   ```
3. Hover state reveals:
   - Gradient overlay from bottom
   - Truncated prompt text (2 lines)
   - Action buttons: View, Download, Remix
4. Status badges (on image):
   - Queued: amber badge top-right
   - Generating: cyan badge with animated pulse
   - Failed: red badge with retry icon
5. Aspect ratio: maintain original (not forced square)
6. Gap between cards: 8px
7. Border-radius: 8px

**Constraints:**
- Keep existing click behavior (opens detail view)
- Don't change image URLs or storage

**Testing Checklist:**
- [ ] Cards render with correct aspect ratio
- [ ] Hover shows prompt + actions
- [ ] Status badges display correctly
- [ ] Generating badge pulses
- [ ] Failed badge shows retry
- [ ] Click opens detail view

**QA Screenshot:** Take Playwright screenshots: `image_card_default.png`, `image_card_hover.png`, `image_card_generating.png`

---

### Prompt 2.3: Add Generation Progress Indicator

**Context:**
- Current: basic spinner with "Generating" text
- Need: Midjourney-style progress with percentage

**Tasks:**
1. Update Image model to track progress:
   ```ruby
   # Add to Image model
   attr_accessor :progress_percent
   ```
2. Backend API: Return progress in status endpoint
3. Frontend: Update card to show:
   ```
   +------------------+
   | [Blurred preview]|
   |   [=========]    |
   |    43% Complete  |
   +------------------+
   ```
4. Progress bar: cyan fill, 4px height, rounded
5. Blur effect: Show low-res preview as it generates (if available)
6. Poll interval: 2 seconds (keep existing)

**Constraints:**
- Progress is estimated based on steps (if backend supports)
- Fallback to indeterminate if no progress available
- Don't block on backend changes if complex

**Testing Checklist:**
- [ ] Progress bar shows during generation
- [ ] Percentage updates on poll
- [ ] Completes at 100% then shows image
- [ ] Indeterminate works as fallback

**QA Screenshot:** Take Playwright screenshot: `generation_progress.png`

---

### Prompt 2.4: Responsive Grid System

**Context:**
- Need grid to adapt across screen sizes
- Midjourney uses ~4 columns on desktop

**Tasks:**
1. Update grid classes:
   - Mobile (< 640px): 2 columns
   - Tablet (640-1024px): 3 columns
   - Desktop (> 1024px): 4 columns
   - Large (> 1400px): 5 columns
2. Ensure masonry-style layout (varying heights)
3. Add CSS column-gap and row-gap: 8px
4. Lazy loading for images below fold

**Constraints:**
- Use CSS Grid or Tailwind classes (no JS masonry)
- Keep performance smooth with many images

**Testing Checklist:**
- [ ] 2 columns on mobile
- [ ] 3 columns on tablet
- [ ] 4 columns on desktop
- [ ] 5 columns on large screens
- [ ] Varying heights look natural
- [ ] Lazy loading works

**QA Screenshot:** Take Playwright screenshots at each breakpoint: `grid_mobile.png`, `grid_tablet.png`, `grid_desktop.png`, `grid_large.png`

---

## Phase 3: Generation Interface

### Prompt 3.1: Create Prompt Metadata Detail Panel

**Context:**
- Clicking image opens detail view
- Need right-side panel showing prompt metadata (Midjourney-style)

**Tasks:**
1. Update `images/show.html.erb` to include metadata panel:
   ```
   +------------------+------------------+
   |                  |  [Model Badge]   |
   |    [IMAGE]       |  SD v1.5         |
   |                  |                  |
   |                  |  Prompt:         |
   |                  |  "Dragon Wings..." |
   |                  |                  |
   |                  |  Negative:       |
   |                  |  "blurry, low..."  |
   |                  |                  |
   |                  |  Settings:       |
   |                  |  512x512 | 30 steps|
   |                  |  7.5 guidance    |
   |                  |                  |
   |                  |  Generated:      |
   |                  |  2 minutes ago   |
   |                  |                  |
   |                  |  [Download] [Copy]|
   |                  |  [Remix] [Delete]|
   +------------------+------------------+
   ```
2. Panel width: 320px
3. Actions:
   - Download: Direct image download
   - Copy Prompt: Copy to clipboard
   - Remix: Pre-fill prompt in generator
   - Delete: Confirm then delete

**Constraints:**
- Don't change Image model attributes
- Use existing image attributes for display

**Testing Checklist:**
- [ ] Metadata panel shows on image detail
- [ ] All settings displayed correctly
- [ ] Download works
- [ ] Copy prompt works
- [ ] Remix pre-fills generator
- [ ] Delete requires confirmation

**QA Screenshot:** Take Playwright screenshot: `image_detail_panel.png`

---

### Prompt 3.2: Enhanced Settings Panel

**Context:**
- Settings panel exists but is basic
- Need cleaner UI matching SolarDash forms

**Tasks:**
1. Update settings panel styling:
   - Group settings into sections
   - Section headers: uppercase, text-xs, muted
   - Input styling matches SolarDash forms
   - Add tooltips for each setting
2. Sections:
   - **Model**: Dropdown with model descriptions
   - **Quality**: Steps slider, Guidance slider
   - **Dimensions**: Width/Height with aspect ratio presets
   - **Advanced**: Seed input, Negative prompt
3. Add aspect ratio presets:
   - 1:1 (512x512)
   - 16:9 (768x432)
   - 9:16 (432x768)
   - 4:3 (640x480)

**Constraints:**
- Keep existing hidden input synchronization
- Don't change form submission behavior

**Testing Checklist:**
- [ ] Settings grouped into sections
- [ ] Tooltips display on hover
- [ ] Aspect ratio presets work
- [ ] All settings sync to hidden inputs
- [ ] Form submits correctly

**QA Screenshot:** Take Playwright screenshot: `enhanced_settings_panel.png`

---

### Prompt 3.3: Image-to-Image Enhanced UI

**Context:**
- Img2img panel exists but is basic
- Need drag-and-drop preview and strength visualization

**Tasks:**
1. Enhanced upload area:
   - Larger drop zone (full panel width)
   - Animated border on drag over
   - Image preview with zoom on click
2. Strength visualization:
   - Show example: "Low: subtle changes" vs "High: major changes"
   - Slider with visual markers
3. Add "Use gallery image" option:
   - Button to select from existing images
   - Modal with recent images grid

**Constraints:**
- Keep existing file upload functionality
- Don't change backend img2img logic

**Testing Checklist:**
- [ ] Drag and drop works
- [ ] Preview shows uploaded image
- [ ] Strength slider has visual indicators
- [ ] "Use gallery image" opens modal
- [ ] Selected gallery image sets as input

**QA Screenshot:** Take Playwright screenshots: `img2img_upload.png`, `img2img_gallery_select.png`

---

### Prompt 3.4: Generation Queue Indicator

**Context:**
- Multiple generations can be queued
- Need visual indicator of queue status

**Tasks:**
1. Add queue indicator in header:
   ```
   [Generating 1 of 3] [===-----]
   ```
2. Show in sidebar under "Create":
   ```
   Create [2] <- badge showing queue count
   ```
3. Queue list in sidebar (expandable):
   - Thumbnail
   - Truncated prompt
   - Status (Queued #1, Generating, etc.)
   - Cancel button

**Constraints:**
- Queue is per-user only
- Don't change backend queue logic

**Testing Checklist:**
- [ ] Queue count shows in header
- [ ] Badge appears on Create nav item
- [ ] Queue list shows pending generations
- [ ] Cancel removes from queue

**QA Screenshot:** Take Playwright screenshot: `generation_queue.png`

---

## Phase 4: Polish & Interactions

### Prompt 4.1: Loading States & Transitions

**Context:**
- Add professional loading states throughout

**Tasks:**
1. Page load skeleton:
   - Header: immediate
   - Sidebar: immediate
   - Gallery: skeleton cards while loading
2. Image card loading:
   - Shimmer effect placeholder
   - Fade in on image load
3. Panel transitions:
   - Settings panel: slide in from right (200ms)
   - Sidebar (mobile): slide in from left (200ms)
4. Button states:
   - Loading spinner on generate button
   - Disabled state during submission

**Constraints:**
- Use CSS transitions (no external animation libraries)
- Keep page performance fast

**Testing Checklist:**
- [ ] Skeleton shows on initial load
- [ ] Images fade in smoothly
- [ ] Panels slide in/out
- [ ] Generate button shows loading state
- [ ] No layout shift during transitions

**QA Screenshot:** Take Playwright screenshots: `loading_skeleton.png`, `panel_transition.png`

---

### Prompt 4.2: Keyboard Shortcuts

**Context:**
- Power users want keyboard shortcuts

**Tasks:**
1. Implement shortcuts:
   - `Cmd/Ctrl + Enter`: Generate
   - `Cmd/Ctrl + K`: Focus prompt input
   - `Esc`: Close panels/modals
   - `G`: Go to Gallery
   - `C`: Go to Create
   - `?`: Show shortcuts modal
2. Show shortcuts hint in prompt bar (subtle)
3. Shortcuts modal: list all shortcuts

**Constraints:**
- Don't conflict with browser shortcuts
- Shortcuts disabled when typing in inputs

**Testing Checklist:**
- [ ] All shortcuts work
- [ ] Shortcuts disabled in input fields
- [ ] ? opens shortcuts modal
- [ ] Hint shows in prompt bar

**QA Screenshot:** Take Playwright screenshot: `keyboard_shortcuts_modal.png`

---

### Prompt 4.3: Toast Notifications

**Context:**
- Need feedback for user actions

**Tasks:**
1. Create toast notification system:
   - Position: bottom-right
   - Types: success (green), error (red), info (cyan)
   - Auto-dismiss after 5 seconds
   - Manual dismiss with X
2. Trigger toasts for:
   - Generation started: "Creating your image..."
   - Generation complete: "Image ready!" with thumbnail
   - Generation failed: "Generation failed. Retry?"
   - Copied to clipboard: "Prompt copied!"
   - Image deleted: "Image deleted"
3. Stack multiple toasts (max 3 visible)

**Constraints:**
- Use Stimulus controller (no external libraries)
- Accessible (role="alert")

**Testing Checklist:**
- [ ] Toast shows on generation start
- [ ] Toast shows on completion
- [ ] Toast shows on error
- [ ] Auto-dismiss works
- [ ] Manual dismiss works
- [ ] Multiple toasts stack

**QA Screenshot:** Take Playwright screenshots: `toast_success.png`, `toast_error.png`, `toast_stacked.png`

---

### Prompt 4.4: Final Polish & Accessibility

**Context:**
- Final polish pass for professional quality

**Tasks:**
1. Accessibility:
   - All interactive elements focusable
   - Focus indicators visible
   - Screen reader labels on icons
   - Color contrast meets WCAG AA
2. Polish:
   - Consistent spacing throughout
   - Remove any debug code
   - Check all hover/active states
   - Verify responsive at all breakpoints
3. Performance:
   - Lazy load images
   - Optimize SVG icons (inline vs sprite)
   - Check Lighthouse score

**Constraints:**
- Don't add new features
- Focus on polish only

**Testing Checklist:**
- [ ] Tab navigation works throughout
- [ ] Focus indicators visible
- [ ] Screen reader announces correctly
- [ ] Color contrast passes
- [ ] No console errors
- [ ] Lighthouse performance > 90

**QA Screenshot:** Take Playwright screenshots: `final_desktop.png`, `final_mobile.png`

---

## QA Protocol: Screenshot Verification

### After Each Prompt Completion

Phoenix QA should capture screenshots using Playwright MCP:

```javascript
// Example Playwright commands for QA verification
await page.goto('http://localhost:3000/images');
await page.screenshot({ path: 'screenshots/[prompt_id]_desktop.png' });
await page.setViewportSize({ width: 390, height: 844 });
await page.screenshot({ path: 'screenshots/[prompt_id]_mobile.png' });
```

### Screenshot Naming Convention
```
screenshots/
├── phase1/
│   ├── prompt1.1_sidebar_navigation.png
│   ├── prompt1.2_sidebar_layout_desktop.png
│   ├── prompt1.2_sidebar_layout_mobile.png
│   └── ...
├── phase2/
│   └── ...
└── ...
```

### Visual Regression Baseline
After Phase 4 completion, establish baseline screenshots for regression testing.

---

## Progress Tracker

| Phase | Prompt | Status | PR # | QA |
|-------|--------|--------|------|-----|
| 1 | 1.1 Sidebar Navigation | [ ] Pending | - | - |
| 1 | 1.2 Layout Update | [ ] Pending | - | - |
| 1 | 1.3 Prompt Bar | [ ] Pending | - | - |
| 1 | 1.4 Mobile Drawer | [ ] Pending | - | - |
| 2 | 2.1 Date Grouping | [ ] Pending | - | - |
| 2 | 2.2 Image Cards | [ ] Pending | - | - |
| 2 | 2.3 Progress Indicator | [ ] Pending | - | - |
| 2 | 2.4 Responsive Grid | [ ] Pending | - | - |
| 3 | 3.1 Metadata Panel | [ ] Pending | - | - |
| 3 | 3.2 Settings Panel | [ ] Pending | - | - |
| 3 | 3.3 Img2Img UI | [ ] Pending | - | - |
| 3 | 3.4 Queue Indicator | [ ] Pending | - | - |
| 4 | 4.1 Loading States | [ ] Pending | - | - |
| 4 | 4.2 Keyboard Shortcuts | [ ] Pending | - | - |
| 4 | 4.3 Toast Notifications | [ ] Pending | - | - |
| 4 | 4.4 Final Polish | [ ] Pending | - | - |

---

## Next Steps

1. **Phoenix UI**: Execute prompts sequentially (one PR per prompt)
2. **Phoenix QA**: Take screenshots after each prompt for verification
3. **Phoenix Prime**: Review progress, update plan as needed

---

## Appendix: Component Reference

### Color Tokens (from dragon_wings_design_system.css)
```css
--background: 222.2 84% 4.9%;
--foreground: 210 40% 98%;
--card: 222.2 84% 4.9%;
--primary: 187 100% 50%;      /* Cyan accent */
--destructive: 0 62.8% 30.6%; /* Red for errors */
--muted: 217.2 32.6% 17.5%;
--muted-foreground: 215 20.2% 65.1%;
--border: 217.2 32.6% 17.5%;
```

### Icon Set (Lucide)
Use consistent Lucide-style icons:
- Plus (create)
- Image (gallery)
- Clock (history)
- Star (favorites)
- Cube (models)
- User (account)
- Settings (gear)
- Download
- Copy
- Trash
- Refresh (retry)
- Sparkles (generate)

### Typography
```css
font-family-heading: 'Space Grotesk', sans-serif;
font-family-body: 'Inter', sans-serif;
font-family-mono: 'JetBrains Mono', monospace;
```
