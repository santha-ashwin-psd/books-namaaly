<template>
<div class="sc-page">

  <!-- ── Sticky block ─────────────────────────────────────────────── -->
  <div class="sc-sticky">
    <div class="sc-header">
      <span class="sc-title">Company Settings</span>
      <button class="nim-btn nim-btn-primary sc-save-btn" @click="save" :disabled="saving || !$canEdit('admin')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
        {{ saving ? 'Saving…' : 'Save Changes' }}
      </button>
    </div>
    <div class="sc-tabs">
      <button v-for="t in TABS" :key="t.k"
        class="sc-tab" :class="{ 'sc-tab--active': activeTab === t.k }"
        @click="activeTab = t.k">
        {{ t.l }}
      </button>
    </div>
  </div>

  <!-- ── Company Profile ──────────────────────────────────────────── -->
  <div v-if="activeTab === 'profile'" class="sc-body sc-body--two-col">

    <!-- LEFT: Company Information -->
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
          </div>
          <div>
            <div class="sc-card-title">Company Information</div>
            <div class="sc-card-subtitle">Update your company details and contact information.</div>
          </div>
        </div>
        <div class="sc-divider"></div>

        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Company Name <span class="sc-required">*</span></label>
            <input class="nim-input" v-model="form.default_company" placeholder="Acme Technologies Pvt Ltd"/>
          </div>
        </div>

        <div class="sc-fg" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Phone</label>
            <div class="sc-input-icon-wrap">
              <svg class="sc-input-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.61 3.41 2 2 0 0 1 3.6 1.22h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.8a16 16 0 0 0 6.29 6.29l.95-.95a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
              <input class="nim-input sc-icon-input" v-model="form.company_phone" placeholder="+91 00000 00000"/>
            </div>
          </div>
          <div class="nim-field">
            <label class="nim-label">Email</label>
            <div class="sc-input-icon-wrap">
              <svg class="sc-input-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
              <input class="nim-input sc-icon-input" v-model="form.company_email" placeholder="info@acmetech.com"/>
            </div>
          </div>
        </div>

        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Website</label>
            <div class="sc-input-icon-wrap">
              <svg class="sc-input-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
              <input class="nim-input sc-icon-input" v-model="form.company_website" placeholder="https://www.acmetech.com"/>
            </div>
          </div>
        </div>

        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Address</label>
            <div class="sc-input-icon-wrap">
              <svg class="sc-input-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
              <input class="nim-input sc-icon-input" v-model="form.company_address" placeholder="123 Business Park, Sector 62, Noida"/>
            </div>
          </div>
        </div>

        <div class="sc-fg sc-fg--three" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">City</label>
            <div class="sc-input-icon-wrap">
              <svg class="sc-input-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg>
              <input class="nim-input sc-icon-input" v-model="form.company_city" placeholder="Noida"/>
            </div>
          </div>
          <div class="nim-field">
            <label class="nim-label">State / Province</label>
            <div class="sc-input-icon-wrap">
              <svg class="sc-input-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>
              <select v-if="stateOptions.length" class="nim-input sc-icon-input" v-model="form.company_state">
                <option value="">— Select State —</option>
                <option v-for="s in stateOptions" :key="s" :value="s">{{ s }}</option>
              </select>
              <input v-else class="nim-input sc-icon-input" v-model="form.company_state" placeholder="Enter state"/>
            </div>
          </div>
          <div class="nim-field">
            <label class="nim-label">Country</label>
            <div class="sc-input-icon-wrap">
              <svg class="sc-input-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
              <select class="nim-input sc-icon-input" v-model="form.company_country" @change="form.company_state = ''">
                <option value="">— Select Country —</option>
                <option v-for="c in COUNTRIES" :key="c" :value="c">{{ c }}</option>
              </select>
            </div>
          </div>
        </div>

        <div class="sc-fg sc-fg--single" style="margin-bottom:0">
          <div class="nim-field">
            <label class="nim-label">Pincode / ZIP</label>
            <div class="sc-input-icon-wrap">
              <svg class="sc-input-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              <input class="nim-input sc-icon-input" v-model="form.company_pincode" placeholder="201309"/>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- RIGHT: Logo + Preview -->
    <div class="sc-col-side">

      <!-- Company Logo Card -->
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
          </div>
          <div>
            <div class="sc-card-title">Company Logo</div>
            <div class="sc-card-subtitle">Upload your company logo</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-logo-area">
          <!-- Logo preview box -->
          <div class="sc-logo-box">
            <img v-if="form.logo_url" :src="form.logo_url" style="width:100%;height:100%;object-fit:contain"/>
            <div v-else class="sc-logo-placeholder">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#c5d0fa" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
            </div>
          </div>
          <!-- Actions -->
          <div class="sc-logo-actions">
            <label class="sc-upload-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>
              Upload Logo
              <input type="file" accept="image/*" style="display:none" @change="handleLogoUpload"/>
            </label>
            <div class="sc-hint">PNG, JPG up to 2 MB.<br/>Appears on PDF invoices.</div>
            <button v-if="form.logo_url" class="sc-remove-btn" @click="form.logo_url = ''">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>
              Remove
            </button>
          </div>
        </div>
      </div>

      <!-- Preview Card -->
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon sc-card-icon--blue">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          </div>
          <div>
            <div class="sc-card-title">Preview</div>
            <div class="sc-card-subtitle">This is how your logo will appear on invoices.</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <!-- Mini invoice preview -->
        <div class="sc-preview">
          <div class="sc-preview-header">
            <div class="sc-preview-logo-wrap">
              <img v-if="form.logo_url" :src="form.logo_url" class="sc-preview-logo-img"/>
              <div v-else class="sc-preview-logo-placeholder">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#c5d0fa" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
              </div>
            </div>
            <div class="sc-preview-company">
              <div class="sc-preview-company-name">{{ form.default_company || 'Company Name' }}</div>
              <div class="sc-preview-company-addr">{{ form.company_address || '123 Business Park, Sector 62' }}</div>
              <div class="sc-preview-company-addr">{{ [form.company_city, form.company_state, form.company_pincode].filter(Boolean).join(', ') || 'City, State 000000' }}</div>
              <div class="sc-preview-company-addr">{{ form.company_country || 'Oman' }}</div>
            </div>
          </div>
          <div class="sc-preview-divider"></div>
          <div class="sc-preview-label">INVOICE</div>
          <div class="sc-preview-row"><span class="sc-preview-key">Invoice #</span><span class="sc-preview-val">INV-2024-001</span></div>
          <div class="sc-preview-row"><span class="sc-preview-key">Date</span><span class="sc-preview-val">May 20, 2024</span></div>
          <div class="sc-preview-row"><span class="sc-preview-key">Due Date</span><span class="sc-preview-val">June 03, 2024</span></div>
        </div>
      </div>

    </div>
  </div>

  <!-- ── Tax ─────────────────────────────────────────────────────── -->
  <div v-else-if="activeTab === 'tax'" class="sc-body sc-body--two-col">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
          </div>
          <div>
            <div class="sc-card-title">Tax Configuration</div>
            <div class="sc-card-subtitle">GST and tax settings for India</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg sc-fg--single">
          <div class="nim-field">
            <label class="nim-label">GSTIN</label>
            <input class="nim-input" v-model="form.gstin" placeholder="22AAAAA0000A1Z5"
              @input="form.gstin = form.gstin.toUpperCase()"
              :style="form.gstin && !GSTIN_REGEX.test(form.gstin) ? 'border-color:#dc2626;background:#fff5f5' :
                      form.gstin && GSTIN_REGEX.test(form.gstin) ? 'border-color:#2f9e44' : ''"/>
            <div v-if="form.gstin && !GSTIN_REGEX.test(form.gstin)" style="margin-top:4px;font-size:12px;color:#dc2626;display:flex;align-items:center;gap:4px">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
              Invalid GSTIN format (e.g. 22AAAAA0000A1Z5)
            </div>
            <div v-else-if="form.gstin && GSTIN_REGEX.test(form.gstin)" style="margin-top:4px;font-size:12px;color:#2f9e44;display:flex;align-items:center;gap:4px">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
              Valid GSTIN
            </div>
          </div>
          <div class="nim-field">
            <label class="nim-label">GST State</label>
            <input class="nim-input sc-input--readonly" :value="form.gst_state" readonly tabindex="-1"
              placeholder="Auto-filled from GSTIN"/>
            <div class="sc-field-hint">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="8.01"/></svg>
              Derived automatically from the GSTIN's first 2 digits (state code).
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="sc-col-side">
      <div class="sc-info-card">
        <div class="sc-info-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16.01"/></svg>
        </div>
        <div class="sc-info-title">About GSTIN</div>
        <div class="sc-info-body">
          <p>GSTIN is a 15-digit unique identification number assigned to every GST registered business in India.</p>
          <p>Format: <code>22AAAAA0000A1Z5</code></p>
          <ul>
            <li>First 2 digits — State code</li>
            <li>Next 10 — PAN number</li>
            <li>13th digit — Entity number</li>
            <li>14th — Z (default)</li>
            <li>15th — Check digit</li>
          </ul>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Branding ─────────────────────────────────────────────────── -->
  <div v-else-if="activeTab === 'branding'" class="sc-body sc-body--two-col">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
          </div>
          <div>
            <div class="sc-card-title">Invoice Template</div>
            <div class="sc-card-subtitle">Choose a layout for your PDF invoices</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-branding-templates">
          <button v-for="t in TEMPLATES" :key="t.key"
            class="sc-tmpl-btn" :class="{ 'sc-tmpl-btn--active': form.pdf_template === t.key }"
            @click="form.pdf_template = t.key">
            <div class="sc-tmpl-icon">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
            </div>
            <div class="sc-tmpl-label">{{ t.label }}</div>
            <div v-if="form.pdf_template === t.key" class="sc-tmpl-check">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
            </div>
          </button>
        </div>
      </div>

      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="13.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="10.5" r="2.5"/><circle cx="8.5" cy="7.5" r="2.5"/><circle cx="6.5" cy="12.5" r="2.5"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2z"/></svg>
          </div>
          <div>
            <div class="sc-card-title">Brand Color</div>
            <div class="sc-card-subtitle">Accent color used on PDF invoices</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-color-row">
          <label class="sc-color-pick" style="cursor:pointer">
            <span class="sc-color-swatch" :style="{ background: form.brand_color }"></span>
            <span class="sc-color-hex">{{ form.brand_color }}</span>
            <input type="color" v-model="form.brand_color" class="sc-color-input"/>
          </label>
          <div class="sc-hint">Used as the accent color on your PDF invoices.</div>
        </div>
      </div>
    </div>

    <div class="sc-col-side">
      <!-- Logo upload -->
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
          </div>
          <div>
            <div class="sc-card-title">Company Logo</div>
            <div class="sc-card-subtitle">Default logo on PDF invoices</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-logo-area sc-logo-area--stacked">
          <div class="sc-logo-box sc-logo-box--wide">
            <img v-if="form.company_logo" :src="resolveSrc(form.company_logo)" style="width:100%;height:100%;object-fit:contain"/>
            <div v-else class="sc-logo-placeholder">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#c5d0fa" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
            </div>
          </div>
          <div class="sc-logo-actions sc-logo-actions--row">
            <label class="sc-upload-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>
              Upload Logo
              <input type="file" accept="image/*" style="display:none" @change="handleBrandingLogoUpload"/>
            </label>
            <button v-if="form.company_logo" class="sc-remove-btn" @click="form.company_logo = ''">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>
              Remove
            </button>
          </div>
          <div class="sc-hint" style="margin-top:4px">PNG, JPG or SVG (max. 2MB).</div>
        </div>
      </div>
      <!-- Tips -->
      <div class="sc-info-card">
        <div class="sc-info-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16.01"/></svg>
        </div>
        <div class="sc-info-title">Branding Tips</div>
        <div class="sc-info-body">
          <ul>
            <li>Use a PNG logo with a transparent background for best results.</li>
            <li>Your brand color appears on invoice headers and accent elements.</li>
            <li>The Classic template works best for most Indian businesses.</li>
          </ul>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Reminders ─────────────────────────────────────────────────── -->
  <div v-else-if="activeTab === 'reminders'" class="sc-body sc-body--two-col">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
          </div>
          <div>
            <div class="sc-card-title">Payment Reminders</div>
            <div class="sc-card-subtitle">Automate overdue payment notifications</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg sc-fg--single">
          <div class="sc-toggle-row" @click="form.auto_send_invoice = form.auto_send_invoice ? 0 : 1">
            <div class="sc-toggle" :class="{ 'sc-toggle--on': form.auto_send_invoice }">
              <div class="sc-toggle-knob"></div>
            </div>
            <div>
              <div class="sc-toggle-label">Auto-Send Invoice on Submit</div>
              <div class="sc-hint">Email invoice to customer automatically when submitted</div>
            </div>
          </div>
          <div class="sc-toggle-row" @click="form.send_payment_reminders = form.send_payment_reminders ? 0 : 1">
            <div class="sc-toggle" :class="{ 'sc-toggle--on': form.send_payment_reminders }">
              <div class="sc-toggle-knob"></div>
            </div>
            <div>
              <div class="sc-toggle-label">Send Overdue Payment Reminders</div>
              <div class="sc-hint">Automatically email overdue invoice reminders</div>
            </div>
          </div>
          <template v-if="form.send_payment_reminders">
            <div class="nim-field"><label class="nim-label">Remind N days before due</label><input class="nim-input" type="number" v-model="form.reminder_days_before" min="0"/></div>
            <div class="nim-field"><label class="nim-label">Remind N days after due</label><input class="nim-input" type="number" v-model="form.reminder_days_after" min="1"/></div>
          </template>
        </div>
      </div>
    </div>
    <div class="sc-col-side">
      <div class="sc-info-card">
        <div class="sc-info-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16.01"/></svg>
        </div>
        <div class="sc-info-title">How Reminders Work</div>
        <div class="sc-info-body">
          <ul>
            <li>Invoices are emailed to customers automatically on submit when auto-send is on.</li>
            <li>Overdue reminders are sent based on the days before/after the due date you configure.</li>
            <li>Emails use the company email address set in Company Profile.</li>
          </ul>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Period Lock ──────────────────────────────────────────────────── -->
  <div v-else-if="activeTab === 'period_lock'" class="sc-body sc-body--two-col">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon sc-card-icon--red">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
          </div>
          <div>
            <div class="sc-card-title">Books Lock Date</div>
            <div class="sc-card-subtitle">Freeze all financial transactions on or before this date</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg sc-fg--single">
          <div class="nim-field">
            <label class="nim-label">Books Lock Date</label>
            <input class="nim-input" type="date" v-model="form.lock_date" />
            <div class="sc-hint" style="margin-top:6px">
              Freeze all financial transactions on or before this date.
              Only a System Manager can post past it.
            </div>
          </div>
          <div v-if="form.lock_date" class="sc-lock-status">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            Locked up to {{ new Date(form.lock_date).toLocaleDateString("en-IN", { day:"2-digit", month:"short", year:"numeric" }) }}
          </div>
          <div v-else class="sc-lock-status sc-lock-status--none">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            No lock date set — all periods are open
          </div>
          <div v-if="form.lock_date" class="sc-clear-lock-row">
            <button class="sc-remove-btn" @click="form.lock_date = ''">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>
              Clear Lock Date
            </button>
          </div>
        </div>
      </div>
    </div>
    <div class="sc-col-side">
      <div class="sc-info-card sc-info-card--warn">
        <div class="sc-info-icon sc-info-icon--red">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </div>
        <div class="sc-info-title sc-info-title--red">How Period Lock Works</div>
        <div class="sc-info-body">
          <ul>
            <li>All transactions dated <strong>on or before</strong> the lock date are frozen.</li>
            <li>Applies to Invoices, Bills, Payments, Journal Entries, Credit Notes, and more.</li>
            <li>Only a <strong>System Manager</strong> role can post past the lock date.</li>
            <li>Clear the date to remove the lock entirely.</li>
            <li>This is separate from fiscal year period locks, which apply per period in the Fiscal Years page.</li>
          </ul>
        </div>
      </div>
    </div>
  </div>

