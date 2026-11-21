document.addEventListener('DOMContentLoaded', () => {
   const mainImage = document.querySelector('#product-main-image');
   const thumbnails = document.querySelectorAll('[data-product-image]');
   const quantityValue = document.querySelector('[data-quantity-value]');
   const decreaseQuantity = document.querySelector('[data-quantity-decrease]');
   const increaseQuantity = document.querySelector('[data-quantity-increase]');
   const quantityControl = quantityValue?.closest('[data-stock]');
   const stockLimit = quantityControl ? Number(quantityControl.dataset.stock) : null;

   thumbnails.forEach((thumbnail) => {
      thumbnail.addEventListener('click', () => {
         if (!mainImage) return;
         mainImage.src = thumbnail.dataset.productImage;
         thumbnails.forEach((item) => item.classList.remove('is-active'));
         thumbnail.classList.add('is-active');
      });
   });

   if (quantityValue && decreaseQuantity && increaseQuantity) {
      let quantity = 1;
      decreaseQuantity.addEventListener('click', () => {
         quantity = Math.max(1, quantity - 1);
         quantityValue.textContent = quantity;
      });
      increaseQuantity.addEventListener('click', () => {
         if (Number.isFinite(stockLimit) && quantity >= stockLimit) {
            window.showNotification?.({
               message: 'Out of stock',
               type: 'error',
               icon: 'bi-exclamation-circle-fill',
            });
            return;
         }
         quantity += 1;
         quantityValue.textContent = quantity;
      });
   }

   const bindSingleSelection = (selector) => {
      const options = document.querySelectorAll(selector);
      options.forEach((option) => {
         option.setAttribute('aria-pressed', String(option.classList.contains('is-selected')));
         option.addEventListener('click', () => {
            options.forEach((item) => {
               const isSelected = item === option;
               item.classList.toggle('is-selected', isSelected);
               item.setAttribute('aria-pressed', String(isSelected));
            });
         });
      });
   };

   bindSingleSelection('.product-color-option');
   bindSingleSelection('.product-size-option');

   const tabs = document.querySelectorAll('[data-product-tab]');
   const panels = document.querySelectorAll('[data-product-panel]');
   tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
         const target = tab.dataset.productTab;
         tabs.forEach((item) => item.classList.toggle('is-active', item === tab));
         panels.forEach((panel) => panel.classList.toggle('is-hidden', panel.dataset.productPanel !== target));
      });
   });
});
