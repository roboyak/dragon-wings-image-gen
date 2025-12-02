# Pin npm packages by running ./bin/importmap

pin "application"
pin "@hotwired/turbo-rails", to: "turbo.min.js"
pin "@hotwired/stimulus", to: "stimulus.min.js"
pin "@hotwired/stimulus-loading", to: "stimulus-loading.js"
pin_all_from "app/javascript/controllers", under: "controllers"

# Fabric.js for canvas mask editing (Phase 6 - Inpainting)
pin "fabric", to: "https://cdn.jsdelivr.net/npm/fabric@5.3.0/dist/fabric.min.js"
