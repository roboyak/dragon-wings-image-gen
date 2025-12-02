import { Controller } from "@hotwired/stimulus"

// Phase 6: Mask Editor Controller for Inpainting
// Uses Fabric.js for canvas-based mask drawing
export default class extends Controller {
  static targets = [
    "canvas", "canvasContainer", "loading", "maskIndicator",
    "brushBtn", "eraserBtn", "brushSize", "brushSizeValue",
    "maskOpacity", "maskOpacityValue",
    "prompt", "negativePrompt", "modelKey", "strength", "strengthValue",
    "steps", "stepsValue", "generateBtn", "generateBtnText", "statusMessage",
    "undoBtn", "redoBtn"
  ]

  static values = {
    imageUrl: String,
    imageId: Number,
    generateUrl: String,
    csrf: String
  }

  connect() {
    this.currentTool = 'brush'
    this.brushColor = 'rgba(255, 255, 255, 0.7)' // White with opacity
    this.brushWidth = 30
    this.undoStack = []
    this.redoStack = []
    this.isDrawing = false
    this.maskHasContent = false

    // Load Fabric.js and initialize canvas
    this.initializeFabric()

    // Keyboard shortcuts
    document.addEventListener('keydown', this.handleKeydown.bind(this))
  }

  disconnect() {
    document.removeEventListener('keydown', this.handleKeydown.bind(this))
    if (this.canvas) {
      this.canvas.dispose()
    }
  }

