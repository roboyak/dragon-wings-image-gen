module ImagesHelper
  # Groups images by date with human-readable labels
  # Returns: { "Today" => [...], "Yesterday" => [...], "Nov 25, 2025" => [...] }
  def group_images_by_date(images)
    return {} if images.blank?

    today = Date.current
    yesterday = today - 1.day

    images.group_by do |image|
      image_date = image.created_at.to_date

      if image_date == today
        "Today"
      elsif image_date == yesterday
        "Yesterday"
      else
        image_date.strftime("%b %-d, %Y")
      end
    end
  end
end
