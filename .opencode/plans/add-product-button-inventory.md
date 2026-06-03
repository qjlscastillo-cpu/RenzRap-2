# Add Product Button (Inventory Module)

## File to modify
`templates/inventory.html`

## Changes

### 1. CSS — Add `.btn-add` style (after line 246, after `.btn-save:hover`)
```css
    .btn-add {
      height: 36px; padding: 0 16px; border-radius: 8px; border: none;
      background: #3b82f6; color: #fff;
      font-family: 'DM Sans', sans-serif; font-weight: 600; font-size: 13px;
      cursor: pointer; transition: background 0.2s; white-space: nowrap;
    }
    .btn-add:hover { background: #2563eb; }
```

### 2. Toolbar — Add button (after line 375, inside `.toolbar` div)
```html
          <button class="btn-add" onclick="addProduct()">＋ Add Product</button>
```

### 3. `openModal()` — Remove guard that blocks add mode (line 644)
- Remove `if (!id) return; // no add mode` (line 644)
- Update `editingId = id;` so when `id` is falsy it sets to `undefined`

### 4. New `addProduct()` function (before `openModal` or after `closeModal`)
```js
  function addProduct() {
    editingId = null;
    document.getElementById("modalTitle").textContent = "Add Product";
    document.getElementById("modalSubtitle").style.display = "none";
    // Clear all fields
    ["fName","fSku","fBarcode","fPrice","fQty","fThreshold"].forEach(id =>
      document.getElementById(id).value = "");
    document.getElementById("fCategory").value = "";
    document.getElementById("fSupplier").value = "";
    document.getElementById("fInactive").checked = false;
    document.getElementById("inactiveField").style.display = "none";
    // Unlock all fields (admin mode)
    const lockedFields = ["fName","fSku","fBarcode","fCategory","fSupplier","fPrice","fThreshold"];
    const lockIcons    = ["lockName","lockSku","lockBarcode","lockCategory","lockSupplier","lockPrice","lockThreshold"];
    lockedFields.forEach((fieldId, i) => {
      const el = document.getElementById(fieldId);
      el.classList.remove("locked"); el.removeAttribute("readonly");
      if (el.tagName === "SELECT") el.removeAttribute("disabled");
      const lockEl = document.getElementById(lockIcons[i]);
      if (lockEl) lockEl.style.display = "none";
    });
    const btnScan = document.getElementById("btnScanBarcode");
    if (btnScan) { btnScan.disabled = false; btnScan.style.opacity = "1"; btnScan.style.cursor = "pointer"; }
    document.getElementById("modalOverlay").classList.add("open");
  }
```

### 5. `saveProduct()` — Handle create vs edit (lines 705–741)
- Remove `if (!editingId) return;` (line 706)
- Change from always-PUT to conditional:
  - If `editingId` → PUT (existing logic)
  - If `!editingId` → POST to `/api/inventory` with all fields from form (admin-only, no employee restrictions)
- After successful POST, call `loadProducts()` instead of inline update (since we don't know the new id)
- Keep `closeModal(); updateStats(); renderTable();` (or let `loadProducts()` handle it)

Suggested `saveProduct()`:
```js
  async function saveProduct() {
    const isCreating = !editingId;
    const isEmployeeEdit = !IS_ADMIN && !isCreating;
    let name, sku, barcode, category, price, threshold, supplier_id;

    if (isEmployeeEdit) {
      const p = products.find(x => Number(x.id) === Number(editingId));
      name = p.name; sku = p.sku; barcode = p.barcode || "";
      category = p.category; price = p.price; threshold = p.threshold;
      supplier_id = p.supplier_id || null;
    } else {
      name      = document.getElementById("fName").value.trim();
      sku       = document.getElementById("fSku").value.trim();
      barcode   = document.getElementById("fBarcode").value.trim();
      category  = document.getElementById("fCategory").value;
      price     = parseFloat(document.getElementById("fPrice").value) || 0;
      threshold = parseInt(document.getElementById("fThreshold").value) || 5;
      if (!name || !sku || !category) {
        showToast("Please fill in Name, SKU, and Category.");
        return;
      }
    }

    const qty      = parseInt(document.getElementById("fQty").value) || 0;
    const inactive = document.getElementById("fInactive").checked;
    supplier_id   = document.getElementById("fSupplier").value || null;
    if (supplier_id) supplier_id = parseInt(supplier_id);
    const payload = { name, sku, barcode, category, supplier_id, price, qty, threshold, inactive };

    let res;
    if (isCreating) {
      res = await fetch("/api/inventory", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify(payload)
      });
    } else {
      res = await fetch(`/api/inventory/${editingId}`, {
        method: "PUT", headers: {"Content-Type":"application/json"},
        body: JSON.stringify(payload)
      });
    }

    closeModal();
    if (res.ok) {
      await loadProducts(); // refreshes products, stats, table
    }
  }
```
