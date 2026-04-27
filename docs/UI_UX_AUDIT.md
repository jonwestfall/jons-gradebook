# UI/UX Audit

Date: 2026-04-27

This audit reviewed the current React application as an instructor/advisor operations cockpit, then compared its patterns against Canvas LMS and Salesforce Education Cloud surfaces.

## External Patterns Reviewed

- Canvas Card View Dashboard emphasizes fast course recognition through course cards, nicknames, colors, and a dashboard sidebar for cross-course To Do items.
  Source: https://community.instructure.com/en/kb/articles/662815-how-do-i-view-my-courses-in-the-card-view-dashboard
- Canvas To Do/sidebar patterns keep upcoming work cross-course, limited, course-labeled, and action-oriented.
  Source: https://community.instructure.com/en/kb/articles/662818-how-do-i-use-the-to-do-list-and-sidebar-in-the-dashboard-as-a-student
- Salesforce Education Cloud positions Student Success around comprehensive student summaries, proactive advising, next-step automation, progress signals, and data-driven alerts.
  Source: https://www.salesforce.com/education/cloud/

## Audit Findings

1. Themeability was too implicit.
   The previous stylesheet used hard-coded warm tones across many surfaces. That made the app pleasant but harder to re-skin toward a minimal or higher-contrast operational interface.

2. The app shell had useful speed features but needed clearer mode signaling.
   Collapse, density, command palette, and sticky action bars were already present. Demo or screenshot usage had no global mode marker, creating a risk that screenshots could look like live data.

3. Dense operational pages were readable but visually louder than necessary.
   Cards, tables, controls, and panel backgrounds used several near-beige variants. A more neutral token set improves scanability and makes important alerts/actions stand out.

4. Course/student screenshots needed believable data without touching production records.
   The app had no built-in screenshot-safe path. Demo mode now answers common frontend API calls with local browser data.

5. Accessibility and readability needed stronger defaults.
   Focus states, button disabled states, theme contrast, card radius, and table header colors now use shared tokens.

## Implemented Improvements

- Added Settings -> Interface Preferences with:
  - Balanced, Minimal, and High Contrast themes
  - Demo mode switch
- Added browser-local demo API responses for:
  - dashboard summary
  - students list
  - student profile
  - courses list
  - course gradebook
  - tasks
  - rubrics and rubric evaluations
  - attendance roll call records
  - report templates, previews, history, and export results
  - documents targets/list/text
  - settings options
  - several empty-state supporting routes
- Added persistent global Demo mode labeling:
  - sidebar pill
  - top content banner on every screen
- Reworked core CSS tokens:
  - neutralized the background
  - removed decorative radial background treatment
  - reduced card radius to a tighter operational style
  - introduced theme variables for surfaces, text, lines, accent, focus, warning, error, and success
  - added minimal and high-contrast theme overrides
- Improved dashboard/course readability:
  - metric cards use consistent metric styling
  - course cards flow in a responsive grid

## Current UX Direction

The app should continue to feel like a quiet operations console, not a marketing dashboard. The best external patterns to keep borrowing are:

- Canvas-style course recognizability and cross-course action queues.
- Salesforce-style student 360 views, alert visibility, and automated next steps.
- Admin-console restraint: compact controls, durable labels, explicit modes, and readable tables.

## Follow-Up Recommendations

- Add route-level screenshot scripts for Demo mode so GitHub images can be regenerated consistently.
- Add a theme regression smoke test that toggles each theme and confirms the shell persists the selected setting.
- Consider a reusable page header component for title, subtitle, primary action, and mode/status chips.
- Continue reducing inline styles in pages as each workflow is revisited.
