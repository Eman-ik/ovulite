# Ovulite UI Interface Details

## Typography System

### Font Stack
- **Primary/Display Font:** Axiforma (geometric, modern display typeface)
- **Secondary/Body Font:** Gotham Pro (clean, readable body text)
- **Code Font:** JetBrains Mono

### Implementation
- **Location:** `frontend/src/index.css`
- **Method:** CSS custom properties with `!important` overrides for global consistency
- **CSS Variables:**
  - `--font-display`: Axiforma with fallbacks to Gotham Rounded, Avenir Next, Montserrat, Segoe UI
  - `--font-body`: Gotham Pro with fallbacks to Avenir Next, Montserrat, Segoe UI, sans-serif
  - `--font-mono`: JetBrains Mono with fallbacks to Monaco, Courier New, monospace

### Global Font Override Strategy
```css
* {
  font-family: var(--font-body) !important;
}
h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-display) !important;
}
code, pre {
  font-family: var(--font-mono) !important;
}
```

---

## Pages and Components

### 1. DashboardPage.tsx
**Purpose:** Real-time ET analytics dashboard with key performance indicators and charts

**Features:**
- Parses ET dataset CSV to derive metrics in real-time
- Monthly aggregation and analytics
- Outcome-based statistics (success/failure rates)
- Technician and protocol performance tracking
- Multiple data visualization charts

**Data Source:**
- CSV Path: `/docs/dataset/ET%20Summary%20-%20ET%20Data.csv` (legacy)
- Updated Path: `/datasets/ET%20Summary%20-%20ET%20Data.csv`

**Key KPIs Displayed:**
- Monthly ET transfers
- Success/failure outcomes
- Protocol comparisons
- Technician performance metrics

---

### 2. DataEntryPage.tsx
**Purpose:** ET transfer record management with import/export capabilities

**Features:**
- Manual ET record entry
- Sample dataset loading functionality
- CSV import/export features
- Data validation

**Sample Dataset Loader Issue (RESOLVED):**
- **Problem:** "Load sample dataset" button showed dashes (—) in every column
- **Root Cause:** Sample data fetched from `/docs/dataset/ET%20Summary%20-%20ET%20Data.csv` returned HTML (Vite app shell) instead of raw CSV
- **Solution:** 
  - Copied CSV to `frontend/public/datasets/ET%20Summary%20-%20ET%20Data.csv`
  - Updated fetch URL to `/datasets/ET%20Summary%20-%20ET%20Data.csv`
  - Verified: HTTP 200 response with correct `text/csv` MIME type

**Load Sample Function:**
```typescript
loadSampleDataset()
  - Fetches: '/datasets/ET%20Summary%20-%20ET%20Data.csv'
  - Parses CSV locally
  - Populates table with parsed records
```

---

### 3. PredictionPage.tsx
**Purpose:** AI pregnancy prediction form with SHAP explainability panel

**Key Features:**
- Prediction form input
- Result display with confidence metrics
- Confidence interval sparkline chart (Recharts LineChart)
- SHAP feature contributions panel

**Type Definitions:**

```typescript
interface PredictionResult {
  prediction: number;           // Predicted probability (0-1)
  confidence: number;           // Confidence level
  interval: [number, number];   // Confidence interval (min, max)
  shap_explanation: {
    base_value: number;         // SHAP base value
    contributions: ShapContribution[];
  };
}

interface ShapContribution {
  feature: string;              // Feature name (e.g., "cl_measure_mm")
  value: number;                // SHAP value (positive/negative contribution)
}
```

**Type Guard Function:**
```typescript
function isPredictionResult(data: unknown): data is PredictionResult
```

**SHAP Feature Contributions Panel (Lines 842-882):**
- **Rendering Condition:** 
  ```
  prediction && resultVisible && prediction.shap_explanation.contributions.length > 0
  ```
- **Display Elements:**
  - Feature name (formatted via `formatFeatureName()`)
  - SHAP value badge
  - Horizontal contribution bar
  - Separate styling for positive (increasing probability) vs negative (decreasing probability)

**Feature Name Formatter:**
```typescript
function formatFeatureName(name: string): string {
  // Handles feature names with __ separator patterns
  // Example: "cl_measure_mm" → "Cl Measure Mm"
  // Example: "protocol__IVF" → "Protocol: IVF"
  
  if (name.includes("__")) {
    const [base, value] = name.split("__");
    const label = base.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    return `${label}: ${value}`;
  }
  return name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}
```