</div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from "vue";
import { useRoute } from "vue-router";
import { apiGET, apiPOST, setBooksCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { COUNTRIES, statesFor, stateFromGstin } from "../composables/useCountryState.js";
import { GSTIN_REGEX } from "../composables/useValidation.js";

const { toast } = useToast();
const route = useRoute();

const form = reactive({
  default_company: "", default_currency: "OMR", fiscal_year_start_month: "April",
  invoice_prefix: "INV", gstin: "", gst_state: "", logo_url: "",
  company_address: "", company_city: "", company_country: "Oman",
  company_state: "", company_pincode: "",
  company_phone: "", company_email: "", company_website: "",
  auto_send_invoice: 0, send_payment_reminders: 0,
  reminder_days_before: 3, reminder_days_after: 7, auto_reconcile: 0,
  pdf_template: "classic", brand_color: "#1a6ef7", company_logo: "",
  lock_date: "",
});
const saving = ref(false);
const loadedCompanyName = ref("");

const TABS = [
  { k: "profile",   l: "Company Profile" },
  { k: "tax",       l: "Tax" },
  { k: "branding",  l: "Branding & Template" },
  { k: "reminders", l: "Reminders" },
  { k: "period_lock", l: "Period Lock" },
];

const validTabKeys = TABS.map(t => t.k);
const activeTab = ref(validTabKeys.includes(route.query.tab) ? route.query.tab : "profile");

const TEMPLATES = [
  { key: "classic", label: "Classic" },
  { key: "modern",  label: "Modern"  },
  { key: "minimal", label: "Minimal" },
];

function resolveSrc(path) {
  if (!path) return "";
  if (path.startsWith("data:") || path.startsWith("http")) return path;
  return (window.location.origin || "") + path;
}

function handleBrandingLogoUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file); fd.append("doctype", "Books Company");
  fd.append("docname", form.default_company || ""); fd.append("fieldname", "company_logo");
  fd.append("csrf_token", window.frappe?.csrf_token || "");
  fetch("/api/method/upload_file", { method: "POST", credentials: "same-origin", body: fd })
    .then((r) => r.json())
    .then((d) => { if (d.message?.file_url) { form.company_logo = d.message.file_url; toast("Logo uploaded"); } })
    .catch(() => toast("Upload failed", "error"));
}

