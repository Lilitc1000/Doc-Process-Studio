import DOMPurify from 'dompurify';
import type { Directive } from 'vue';

const safeHtml: Directive<HTMLElement> = {
  mounted(el, binding) {
    el.innerHTML = DOMPurify.sanitize(binding.value ?? '');
  },
  updated(el, binding) {
    if (binding.value !== binding.oldValue) {
      el.innerHTML = DOMPurify.sanitize(binding.value ?? '');
    }
  },
};

export default safeHtml;
