import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  handleEnter(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      this.element.closest('form').requestSubmit()
    }
  }
}
