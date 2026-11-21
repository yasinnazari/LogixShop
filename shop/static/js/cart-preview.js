document.addEventListener('DOMContentLoaded', () => {
   const wrapper = document.querySelector('.cart-preview-wrapper');
   const trigger = wrapper?.querySelector('.cart-trigger');

   if (!wrapper || !trigger) return;

   trigger.addEventListener('click', (event) => {
      event.stopPropagation();
      const isOpen = wrapper.classList.toggle('is-open');
      trigger.setAttribute('aria-expanded', String(isOpen));
   });

   document.addEventListener('click', (event) => {
      if (!wrapper.contains(event.target)) {
         wrapper.classList.remove('is-open');
         trigger.setAttribute('aria-expanded', 'false');
      }
   });

   document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
         wrapper.classList.remove('is-open');
         trigger.setAttribute('aria-expanded', 'false');
         trigger.focus();
      }
   });
});
