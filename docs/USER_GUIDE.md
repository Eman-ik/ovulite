# Ovulite — User Guide

> **For:** Veterinarians, Embryologists, and ET Technicians  
> **Version:** 1.0

---

## 1. Getting Started

### Accessing the System
1. Open your browser and navigate to `http://localhost:5173`
2. Log in with your username and password
3. You'll see the main dashboard with system overview

### Navigation
The left sidebar provides access to all modules:
- **Dashboard** — System overview with key statistics
- **Data Entry** — View and manage ET transfer records
- **Predictions** — Get pregnancy predictions for transfers
- **Embryo Grading** — Upload blastocyst images for quality assessment
- **Lab QC** — Monitor lab quality and detect anomalies
- **Analytics** — Explore reproductive KPIs and protocol effectiveness

---

## 2. Data Entry

### Viewing Records
1. Click **Data Entry** in the sidebar
2. Browse the table of ET transfer records
3. Use pagination to navigate through records

### Adding New Transfers
1. Click **Data Entry** → **New Transfer**
2. Fill in the required fields:
   - **ET Date** — date of the embryo transfer
   - **Donor** — select the donor animal
   - **Recipient** — select the recipient
   - **CL Measure** — corpus luteum measurement in mm (must be 0–50mm)
   - **Protocol** — synchronization protocol used
   - **Technician** — performing technician
3. Optional fields: BC Score, Heat Day, CL Side, etc.
4. Click **Save** to submit

### Importing CSV Data
- Use the bulk import endpoint to upload historical data
- CSV must follow the ET Summary format
- Invalid records are rejected with specific error messages

---

## 3. Pregnancy Predictions

### Getting a Prediction
1. Navigate to **Predictions**
2. Enter the transfer parameters:
   - CL Measure (mm)
   - Heat Day
   - Protocol
   - Donor Breed
   - Semen Type
   - Fresh/Frozen
   - Technician
3. Click **Predict**

### Reading Results
- **Probability**: 0–100% chance of pregnancy
- **Risk Band**: Low (<30%), Medium (30–60%), High (>60%)
- **Confidence Interval**: 95% bootstrap CI showing uncertainty range
- **Feature Contributions**: SHAP values showing which factors push toward/against pregnancy

### Important Notes
- Predictions are **statistical estimates**, not guarantees
- Always consider confidence intervals — wide intervals mean uncertain predictions
- The model works best for inputs similar to the training data
- See [LIMITATIONS.md](LIMITATIONS.md) for when not to trust predictions

---

## 4. Embryo Grading

### Uploading an Image
1. Navigate to **Embryo Grading**
2. Click the upload area or drag & drop a blastocyst image
3. Optionally provide metadata (CL measure, BC score, donor breed)
4. Click **Grade Embryo**

### Reading Results
- **Grade**: High / Medium / Low quality classification
- **Class Probabilities**: Confidence in each grade level
- **Viability Score**: 0–1 continuous quality score
- **Heatmap**: Grad-CAM visualization showing which image regions influenced the grade

### Important Notes
- Grades are based on **pregnancy outcome pseudo-labels**, not traditional embryo grading
- The heatmap highlights model attention areas — compare with your morphological assessment
- Low confidence predictions (balanced probabilities) suggest uncertain quality

---

## 5. Lab QC Dashboard

### Viewing QC Status
1. Navigate to **Lab QC**
2. The dashboard shows:
   - **Summary cards**: Total records, anomalies detected, active alerts
   - **Control charts**: EWMA and CUSUM charts for key metrics
   - **Alerts table**: All detected anomalies with severity levels
   - **Technician stats**: Per-technician performance comparison

### Control Charts
- **EWMA Chart**: Smoothed trend with upper/lower control limits (UCL/LCL)
  - Red bars = out-of-control points (need investigation)
  - Hover for exact values
- **CUSUM Chart**: Cumulative sum detecting sustained shifts
  - Tall bars indicate persistent process changes

### Alerts
- **Critical** (red): Immediate attention needed — significant anomaly detected
- **Warning** (yellow): Noteworthy deviation — monitor closely
- **Info** (blue): Minor variation — for awareness only

### Running the Pipeline
- Click **Run Pipeline** to re-analyze with latest data
- Results are cached; click **Refresh** to reload

---

## 6. Analytics Dashboard

### Overview Tab
- **KPI Cards**: Total transfers, pregnancy rate, donors, embryo utilization
- **Fresh vs Frozen**: Comparison of pregnancy rates
- **IVF Funnel**: Conversion rates through the transfer pipeline
- **Monthly Trend**: Pregnancy rate over time

### Protocols Tab
- **Bar Chart**: Pregnancy rate per protocol with 95% confidence intervals
- **Detail Table**: Exact numbers for each protocol
- Wider confidence intervals mean less data → less certainty

### Donors Tab
- **Performance Chart**: Top donors by pregnancy rate
- **Detail Table**: Complete donor metrics including vs-mean comparison
- Green arrow = above average, Red arrow = below average

### Biomarkers Tab
- **CL Measure**: Sweet-spot analysis showing which CL sizes correlate with best outcomes
- **BC Score**: Body condition score analysis (if sufficient data)
- **Heat Day**: Optimal heat day range
- Green-highlighted bar = optimal range

---

## 7. Troubleshooting

| Issue | Solution |
|-------|----------|
| "Loading…" never resolves | Check if backend server is running (`docker compose up`) |
| "QC pipeline not available" | Click "Run QC Pipeline" to generate initial analysis |
| "Analytics pipeline failed" | Ensure CSV data is loaded; click "Run Pipeline" |
| Login token expired | You'll be redirected to login; re-authenticate |
| Prediction seems wrong | Check confidence interval; wide CI = uncertain; see limitations |
| No technician data in QC | Data needs technician_name column populated |

---

## 8. Technical Requirements

- **Browser**: Chrome 90+, Firefox 90+, Safari 15+, Edge 90+
- **Server**: Docker + Docker Compose
- **Network**: Access to `localhost:5173` (frontend) and `localhost:8000` (API)
- **For embryo grading**: GPU recommended for faster inference (CPU works but slower)
