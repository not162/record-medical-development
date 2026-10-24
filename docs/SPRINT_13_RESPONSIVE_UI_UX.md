# SPRINT 13 — RESPONSIVE UI/UX & MOBILE EXPERIENCE
**Full-Stack Evidence-Grounded Clinical AI Chatbot Agent**  
**Rumah Sakit Umum Kota Terpadu (RSUKT)**

---

## 1. Executive Summary & Design System
Sprint 13 solidifies Section 13 of the Clinical AI Engineering specification: delivering a premium, accessible, and responsive user experience for patients and medical administrators across desktop, tablet, and mobile displays.

---

## 2. Key UX Architectural Deliverables
1. **Separation of Workspaces**:
   - **Patient Clinical Workspace (`/chat`)**: Clean conversational interface, side drawer history, evidence citation expansion badges, and relative feedback buttons (+1.75% / -0.74%).
   - **Admin Research Command Center (`/admin/*`)**: Command console layout featuring 10 dedicated modules (Dashboard, Datasets, Imports, Knowledge Index, Annotations, Training Studio, Model Evaluation, Graph Visualization, Feedback Review, and Settings).
2. **Design Language (Dark Clinical Glassmorphism)**:
   - High-contrast typography optimized for readability (Inter / Roboto font metrics).
   - Glassmorphic panels with subtle glowing borders (`slate-800/80` to `slate-900/90`).
   - Standardized status tokens: Emerald (Approved/Healthy), Cyan (Processing/Action), Purple (Model/ML), Amber (Attention/Review), Red (Emergency/Red-flag).
3. **Mobile & Viewport Adaptation**:
   - Collapsible slide-over drawer navigation for viewports under 768px.
   - Fixed touch-friendly composer with viewport-aware mobile keyboard padding.
   - Responsive grid collapsing from 4 columns to 2 and 1 column without horizontal scrolling.

---

## 3. Prerendering & Build Validation
- **Next.js 16 (Turbopack)**: All 22 routes prerender statically with zero runtime errors.
- **Zero Mock UI Rule**: 100% of data rendered in admin panels binds directly to live SQLite WAL and FastAPI endpoints.