  async initializeFabric() {
    // Fabric.js loads as a global (window.fabric) from CDN
    // Wait for it to be available
    let attempts = 0
    const maxAttempts = 50

    while (typeof window.fabric === 'undefined' && attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 100))
      attempts++
    }

    if (typeof window.fabric === 'undefined') {
      console.error('Fabric.js not loaded after waiting')
      this.showError('Failed to load canvas library')
      return
    }

    this.fabric = window.fabric

    // Load the background image
    // Note: We don't set crossOrigin because we don't need to export the background
    // The mask is drawn separately and exported independently
    const img = new Image()
    img.onload = () => {
      this.setupCanvas(img)
    }
    img.onerror = (e) => {
      console.error('Failed to load image:', this.imageUrlValue, e)
      // Try with crossOrigin as fallback
      const img2 = new Image()
      img2.crossOrigin = 'anonymous'
      img2.onload = () => this.setupCanvas(img2)
      img2.onerror = () => this.showError('Failed to load image')
      img2.src = this.imageUrlValue
    }
    img.src = this.imageUrlValue
  }

  setupCanvas(img) {
    // Calculate display size (fit within viewport)
    const maxWidth = this.canvasContainerTarget.clientWidth - 40
    const maxHeight = window.innerHeight - 200
    const scale = Math.min(maxWidth / img.width, maxHeight / img.height, 1)

    const displayWidth = Math.round(img.width * scale)
    const displayHeight = Math.round(img.height * scale)

    // Store original dimensions for mask export
    this.originalWidth = img.width
    this.originalHeight = img.height

    // Initialize Fabric canvas
    this.canvas = new this.fabric.Canvas(this.canvasTarget, {
      width: displayWidth,
      height: displayHeight,
      isDrawingMode: true,
      backgroundColor: 'transparent'
    })

    // Set background image
    const fabricImg = new this.fabric.Image(img, {
      scaleX: scale,
      scaleY: scale,
      selectable: false,
      evented: false
    })
    this.canvas.setBackgroundImage(fabricImg, this.canvas.renderAll.bind(this.canvas))

    // Configure brush
    this.canvas.freeDrawingBrush = new this.fabric.PencilBrush(this.canvas)
    this.canvas.freeDrawingBrush.color = this.brushColor
    this.canvas.freeDrawingBrush.width = this.brushWidth

    // Event handlers
    this.canvas.on('path:created', (e) => {
      this.saveState()
      this.maskHasContent = true
      this.updateMaskIndicator()
    })

    this.canvas.on('mouse:down', () => {
      this.isDrawing = true
    })

    this.canvas.on('mouse:up', () => {
      this.isDrawing = false
    })

    // Hide loading, show canvas
    this.loadingTarget.classList.add('hidden')
    this.canvasTarget.style.display = 'block'

    // Save initial state
    this.saveState()
  }

  // Tool switching
  setTool(event) {
    const tool = event.currentTarget.dataset.tool
    this.currentTool = tool

    // Update button states
    this.brushBtnTarget.classList.remove('tool-active')
    this.eraserBtnTarget.classList.remove('tool-active')
    this.brushBtnTarget.style.backgroundColor = 'hsl(var(--secondary))'
    this.brushBtnTarget.style.color = 'hsl(var(--secondary-foreground))'
    this.eraserBtnTarget.style.backgroundColor = 'hsl(var(--secondary))'
    this.eraserBtnTarget.style.color = 'hsl(var(--secondary-foreground))'

    if (tool === 'brush') {
      this.brushBtnTarget.classList.add('tool-active')
      this.brushBtnTarget.style.backgroundColor = 'hsl(var(--primary))'
      this.brushBtnTarget.style.color = 'hsl(var(--primary-foreground))'
      this.canvas.freeDrawingBrush.color = this.brushColor
    } else {
      this.eraserBtnTarget.classList.add('tool-active')
      this.eraserBtnTarget.style.backgroundColor = 'hsl(var(--primary))'
      this.eraserBtnTarget.style.color = 'hsl(var(--primary-foreground))'
      // Eraser is just transparent drawing that removes
      this.canvas.freeDrawingBrush.color = 'rgba(0,0,0,1)'
    }
  }

  updateBrushSize() {
    this.brushWidth = parseInt(this.brushSizeTarget.value)
    this.brushSizeValueTarget.textContent = `${this.brushWidth}px`
    if (this.canvas) {
      this.canvas.freeDrawingBrush.width = this.brushWidth
    }
  }

  updateMaskOpacity() {
    const opacity = parseInt(this.maskOpacityTarget.value) / 100
    this.maskOpacityValueTarget.textContent = `${Math.round(opacity * 100)}%`
    this.brushColor = `rgba(255, 255, 255, ${opacity})`
    if (this.canvas && this.currentTool === 'brush') {
      this.canvas.freeDrawingBrush.color = this.brushColor
    }
  }

  updateStrength() {
    const strength = parseFloat(this.strengthTarget.value)
    this.strengthValueTarget.textContent = strength.toFixed(2)
  }

  updateSteps() {
    const steps = parseInt(this.stepsTarget.value)
    this.stepsValueTarget.textContent = steps
  }

  // Undo/Redo
  saveState() {
    if (!this.canvas) return

    const json = this.canvas.toJSON()
    this.undoStack.push(JSON.stringify(json))
    this.redoStack = [] // Clear redo on new action

    // Limit stack size
    if (this.undoStack.length > 50) {
      this.undoStack.shift()
    }

    this.updateUndoRedoButtons()
  }

  undo() {
    if (this.undoStack.length <= 1) return

    const current = this.undoStack.pop()
    this.redoStack.push(current)

    const previous = this.undoStack[this.undoStack.length - 1]
    this.canvas.loadFromJSON(previous, () => {
      this.canvas.renderAll()
      this.updateUndoRedoButtons()
      this.checkMaskContent()
    })
  }

  redo() {
    if (this.redoStack.length === 0) return

    const next = this.redoStack.pop()
    this.undoStack.push(next)

    this.canvas.loadFromJSON(next, () => {
      this.canvas.renderAll()
      this.updateUndoRedoButtons()
      this.checkMaskContent()
    })
  }

  updateUndoRedoButtons() {
    this.undoBtnTarget.disabled = this.undoStack.length <= 1
    this.redoBtnTarget.disabled = this.redoStack.length === 0
  }

  clearMask() {
    if (!this.canvas) return
    if (!confirm('Clear the entire mask?')) return

    // Remove all objects except background
    const objects = this.canvas.getObjects()
    objects.forEach(obj => this.canvas.remove(obj))
    this.canvas.renderAll()

    this.saveState()
    this.maskHasContent = false
    this.updateMaskIndicator()
  }

  checkMaskContent() {
    this.maskHasContent = this.canvas.getObjects().length > 0
    this.updateMaskIndicator()
  }

  updateMaskIndicator() {
    if (this.maskHasContent) {
      this.maskIndicatorTarget.classList.remove('hidden')
    } else {
      this.maskIndicatorTarget.classList.add('hidden')
    }
  }

  handleKeydown(event) {
    // Ctrl+Z for undo
    if (event.ctrlKey && event.key === 'z') {
      event.preventDefault()
      this.undo()
    }
    // Ctrl+Y for redo
    if (event.ctrlKey && event.key === 'y') {
      event.preventDefault()
      this.redo()
    }
    // [ and ] for brush size
    if (event.key === '[') {
      this.brushSizeTarget.value = Math.max(5, this.brushWidth - 5)
      this.updateBrushSize()
    }
    if (event.key === ']') {
      this.brushSizeTarget.value = Math.min(100, this.brushWidth + 5)
      this.updateBrushSize()
    }
  }

  // Export mask as black/white image
  getMaskDataUrl() {
    if (!this.canvas) return null

    // Create a temporary canvas at original resolution
    const tempCanvas = document.createElement('canvas')
    tempCanvas.width = this.originalWidth
    tempCanvas.height = this.originalHeight
    const ctx = tempCanvas.getContext('2d')

    // Fill with black (preserve areas)
    ctx.fillStyle = 'black'
    ctx.fillRect(0, 0, this.originalWidth, this.originalHeight)

    // Scale factor from display to original
    const scaleX = this.originalWidth / this.canvas.width
    const scaleY = this.originalHeight / this.canvas.height

    // Draw all paths in white (inpaint areas)
    ctx.fillStyle = 'white'
    ctx.strokeStyle = 'white'

    this.canvas.getObjects().forEach(obj => {
      if (obj.type === 'path') {
        ctx.save()
        ctx.lineWidth = obj.strokeWidth * scaleX
        ctx.lineCap = 'round'
        ctx.lineJoin = 'round'

        // Get path data and scale it
        const path = obj.path
        ctx.beginPath()
        path.forEach((cmd, i) => {
          if (cmd[0] === 'M') {
            ctx.moveTo((obj.left + cmd[1]) * scaleX, (obj.top + cmd[2]) * scaleY)
          } else if (cmd[0] === 'Q') {
            ctx.quadraticCurveTo(
              (obj.left + cmd[1]) * scaleX,
              (obj.top + cmd[2]) * scaleY,
              (obj.left + cmd[3]) * scaleX,
              (obj.top + cmd[4]) * scaleY
            )
          } else if (cmd[0] === 'L') {
            ctx.lineTo((obj.left + cmd[1]) * scaleX, (obj.top + cmd[2]) * scaleY)
          }
        })
        ctx.stroke()
        ctx.restore()
      }
    })

    return tempCanvas.toDataURL('image/png')
  }

  // Generate inpainted image
  async generate() {
    if (!this.maskHasContent) {
      alert('Please draw a mask on the image first.')
      return
    }

    const prompt = this.promptTarget.value.trim()
    if (!prompt) {
      alert('Please enter a prompt.')
      this.promptTarget.focus()
      return
    }

    // Get mask data
    const maskData = this.getMaskDataUrl()
    if (!maskData) {
      alert('Failed to export mask.')
      return
    }

    // Disable button and show loading
    this.generateBtnTarget.disabled = true
    this.generateBtnTextTarget.textContent = 'Generating...'
    this.statusMessageTarget.classList.remove('hidden')
    this.statusMessageTarget.textContent = 'Starting generation...'

    try {
      const response = await fetch(this.generateUrlValue, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': this.csrfValue
        },
        body: JSON.stringify({
          mask_data: maskData,
          prompt: prompt,
          negative_prompt: this.negativePromptTarget.value.trim(),
          model_key: this.modelKeyTarget.value,
          strength: parseFloat(this.strengthTarget.value),
          num_inference_steps: parseInt(this.stepsTarget.value),
          guidance_scale: 7.5,
          blur_mask: true,
          blur_factor: 33
        })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Generation failed')
      }

      const data = await response.json()
      this.statusMessageTarget.textContent = 'Generation started! Redirecting...'

      // Redirect to the new image's status page
      setTimeout(() => {
        window.location.href = `/images/${data.id}`
      }, 1000)

    } catch (error) {
      console.error('Generation error:', error)
      this.statusMessageTarget.textContent = `Error: ${error.message}`
      this.statusMessageTarget.style.color = 'hsl(var(--destructive))'
      this.generateBtnTarget.disabled = false
      this.generateBtnTextTarget.textContent = 'Generate Inpaint'
    }
  }

  showError(message) {
    this.loadingTarget.innerHTML = `
      <div class="text-center">
        <svg class="w-10 h-10 mx-auto mb-2 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
        <p class="text-red-400">${message}</p>
      </div>
    `
  }
}
