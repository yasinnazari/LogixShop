# LogixShop MVP Domain Design

Status: reconnaissance-based design proposal. Verified repository facts are labelled **Fact**; recommendations and unknowns are kept separate.

## 1. Current relevant implementation

**Facts**

- The project is a server-rendered Django application using Django Templates.
- `Category` and `Product` are the active catalog models. Products belong to one category and contain title, description, price, optional discount fields, stock fields, rating, and image.
- `Customer` is a separate custom table with name, phone, email, and a plain `password` field. It is not connected to Django's built-in `User` model.
- `Invoice` currently links exactly one product to one customer, with quantity, address, date, and a status choice. It is not used by the current views.
- Current views only render home, about, product-list, and a presentation-only login page. There is no cart, checkout, authentication processing, order creation, or payment code.
- The product template displays cart controls, but they have no verified backend or JavaScript behavior. The cart badge is hard-coded to `0`.

## 2. Proposed MVP domain structure

### Category and Product — reuse existing models

Keep the existing catalog concepts as the source for product browsing.

- `Category`: category name and image; one category has many products.
- `Product`: catalog description, current selling price, image, and available stock.
- At checkout, do not rely on the product's current price or title for historical reporting; copy the relevant values to the order item.

Design considerations, not confirmed requirements:

- Treat `stock >= 0` as the authoritative inventory quantity. `has_stock` is redundant and should not independently determine availability.
- Treat the effective selling price as one defined value. The current `is_sale`/`price`/`discounted_price` combination needs an explicit rule before implementation.
- Existing field names `category_title` and the old foreign-key naming are retained for compatibility in this proposal; clearer names can be considered during a controlled migration.

### Cart and CartItem

Add a `Cart` aggregate with one of these ownership modes:

- authenticated owner: nullable one-to-one/foreign-key relation to the chosen authenticated user;
- anonymous owner: session key, unique while the cart is anonymous.

`CartItem` belongs to one cart and one product, with a positive integer quantity. Enforce one row per `(cart, product)` pair with a database uniqueness constraint.

Recommended rules:

- Adding the same product increases quantity rather than creating a duplicate row.
- Cart quantity must be positive and must not exceed currently available stock.
- A cart may contain multiple products.
- Anonymous cart contents live in the database and are associated with the session; after login, merge them into the user's cart using a defined conflict rule (recommended: sum quantities, then cap at stock).
- Empty or abandoned carts may remain; cleanup policy is not required for the first MVP.

### Order and OrderItem

Use an `Order` header plus multiple `OrderItem` rows. This supersedes the single-product shape of `Invoice` for new checkout flows.

`Order` should contain:

- owner reference to the authenticated user/profile, according to the authentication decision;
- order status;
- payment status or a clearly defined relation to payment records;
- immutable shipping/contact address captured at checkout;
- subtotal, discount, shipping, and total amounts as stored monetary snapshots;
- creation and update timestamps.

`OrderItem` should contain:

- order and product reference, allowing the product reference to become nullable if products may later be deleted;
- product title snapshot;
- unit price snapshot after the applicable discount;
- quantity;
- line total snapshot or a deterministic calculation from quantity and unit price.

The existing `Invoice` should be treated as **legacy/transition data**, not automatically renamed or deleted. Its current one-product structure cannot represent a multi-product order. Whether it is migrated into `Order`/`OrderItem` is unresolved and depends on whether its records are considered real historical data.

### TestPayment

Add a payment record associated with one order. It should record:

- order;
- provider, with a test provider value for the MVP;
- amount attempted;
- payment status: `PENDING`, `SUCCEEDED`, or `FAILED`;
- provider/reference identifier when available;
- failure reason or safe diagnostic code;
- created and completed timestamps.

The test flow should simulate success and failure without claiming real payment authorization. A retry creates a new payment attempt or a new attempt record while preserving prior attempts.

## 3. Statuses and business rules

Recommended order statuses:

- `DRAFT` or `PENDING_PAYMENT`
- `PAID`
- `PROCESSING`
- `SHIPPED` (optional if shipping is inside MVP)
- `COMPLETED`
- `CANCELED`

Recommended payment transitions:

- `PENDING -> SUCCEEDED`
- `PENDING -> FAILED`
- `FAILED -> PENDING` for an explicit retry, or create a new attempt
- A successful payment must not be changed back to failed by a later browser request.

Recommended order rules:

