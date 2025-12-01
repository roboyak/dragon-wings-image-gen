class HomeController < ApplicationController
  def index
    # Redirect logged-in users to images page (Phase 4C: Remove stale "Coming Soon" content)
    if user_signed_in?
      redirect_to images_path
    end
    # Show landing page for guests
  end
end
