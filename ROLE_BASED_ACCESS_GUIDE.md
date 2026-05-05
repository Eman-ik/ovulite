# Ovulite Role-Based Access Control Implementation

## Demo Users Created

All demo users use the password: `ovulite2026`

### 1. Admin Account
- **Username:** `admin`
- **Full Name:** System Administrator
- **Role:** Admin
- **Email:** admin@ovulite.local
- **Landing Page:** `/app/analytics` (Admin Dashboard)

### 2. Lab Technician / Embryologist Account
- **Username:** `lab_tech`
- **Full Name:** Ahmed Lab Technician
- **Role:** Embryologist
- **Email:** lab@ovulite.local
- **Landing Page:** `/app/embryo-grading` (Lab Dashboard)

### 3. ET Technician / Veterinarian Account
- **Username:** `et_tech`
- **Full Name:** Fatima ET Technician
- **Role:** ET Team
- **Email:** et@ovulite.local
- **Landing Page:** `/app/predictions` (ET Technician Dashboard)

---

## Role-Based Access Matrix

### Admin Dashboard (/app/analytics)

**Capabilities:**
- Full system control panel
- User management (create, edit, delete users)
- Complete analytics and KPI dashboard
- System settings and configuration
- Audit trail and compliance tracking
- Full data export and reporting

**Visible KPIs:**
- Total Users: 12 (Active accounts)
- Embryo Transfers: 847 (This season)
- Pregnancy Rate: 68.5% (Current cycle)
- Model Confidence: 94.2% (AI predictions)

**Modules:**
- User Management - Create/manage lab staff, technicians, vets
- Analytics & Reports - Comprehensive system analytics
- System Settings - Configure protocols and preferences
- Audit & Compliance - Track all system activities

---

### Lab Dashboard (/app/embryo-grading)

**Capabilities:**
- Embryo production and grading
- Lab data entry (donor, OPU, embryo records)
- AI embryo grading with confidence scores
- Lab quality control monitoring
- Lab-specific reporting and analytics

**Visible KPIs:**
- Today's OPU: 24 (Oocytes collected)
- Embryos Graded: 156 (This week)
- Lab QC Alerts: 2 (Requires attention)
- Cold Chain Temp: 5.2°C (Within specification)

**Modules:**
- Data Entry & Records - Record donor, OPU, and embryo data
- Embryo Grading - Grade embryos and generate AI analysis
- Lab Quality Control - Monitor and manage lab KPIs
- Lab Reports - Generate lab-specific reports

**Can Enter:**
- Donor ID and sire information
- OPU date and oocyte data
- Embryo stage and grade
- Fresh/frozen status
- Media lot and technician name
- Embryo images for AI grading

---

### ET Technician Dashboard (/app/predictions)

**Capabilities:**
- Embryo transfer operations management
- Recipient record management
- Estrus synchronization tracking
- Pregnancy prediction before transfer
- Pregnancy outcome recording

**Visible KPIs:**
- Transfers This Week: 18 (Scheduled procedures)
- Success Rate: 71.2% (30-day pregnancy)
- Pending Outcomes: 34 (Awaiting results)
- My Cases: 156 (Assigned to me)

**Modules:**
- Recipient Management - Add and manage recipient records
- Synchronization - Track estrus synchronization protocols
- Embryo Transfer - Record transfer procedures
- Pregnancy Outcome - Record pregnancy check results

**Can Enter:**
- Recipient ID and breed information
- Lactation status and health history
- CL assessment and P4 levels
- Synchronization protocol
- Embryo selected for transfer
- ET date and technique notes
- Pregnancy check results (day 30, 45, 90)

---

## Feature Access by Role