1. Checkout validates every cart item, quantity, product availability, and current effective price.
2. Checkout uses a transaction and row-level locking or an equivalent safe stock check so two checkouts cannot oversell the same stock.
3. The order stores item prices and product display snapshots before the cart can change.
4. Stock is decremented exactly once according to the chosen payment policy. For the simple test flow, reserve/decrement during successful order finalization and make retries idempotent.
5. A failed payment leaves the order retryable and must not create a second stock decrement.
6. A successful payment creates one finalized paid order; duplicate callbacks or refreshes must not create another order or payment effect.
7. Order history remains readable even if a product, category, or customer profile changes. Do not cascade-delete historical orders as a normal catalog-management action.

The exact point at which stock is reserved versus decremented is an unresolved business decision if real asynchronous payments are later introduced.

## 4. Authentication and cart ownership

### Recommendation

Prefer Django's built-in authentication for the MVP. The installed settings already include Django auth, sessions, authentication middleware, and password validators, but the current login view does not use them.

The existing `Customer` table should not be used for password authentication in its current form because its password field is a plain, length-limited text field and email is not unique. A sensible compatibility path is:

- use Django's user identity for login and authorization;
- add a profile/contact record only if the existing customer fields are needed;
- decide explicitly whether existing `Customer` rows are migrated, linked, or retained as legacy records.

For cart persistence, use a database cart keyed to the authenticated user and a session-key cart for anonymous visitors. Merge the session cart after login. This fits the existing template frontend and avoids making browser state the only source of cart data.

## 5. Security and integrity risks

**Confirmed risks**

- The current custom password field is unsuitable for storing usable credentials securely.
- The current login form has no verified POST handling, CSRF token, authentication, or error path.
- Current product and cart controls are presentation-only; no server-side authorization or stock validation exists.
- Existing `CASCADE` relations could remove business records when catalog/customer records are deleted.
- `Invoice.__str__()` currently concatenates a string and integer and is unsafe to rely on in admin or logs.

**Design risks to resolve during implementation**

- Do not trust prices, product IDs, quantities, totals, or payment results submitted by the browser.
- Recalculate totals server-side and use decimal monetary fields consistently.
- Protect order detail and retry endpoints by ownership and authentication checks.
- Make checkout and payment finalization idempotent.
- Avoid exposing provider secrets or detailed payment diagnostics to templates/users.

## 6. Acceptance criteria

### Normal scenarios

- A visitor can add multiple different products to a persistent session cart.
- Adding an existing product updates its quantity without duplicate cart rows.
- A logged-in user sees the same cart after a new browser request and after logout/login according to the defined merge rule.
- Checkout creates one order with one order item per distinct product.
- Order item quantity, title, and unit price remain unchanged after the catalog product is edited.
- A successful test payment marks the order paid exactly once and decrements stock exactly once.
- A failed test payment leaves the order retryable and preserves the failed attempt.
- A later retry can succeed without duplicating the order or decrementing stock twice.

### Failure scenarios

- Checkout rejects zero, negative, non-integer, or over-stock quantities.
- Checkout rejects an unavailable product or a cart whose price/availability changed, with a clear recovery path.
- Concurrent checkout cannot reduce stock below zero.
- A user cannot view or retry another user's order/payment.
- Refreshing or repeating a payment callback does not duplicate payment effects.
- Deleting or deactivating a catalog product does not erase finalized order history.

## 7. Unresolved questions and assumptions

### Unresolved decisions

- Whether existing `Customer` rows represent real users that must be migrated.
- Whether guest checkout is required or only session carts before login.
- Whether shipping is in MVP or only address capture.
- Whether stock is reserved at order creation, payment initiation, or successful test payment.
- Whether the existing `Invoice` data must be preserved as orders.
- Exact discount, tax, shipping-fee, currency, and rounding rules.
- Required order lifecycle after payment: processing, shipping, cancellation, refund, and completion.

### Assumptions used for this proposal

- MVP supports authenticated checkout and anonymous cart browsing.
- One checkout produces one multi-item order.
- The test payment is synchronous enough for the initial flow; real gateway webhooks are later work.
- Product ratings and catalog presentation are outside checkout-domain scope.

## 8. Prerequisites for implementation

1. Confirm the authentication choice and the migration/linking policy for `Customer`.
2. Confirm guest checkout, shipping scope, currency, discount rules, and stock timing.
3. Decide whether existing `Invoice` rows are legacy-only or must be converted.
4. Define the order/payment status transition matrix and idempotency expectations.
5. Review the current database before writing migrations, especially any production or shared data not represented by the local SQLite file.
6. Add focused model, checkout, ownership, stock-concurrency, and payment-retry tests before enabling the new flow.
