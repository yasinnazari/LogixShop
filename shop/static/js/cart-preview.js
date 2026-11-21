document.addEventListener('DOMContentLoaded', () => {
   const wrapper = document.querySelector('.cart-preview-wrapper');
   const trigger = wrapper?.querySelector('.cart-trigger');
   const badge = wrapper?.querySelector('.cart-count');
   const countLabel = wrapper?.querySelector('.cart-preview-count');
   const emptyState = wrapper?.querySelector('.cart-empty-state');
   const list = wrapper?.querySelector('[data-cart-list]');

   if (!wrapper || !trigger || !badge || !countLabel || !emptyState || !list) return;

   const updateBadge = (totalQuantity) => {
      badge.textContent = totalQuantity > 9 ? '+9' : String(totalQuantity);
      countLabel.textContent = `${totalQuantity} item${totalQuantity === 1 ? '' : 's'}`;
   };

   const renderCart = (cart) => {
      const items = cart.items || [];
      updateBadge(cart.total_quantity || 0);
      emptyState.hidden = items.length > 0;
      list.hidden = items.length === 0;
      list.setAttribute('aria-hidden', String(items.length === 0));

      if (!items.length) {
         list.replaceChildren();
         return;
      }

      const fragment = document.createDocumentFragment();
      items.forEach((item) => {
         const article = document.createElement('article');
         article.className = 'cart-preview-item';

         const image = document.createElement('div');
         image.className = 'cart-preview-item-image';
         if (item.image_url) {
            const imageElement = document.createElement('img');
            imageElement.src = item.image_url;
            imageElement.alt = item.name;
            image.appendChild(imageElement);
         } else {
            image.innerHTML = '<i class="bi bi-image"></i>';
         }

         const details = document.createElement('div');
         details.className = 'cart-preview-item-details';
         const name = document.createElement('h3');
         name.textContent = item.name;
         const quantity = document.createElement('span');
         quantity.className = 'cart-preview-item-quantity';
         quantity.textContent = `${item.quantity}x`;
         const price = document.createElement('span');
         price.className = 'cart-preview-item-price';
         price.textContent = item.price;
         details.append(name, price, quantity);

         const remove = document.createElement('button');
         remove.className = 'cart-preview-item-remove';
         remove.type = 'button';
         remove.dataset.removeUrl = item.remove_url;
         remove.setAttribute('aria-label', `Remove ${item.name} from cart`);
         remove.innerHTML = '<i class="bi bi-trash3"></i>';
         article.append(image, details, remove);
         fragment.appendChild(article);
      });

      const action = document.createElement('a');
      action.className = 'cart-preview-action';
      action.href = '#';
      action.textContent = 'View cart ';
      const arrow = document.createElement('i');
      arrow.className = 'bi bi-arrow-right';
      action.appendChild(arrow);
      fragment.appendChild(action);

      list.replaceChildren(fragment);
   };

   const loadCart = async () => {
      try {
         const response = await fetch(trigger.dataset.cartSummaryUrl, {
            headers: { Accept: 'application/json' },
         });
         if (response.ok) renderCart(await response.json());
      } catch (error) {
         // Keep the safe empty state when the summary is unavailable.
      }
   };

   const addToCart = async (button) => {
      const quantityElement = document.querySelector('[data-quantity-value]');
      const quantity = quantityElement ? Number(quantityElement.textContent) || 1 : 1;
      const wasDisabled = button.disabled;
      button.disabled = true;

      try {
         const response = await fetch(button.dataset.cartUrl, {
            method: 'POST',
            headers: {
               Accept: 'application/json',
               'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
               'X-CSRFToken': button.dataset.csrfToken,
            },
            body: new URLSearchParams({ quantity }),
         });

         if (response.status === 401) {
            window.location.href = `/login/?next=${encodeURIComponent(window.location.href)}`;
            return;
         }

         const data = await response.json();
         if (!response.ok) return;

         renderCart(data);
         wrapper.classList.add('is-open');
         trigger.setAttribute('aria-expanded', 'true');
      } catch (error) {
         // Keep the existing UI stable when the request cannot be completed.
      } finally {
         button.disabled = wasDisabled;
      }
   };

   trigger.addEventListener('click', (event) => {
      event.stopPropagation();
      const isOpen = wrapper.classList.toggle('is-open');
      trigger.setAttribute('aria-expanded', String(isOpen));
   });

   document.querySelectorAll('[data-add-to-cart]').forEach((button) => {
      button.addEventListener('click', () => addToCart(button));
   });

   list.addEventListener('click', async (event) => {
      const remove = event.target.closest('[data-remove-url]');
      if (!remove) return;

      remove.disabled = true;
      try {
         const response = await fetch(remove.dataset.removeUrl, {
            method: 'POST',
            headers: {
               Accept: 'application/json',
               'X-CSRFToken': trigger.dataset.csrfToken,
            },
         });
         if (response.ok) renderCart(await response.json());
      } finally {
         remove.disabled = false;
      }
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

   loadCart();
});