| Feature | Admin | Embryologist | ET Team |
|---------|-------|--------------|---------|
| Login | ✓ | ✓ | ✓ |
| Main Dashboard | Full | Lab-focused | ET-focused |
| User Management | ✓ | ✗ | ✗ |
| Donor Data Entry | View all | ✓ | View only |
| OPU Data Entry | View all | ✓ | ✗ |
| Embryo Data Entry | View all | ✓ | View selected |
| Embryo Grading | View all | ✓ | View only |
| Recipient Data Entry | View all | Minimal | ✓ |
| Pregnancy Prediction | View all | ✓ | ✓ |
| Embryo Transfer Entry | View all | View only | ✓ |
| Pregnancy Outcome Entry | View all | Limited | ✓ |
| Analytics Dashboard | Full | Lab analytics | ET analytics |
| Lab QC Monitoring | Full | ✓ | ✗ |
| Reports & Export | Full | Lab only | ET only |
| Audit Trail | ✓ | ✗ | ✗ |
| System Settings | ✓ | ✗ | ✗ |

---

## How Role-Based Access Works

### 1. Authentication
- User logs in with username and password
- System authenticates credentials

### 2. Role Detection
- User role is stored in database (`admin`, `embryologist`, `et team`)
- Role is included in JWT token

### 3. Dashboard Routing
- After login, `getRoleLandingPath()` function determines landing page:
  - **Admin** → `/app/analytics` (Admin Dashboard)
  - **Embryologist** → `/app/embryo-grading` (Lab Dashboard)
  - **ET Team** → `/app/predictions` (ET Dashboard)

### 4. Permissions Enforcement
- `ROLE_PERMISSIONS` object in `roleRoutes.ts` defines capabilities:
  - `canManageUsers`
  - `canViewAnalytics`
  - `canEnterLabData`
  - `canEnterETData`
  - `canGradeEmbryos`
  - etc.

### 5. UI Customization
- `RoleBasedDashboard` component displays role-specific interface
- Each role sees different KPIs, modules, and features
- Admin sees full system; other roles see focused dashboards

---

## Testing the System

### Test Scenario 1: Admin Login
1. Go to login page
2. Enter `admin` / `ovulite2026`
3. Should land on `/app/analytics` with:
   - Full system control panel
   - User management options
   - Complete analytics dashboard
   - System settings access

### Test Scenario 2: Lab Technician Login
1. Go to login page
2. Enter `lab_tech` / `ovulite2026`
3. Should land on `/app/embryo-grading` with:
   - Lab dashboard with embryo KPIs
   - Data entry modules
   - Embryo grading interface
   - Lab QC monitoring

### Test Scenario 3: ET Technician Login
1. Go to login page
2. Enter `et_tech` / `ovulite2026`
3. Should land on `/app/predictions` with:
   - ET dashboard with transfer KPIs
   - Recipient management
   - Synchronization tracking
   - Pregnancy outcome entry

---

## Key Files Modified

- **Backend:**
  - `/backend/app/models/user.py` - Added "et team" role to constraints
  - `/backend/seed_roles_local.py` - Creates demo users in database

- **Frontend:**
  - `/frontend/src/lib/roleRoutes.ts` - Enhanced with permissions and display names
  - `/frontend/src/components/RoleBasedDashboard.tsx` - New role-based dashboard component
  - `/frontend/src/pages/DashboardPage.tsx` - Updated to route based on role

---

## Next Steps for Full Implementation

To complete the 30% implementation across all major modules:

### Phase 1: Admin Module
- [x] Admin Dashboard with full KPIs
- [ ] User Management Interface
- [ ] Analytics & Reports Module
- [ ] System Settings & Configuration

### Phase 2: Lab Module
- [x] Lab Dashboard with embryo KPIs
- [ ] Donor Data Entry Screen
- [ ] OPU Record Entry
- [ ] Embryo Record Entry & Grading
- [ ] Lab QC Monitoring

### Phase 3: ET Module
- [x] ET Technician Dashboard
- [ ] Recipient Entry Form
- [ ] Synchronization Record Entry
- [ ] Embryo Transfer Entry
- [ ] Pregnancy Outcome Recording

---

## Database Overview

The `users` table in PostgreSQL now contains:

```sql
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) CHECK (role IN ('admin', 'veterinarian', 'embryologist', 'viewer', 'et team')),
    full_name VARCHAR(200),
    email VARCHAR(200),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

Current demo users are already seeded into this table.
