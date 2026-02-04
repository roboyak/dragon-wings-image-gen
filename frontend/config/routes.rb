Rails.application.routes.draw do
  devise_for :users

  # Image generation
  resources :images, only: [:index, :create, :show] do
    member do
      get :status
      post :toggle_favorite
      get :edit_mask
      post :generate_inpaint
      get :download
      get :serve  # Proxy image through Rails for ngrok/external access
    end
    collection do
      post :enhance_prompt
    end
  end

  # Settings pages
  resources :models, only: [:index]

  # Define your application routes per the DSL in https://guides.rubyonrails.org/routing.html

  # Reveal health status on /up that returns 200 if the app boots with no exceptions, otherwise 500.
  # Can be used by load balancers and uptime monitors to verify that the app is live.
  get "up" => "rails/health#show", as: :rails_health_check

  # Defines the root path route ("/")
  root "home#index"
end
