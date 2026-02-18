# Manufacturing Database Schema

## Overview

Sample manufacturing execution system database with 30 days of production data across 4 production lines.

**Database:** SQLite
**File:** sample_manufacturing.db
**Total Records:** 949

---

## Tables

### 1. line_master (4 records)

Production lines and their specifications.

| Column | Type | Description |
|---|---|---|
| line_id | TEXT (PK) | Unique line identifier (LINE-1, LINE-2, etc.) |
| line_name | TEXT | Human-readable line name |
| capacity_per_hour | INTEGER | Maximum units per hour |
| location | TEXT | Physical location |
| status | TEXT | active / inactive |

**Sample Data:**
```
LINE-1 | Assembly Line 1 | 500 units/hr | Building A
LINE-2 | Assembly Line 2 | 450 units/hr | Building A
LINE-3 | Packaging Line 1 | 800 units/hr | Building B
LINE-4 | Quality Control Line | 300 units/hr | Building C
```

---

### 2. products (4 records)

Products manufactured in the facility.

| Column | Type | Description |
|---|---|---|
| product_id | TEXT (PK) | Unique product identifier |
| product_name | TEXT | Product name |
| product_type | TEXT | Category (Chemical, Polymer, Coating, Adhesive) |
| unit | TEXT | Unit of measure (kg, liter) |
| standard_cost | REAL | Standard cost per unit |

**Sample Data:**
```
PROD-101 | ChemX-500 | Chemical | kg | $45.50
PROD-102 | PolyBlend-A | Polymer | kg | $62.00
PROD-103 | SurfaceCoat-Pro | Coating | liter | $78.25
PROD-104 | AdhesivePrime | Adhesive | kg | $52.75
```

---

### 3. recipes (4 records)

Manufacturing recipes for each product.

| Column | Type | Description |
|---|---|---|
| recipe_id | TEXT (PK) | Unique recipe identifier |
| product_id | TEXT (FK) | References products |
| recipe_name | TEXT | Recipe description |
| version | TEXT | Recipe version |
| cycle_time_minutes | INTEGER | Expected cycle time |

**Sample Data:**
```
RCP-A1 | ChemX Standard Process | v2.1 | 45 min
RCP-B2 | PolyBlend Fast Cure | v1.3 | 60 min
RCP-C3 | SurfaceCoat High Gloss | v3.0 | 30 min
RCP-D4 | AdhesivePrime Quick Set | v2.5 | 40 min
```

---

### 4. staff (6 records)

Employees and their roles.

| Column | Type | Description |
|---|---|---|
| staff_id | TEXT (PK) | Unique staff identifier |
| name | TEXT | Employee name |
| role | TEXT | Supervisor / Operator / QC Inspector |
| shift_preference | TEXT | day / night |
| hire_date | TEXT | Date hired |

**Sample Data:**
```
EMP-001 | John Davis | Supervisor | day
EMP-002 | Sarah Chen | Supervisor | night
EMP-003 | Michael Brown | Operator | day
EMP-004 | Lisa Wang | Operator | night
EMP-005 | Robert Taylor | QC Inspector | day
EMP-006 | Emily Martinez | Supervisor | day
```

---

### 5. shift_logs (240 records)

Daily shift records for each production line.

| Column | Type | Description |
|---|---|---|
| shift_id | TEXT (PK) | Unique shift identifier |
| line_id | TEXT (FK) | References line_master |
| supervisor_id | TEXT (FK) | References staff |
| shift_date | TEXT | Date of shift (YYYY-MM-DD) |
| start_time | TEXT | Shift start (HH:MM:SS) |
| end_time | TEXT | Shift end (HH:MM:SS) |
| shift_type | TEXT | day / night |
| notes | TEXT | Optional notes |

**Coverage:** 30 days × 4 lines × 2 shifts/day = 240 records

**Sample Data:**
```
SH-1000 | LINE-1 | EMP-001 | 2026-01-18 | 06:00 - 14:00 | day
SH-1001 | LINE-1 | EMP-002 | 2026-01-18 | 22:00 - 06:00 | night
```

---

### 6. production_orders (117 records)

Manufacturing orders executed over 30 days.

| Column | Type | Description |
|---|---|---|
| order_id | TEXT (PK) | Unique order identifier |
| product_id | TEXT (FK) | References products |
| recipe_id | TEXT (FK) | References recipes |
| line_id | TEXT (FK) | References line_master |
| shift_id | TEXT (FK) | References shift_logs |
| quantity_planned | REAL | Target quantity |
| quantity_actual | REAL | Actual output |
| unit | TEXT | Unit of measure |
| start_time | TEXT | Order start timestamp |
| end_time | TEXT | Order end timestamp |
| status | TEXT | completed / in_progress / cancelled |

**Yield Range:** 85-98% (realistic manufacturing variance)

**Sample Data:**
```
PO-1000 | PROD-101 | RCP-A1 | LINE-2 | SH-1015 | 1200 kg planned | 1092 kg actual | 91% yield
```

---

### 7. production_steps (578 records)

Step-by-step execution log for each order.

| Column | Type | Description |
|---|---|---|
| step_id | TEXT (PK) | Unique step identifier |
| order_id | TEXT (FK) | References production_orders |
| step_number | INTEGER | Sequence number |
| step_name | TEXT | Step description |
| start_time | TEXT | Step start timestamp |
| end_time | TEXT | Step end timestamp |
| status | TEXT | completed / in_progress / failed |
| operator_id | TEXT (FK) | References staff |
| temperature | REAL | Temperature (if applicable) |
| pressure | REAL | Pressure (if applicable) |
| notes | TEXT | Optional notes |

**Common Steps:** Material Preparation, Mixing, Heating, Reaction, Cooling, Quality Check, Packaging

**Sample Data:**
```
STEP-1 | PO-1000 | 1 | Material Preparation | 06:15 - 06:35 | EMP-003
STEP-2 | PO-1000 | 2 | Mixing | 06:35 - 07:00 | EMP-003
STEP-3 | PO-1000 | 3 | Heating | 07:00 - 07:30 | 85.2°C | EMP-003
```

---

## Relationships

```
products ──┐
           ├──▶ recipes ──▶ production_orders ──▶ production_steps
           │                     │
line_master ───────────────────┤
                                │
shift_logs ─────────────────────┤
   │                            │
   └── staff ◀──────────────────┘
```

---

## Sample Natural Language Queries

These queries should work with the conversational analytics system:

1. "What was the yield for LINE-3 this week?"
2. "Which supervisor had the best performance last month?"
3. "Show me details for order PO-1042"
4. "How many orders did we complete yesterday?"
5. "What's the average cycle time for ChemX-500?"
6. "Compare yield between day shift and night shift"
7. "Which line has the most downtime?" (simulated via completed orders)
8. "Plot yield trend for the last 10 days"
9. "What products did we make on 2026-02-14?"
10. "Who are our supervisors and how many shifts have they worked?"

---

## Data Generation Notes

- **Time Range:** Last 30 days from current date
- **Orders per Day:** 3-5 random orders
- **Yield Variance:** 85-98% of planned quantity (realistic manufacturing loss)
- **Shifts:** 2 per day per line (day + night)
- **Steps per Order:** 4-6 steps randomly selected from standard process steps
- **All timestamps are realistic and sequential**

---

*Database created for AI Intime validation project | Varaun Gandhi*