const stateOptions = computed(() => statesFor(form.company_country));

// GST State is always derived from the GSTIN's first 2 digits (state code).
watch(() => form.gstin, (g) => { form.gst_state = stateFromGstin(g); });

async function load() {
  try {
    const d = await apiGET("zoho_books_clone.api.admin.get_company_settings");
    Object.assign(form, d);
    loadedCompanyName.value = d.default_company || "";
  } catch (e) { toast("Could not load settings", "error"); }
}

async function save() {
  const newName = (form.default_company || "").trim();
  if (!newName) { toast("Company name is required", "error"); return; }

  saving.value = true;
  try {
    // Renaming is a distinct, higher-stakes operation: it changes the document's
    // own identity (Books Company autonames on this field) and has to cascade to
    // every place the old name was copied as plain text. Handle it first, via its
    // own endpoint, before saving the rest of the form.
    if (loadedCompanyName.value && newName !== loadedCompanyName.value) {
      await apiPOST("zoho_books_clone.api.admin.rename_company", {
        old_name: loadedCompanyName.value,
        new_name: newName,
      });
      loadedCompanyName.value = newName;
      // Company resolution is cached in window.__booksCompany and sysdefaults.
      // Update that cache immediately so anything that reads it before the
      // reload finishes (or if the reload is ever removed) sees the new name
      // right away instead of a stale one.
      setBooksCompany(newName);
      toast("Company renamed — reloading…");
      await apiPOST("zoho_books_clone.api.admin.save_company_settings", { ...form, default_company: newName });
      window.location.reload();
      return;
    }

    await apiPOST("zoho_books_clone.api.admin.save_company_settings", { ...form });
    toast("Settings saved");
  } catch (e) { toast(e.message, "error"); }
  saving.value = false;
}

function handleLogoUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file); fd.append("doctype", "Books Company");
  fd.append("docname", form.default_company || ""); fd.append("fieldname", "logo_url");
  fd.append("csrf_token", window.frappe?.csrf_token || "");
  fetch("/api/method/upload_file", { method: "POST", credentials: "same-origin", body: fd })
    .then((r) => r.json())
    .then((d) => { if (d.message?.file_url) { form.logo_url = d.message.file_url; toast("Logo uploaded"); } })
    .catch(() => toast("Upload failed", "error"));
}

onMounted(load);
</script>

<style scoped>
/* ── Page ──────────────────────────────────────────────────────────── */
.sc-page {
  background: #f0f2f5;
  padding-bottom: 32px;
}

/* ── Sticky ────────────────────────────────────────────────────────── */
.sc-sticky {
  position: sticky;
  top: 0;
  z-index: 20;
  background: #f0f2f5;
}
.sc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 24px 0;
}
.sc-title {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  letter-spacing: -0.3px;
}
.sc-save-btn {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13.5px;
  font-weight: 600;
  padding: 9px 20px;
  border-radius: 9px;
  background: linear-gradient(135deg, #2f74f5 0%, #1a6ef7 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(26,110,247,.28), inset 0 1px 0 rgba(255,255,255,.18);
  transition: box-shadow .18s ease, transform .18s ease, filter .18s ease;
}
.sc-save-btn:hover:not(:disabled) {
  filter: brightness(1.04);
  box-shadow: 0 6px 18px rgba(26,110,247,.36), inset 0 1px 0 rgba(255,255,255,.2);
  transform: translateY(-1px);
}
.sc-save-btn:active:not(:disabled) { transform: translateY(0); box-shadow: 0 2px 8px rgba(26,110,247,.3); }

/* ── Tabs ──────────────────────────────────────────────────────────── */
.sc-tabs {
  display: flex;
  border-bottom: 2px solid #e4e8f0;
  padding: 0 24px;
  margin-top: 14px;
  overflow-x: auto;
  scrollbar-width: none;
}
.sc-tabs::-webkit-scrollbar { display: none; }
.sc-tab {
  padding: 10px 18px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: #868e96;
  white-space: nowrap;
  border-bottom: 2px solid transparent;
  border-radius: 8px 8px 0 0;
  margin-bottom: -2px;
  transition: color .15s, background .15s;
}
.sc-tab:hover { color: #374151; background: rgba(37,99,235,.05); }
.sc-tab--active { color: #2563eb; border-bottom-color: #2563eb; background: linear-gradient(180deg, rgba(37,99,235,.06), rgba(37,99,235,0)); }

/* ── Body layouts ──────────────────────────────────────────────────── */
.sc-body {
  padding: 24px;
  display: grid;
  gap: 20px;
  align-content: start;
}
.sc-body--narrow {
  max-width: 560px;
}
.sc-body--two-col {
  grid-template-columns: 1fr 300px;
  align-items: start;
  max-width: none;
}
.sc-col-main { display: grid; gap: 20px; align-content: start; }
.sc-col-side  { display: grid; gap: 16px; align-content: start; }

/* ── Cards ─────────────────────────────────────────────────────────── */
.sc-card {
  background: #fff;
  border: 1px solid #e8ecf2;
  border-radius: 14px;
  padding: 22px 24px;
  box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.03);
  transition: box-shadow .2s ease, transform .2s ease, border-color .2s ease;
}
.sc-card:hover {
  box-shadow: 0 6px 20px rgba(16,24,40,.07), 0 2px 6px rgba(16,24,40,.04);
  border-color: #dbe3ee;
  transform: translateY(-1px);
}

.sc-card-header {
  display: flex;
  align-items: center;
  gap: 14px;
}
.sc-card-icon {
  width: 40px;
  height: 40px;
  border-radius: 11px;
  background: linear-gradient(135deg, #eaf1ff 0%, #dbe7ff 100%);
  color: #2563eb;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: inset 0 0 0 1px rgba(37,99,235,.08), 0 2px 6px rgba(37,99,235,.12);
}
.sc-card-icon--blue { background: linear-gradient(135deg, #eaf1ff 0%, #dbe7ff 100%); color: #2563eb; }

.sc-card-title {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}
.sc-card-subtitle {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 2px;
}
.sc-divider {
  height: 1px;
  background: #f3f4f6;
  margin: 18px 0;
}
.sc-required { color: #dc2626; }

/* ── Input with icon ───────────────────────────────────────────────── */
.sc-input-icon-wrap { position: relative; display: flex; align-items: center; }
.sc-input-icon {
  position: absolute;
  left: 10px;
  color: #9ca3af;
  pointer-events: none;
  z-index: 1;
}
.sc-icon-input { padding-left: 30px !important; }

/* ── Form grid ─────────────────────────────────────────────────────── */
.sc-fg {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.sc-fg--single { grid-template-columns: 1fr; }
.sc-fg--three  { grid-template-columns: 1fr 1fr 1fr; }
.sc-full { grid-column: 1 / -1; }

/* Read-only, auto-derived field (e.g. GST State from GSTIN) */
.sc-input--readonly {
  background: #f8fafc;
  color: #475569;
  cursor: default;
}
.sc-input--readonly:focus { border-color: #e4e8f0; box-shadow: none; }
.sc-field-hint {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 5px;
  font-size: 12px;
  color: #6b7280;
}
.sc-field-hint svg { flex-shrink: 0; color: #94a3b8; }

/* ── Logo area ─────────────────────────────────────────────────────── */
.sc-logo-area {
  display: flex;
  gap: 18px;
  align-items: flex-start;
}
.sc-logo-box {
  width: 130px;
  height: 100px;
  flex-shrink: 0;
  border: 2px dashed #c5d0fa;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #f8f9fc;
}
.sc-logo-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
}
.sc-logo-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 4px;
}
.sc-upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1.5px solid #2563eb;
  border-radius: 8px;
  background: #fff;
  color: #2563eb;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  transition: background .15s;
  white-space: nowrap;
}
.sc-upload-btn:hover { background: #eff6ff; }
.sc-hint {
  font-size: 11.5px;
  color: #9ca3af;
  line-height: 1.5;
}
.sc-remove-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border: 1.5px solid #fecaca;
  border-radius: 8px;
  background: #fff5f5;
  color: #dc2626;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background .15s;
  width: fit-content;
}
.sc-remove-btn:hover { background: #fef2f2; }

/* ── Preview card ──────────────────────────────────────────────────── */
.sc-preview {
  background: #fff;
  border: 1px solid #e8ecf2;
  border-radius: 10px;
  padding: 14px 16px;
  font-size: 12px;
}
.sc-preview-header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
}
.sc-preview-logo-wrap {
  width: 50px;
  height: 40px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.sc-preview-logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.sc-preview-logo-placeholder {
  width: 50px;
  height: 40px;
  background: #f3f4f6;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.sc-preview-company { flex: 1; min-width: 0; }
.sc-preview-company-name {
  font-size: 12px;
  font-weight: 700;
  color: #111827;
  margin-bottom: 2px;
}
.sc-preview-company-addr {
  font-size: 10.5px;
  color: #6b7280;
  line-height: 1.5;
}
.sc-preview-divider {
  height: 1px;
  background: #e5e7eb;
  margin: 10px 0 8px;
}
.sc-preview-label {
  font-size: 11px;
  font-weight: 800;
  color: #111827;
  letter-spacing: .5px;
  margin-bottom: 8px;
}
.sc-preview-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}
.sc-preview-key {
  font-size: 11px;
  font-weight: 600;
  color: #374151;
}
.sc-preview-val {
  font-size: 11px;
  color: #374151;
}

/* ── Toggle ────────────────────────────────────────────────────────── */
.sc-toggle-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f8f9fc;
  border-radius: 8px;
  cursor: pointer;
  user-select: none;
}
.sc-toggle-row:hover { background: #f0f2f5; }
.sc-toggle {
  width: 36px; height: 20px; border-radius: 10px;
  position: relative; flex-shrink: 0;
  background: #cbd5e0; transition: background .2s;
}
.sc-toggle--on { background: #2563eb; }
.sc-toggle-knob {
  width: 16px; height: 16px; border-radius: 50%;
  background: #fff; position: absolute; top: 2px; left: 2px;
  transition: left .2s;
}
.sc-toggle--on .sc-toggle-knob { left: 18px; }
.sc-toggle-label { font-size: 13px; font-weight: 600; color: #1a1a2e; }

/* ── Branding tab ──────────────────────────────────────────────────── */
.sc-branding-templates { display: flex; gap: 12px; flex-wrap: wrap; }
.sc-tmpl-btn {
  position: relative;
  display: flex; flex-direction: column; align-items: center;
  gap: 8px; padding: 16px 20px;
  border: 2px solid #e4e8f0; border-radius: 10px;
  background: #f8f9fc; cursor: pointer; min-width: 90px;
  transition: border-color .15s, background .15s;
}
.sc-tmpl-btn:hover { border-color: #93c5fd; background: #eff6ff; }
.sc-tmpl-btn--active { border-color: #2563eb; background: #eff6ff; }
.sc-tmpl-icon { color: #2563eb; }
.sc-tmpl-label { font-size: 12px; font-weight: 600; color: #374151; }
.sc-tmpl-check {
  position: absolute; top: -8px; right: -8px;
  width: 20px; height: 20px; border-radius: 50%;
  background: #2563eb; color: #fff;
  display: flex; align-items: center; justify-content: center;
}
.sc-color-row { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.sc-color-pick {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 14px; border: 1px solid #e4e8f0; border-radius: 8px; background: #fff;
}
.sc-color-swatch {
  width: 24px; height: 24px; border-radius: 4px;
  border: 1px solid rgba(0,0,0,.1); flex-shrink: 0;
}
.sc-color-hex { font-size: 13px; font-weight: 600; color: #374151; }
.sc-color-input { display: none; }

/* ── Responsive ────────────────────────────────────────────────────── */
@media (max-width: 900px) {
  .sc-body--two-col { grid-template-columns: 1fr; }
}
@media (max-width: 700px) {
  .sc-fg--three { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 600px) {
  .sc-fg { grid-template-columns: 1fr; }
  .sc-fg--three { grid-template-columns: 1fr; }
  .sc-full { grid-column: auto; }
  .sc-header { padding: 12px 16px 0; gap: 8px; }
  .sc-title { font-size: 17px; }
  .sc-save-btn { font-size: 12.5px; padding: 8px 14px; gap: 5px; }
  .sc-tabs {
    padding: 0;
    margin-top: 10px;
    mask-image: linear-gradient(to right, transparent 0, black 16px, black calc(100% - 16px), transparent 100%);
    -webkit-mask-image: linear-gradient(to right, transparent 0, black 16px, black calc(100% - 16px), transparent 100%);
    -webkit-overflow-scrolling: touch;
  }
  .sc-tab { padding: 10px 14px; font-size: 12.5px; }
  .sc-tab:first-child { padding-left: 20px; }
  .sc-tab:last-child  { padding-right: 20px; }
  .sc-body { padding: 14px; gap: 14px; }
  .sc-card { padding: 16px; }
  .sc-logo-area { flex-direction: column; }
  .sc-logo-box { width: 100%; height: 120px; }
}

/* ── Period Lock status ────────────────────────────────────────────── */
.sc-lock-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #fef3c7;
  border: 1px solid #fcd34d;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #92400e;
}
.sc-lock-status--none {
  background: #f0fdf4;
  border-color: #86efac;
  color: #14532d;
}
.sc-clear-lock-row { display: flex; }
.sc-card-icon--red { background: #fef2f2; color: #dc2626; }

/* ── Info / tips sidebar card ──────────────────────────────────────── */
.sc-info-card {
  background: linear-gradient(160deg, #f3f8ff 0%, #fbfdff 100%);
  border: 1px solid #dbeafe;
  border-left: 3px solid #2563eb;
  border-radius: 14px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(37,99,235,.05);
}
.sc-info-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #eaf1ff 0%, #d7e6ff 100%);
  color: #2563eb;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  box-shadow: 0 2px 6px rgba(37,99,235,.14);
}
.sc-info-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e40af;
  margin-bottom: 10px;
}
.sc-info-card--warn { background: linear-gradient(160deg, #fffaf0 0%, #fffdf8 100%); border-color: #fcd34d; border-left-color: #f59e0b; }
.sc-info-icon--red { background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); color: #dc2626; box-shadow: 0 2px 6px rgba(220,38,38,.16); }
.sc-info-title--red { color: #991b1b; }
.sc-info-body {
  font-size: 12px;
  color: #4b5563;
  line-height: 1.6;
}
.sc-info-body p { margin: 0 0 8px; }
.sc-info-body p:last-child { margin-bottom: 0; }
.sc-info-body ul { margin: 0; padding-left: 16px; }
.sc-info-body li { margin-bottom: 6px; }
.sc-info-body code {
  background: #e0e7ff;
  color: #3730a3;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 11px;
}

/* Logo area stacked variant (sidebar) */
.sc-logo-area--stacked { flex-direction: column; gap: 12px; }
.sc-logo-box--wide { width: 100%; height: 110px; }
.sc-logo-actions--row { flex-direction: row; flex-wrap: wrap; gap: 8px; align-items: center; }
</style>