**SHAP Contributions Issue (ACTIVE):**
- **Problem:** Feature Contributions panel "not working at all" - not rendering
- **Likely Causes:**
  1. Prediction API (`/predict/pregnancy`) not returning `shap_explanation.contributions` array
  2. Array is empty (`contributions.length === 0`)
  3. Prediction object is null/undefined in state
  4. Type guard `isPredictionResult()` rejecting API response
  5. Missing `formatFeatureName()` function definition or execution errors
- **CSS Classes Used:**
  - `.pp-panel` - panel container
  - `.pp-result-enter` - animation class
  - `.pp-panel-header` - header section
  - `.pp-panel-title` - title text
  - `.pp-panel-sub` - subtitle/description
  - `.pp-panel-body` - content area
  - `.pp-shap-item` - individual contribution item

---

## Public Assets and Data Files

### CSV Data Location
- **New Path (Public Assets):** `frontend/public/datasets/ET%20Summary%20-%20ET%20Data.csv`
- **Served URL:** `http://localhost:5175/datasets/ET%20Summary%20-%20ET%20Data.csv`
- **MIME Type:** `text/csv`
- **Status:** ✓ Verified working

### CSV Headers
```
ET, Lab, Satellite, Date, Age, Protocol, Technique, Grade, Follicles, 
CL Measure, Collection Good, Degeneration, Maturation, Fertilization, 
Embryo Type, Development, Transfer, Pregnancy Outcome, Additional Notes
```

---

## Development Environment

**Frontend Framework:**
- React 18+ with TypeScript
- Vite development server
- Port: `5175`
- Build tool: Vite

**Styling:**
- Tailwind CSS
- Custom CSS with CSS variables
- PostCSS

**Data Visualization:**
- Recharts for charts
  - LineChart (confidence intervals)
  - AreaChart
  - BarChart
  - PieChart

**Features:**
- TypeScript strict mode enabled
- ESLint configured
- PostCSS config at `postcss.config.mjs`
- Tailwind config at `tailwind.config.ts`

---

## CSS Files and Structure

### `frontend/src/index.css`
- **Purpose:** Global styles and typography foundation
- **Changes Made:**
  - Removed Merriweather serif import
  - Added CSS custom properties for Axiforma/Gotham Pro/JetBrains Mono
  - Added `!important` overrides for global font application
  - Ensured all text elements use defined font variables

### Page-Specific Styling
- **DashboardPage:** Contains local Syne, JetBrains Mono font declarations (overridden by global)
- **PredictionPage:** Contains local font declarations (overridden by global)
- **All pages:** Use Tailwind CSS classes with custom CSS variables

---

## Known Issues and Resolutions

| Issue | Status | Description | Resolution |
|-------|--------|-------------|-----------|
| Site-wide typography (Merriweather) | ✓ RESOLVED | Needed Axiforma/Gotham Pro branding | Implemented CSS variable system with `!important` overrides |
| Sample dataset showing dashes | ✓ RESOLVED | CSV fetch from unreachable `/docs/dataset/` path | Moved CSV to public folder, updated fetch URL |
| SHAP Feature Contributions not displaying | ⏳ ACTIVE | Panel not rendering or showing contributions | Pending diagnosis - likely API response or state issue |

---

## API Integration Points

### Prediction Endpoint
- **Endpoint:** `/predict/pregnancy`
- **Method:** POST
- **Expected Response:** `PredictionResult` type
- **Critical Fields for UI:**
  - `shap_explanation.contributions[]` - Must be non-empty array
  - Each contribution requires `feature` (string) and `value` (number)

---

## UI/UX Details

### Color and Styling Convention
- **Positive contributions (increasing probability):** Green/positive color
- **Negative contributions (decreasing probability):** Red/negative color
- **SHAP bars:** Width scaled to max absolute value for visual comparison
- **Animation:** Staggered entrance animations with `animationDelay`

### Text Processing
- Feature names are humanized (underscores → spaces, capitalize words)
- Special patterns like `feature__value` are split and formatted as "Feature: Value"

### Layout Components
- Panel with header and body structure
- Staggered animation for multiple items
- Horizontal bar charts for contribution magnitude
- Responsive design using Tailwind CSS

---

## Files Modified/Created During UI Work

1. **`frontend/src/index.css`** - Typography system implementation
2. **`frontend/src/pages/DataEntryPage.tsx`** - Sample loader URL update
3. **`frontend/public/datasets/ET%20Summary%20-%20ET%20Data.csv`** - Created (copied from docs)

---

## Summary

This document captures all UI interface details from the Ovulite project including:
- ✓ Global typography system (Axiforma/Gotham Pro)
- ✓ Sample dataset loading (fixed CSV serving)
- ⏳ SHAP feature contributions (pending investigation)
- Complete component structures, type definitions, and styling approaches
- Development environment and asset management details
