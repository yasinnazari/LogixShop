document.addEventListener('DOMContentLoaded', () => {
   const mainImage = document.querySelector('#product-main-image');
   const thumbnails = document.querySelectorAll('[data-product-image]');
   const quantityValue = document.querySelector('[data-quantity-value]');
   const decreaseQuantity = document.querySelector('[data-quantity-decrease]');
   const increaseQuantity = document.querySelector('[data-quantity-increase]');

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
         quantity += 1;
         quantityValue.textContent = quantity;
      });
   }

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
