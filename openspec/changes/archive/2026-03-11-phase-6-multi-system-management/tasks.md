## 1. Backend: ProjectDetail Schema Extension

- [x] 1.1 Add `completed_system_count` and `introduction_unlocked` fields to `ProjectDetail` schema in `backend/app/modules/projects/schemas.py`
- [x] 1.2 Implement completion computation in `_build_project_detail` in `backend/app/modules/projects/service.py` (count systems with status == Chapter_Approved, unlock at >= 3)
- [x] 1.3 Add backend tests for completion metrics in `backend/tests/modules/projects/test_projects_api.py` (0 completions, partial, threshold exact, above threshold)

## 2. Backend: System Restricted Deletion

- [x] 2.1 Add `delete_system` function in `backend/app/modules/systems/service.py` with pre-deletion checks (assets, manifests, workflow events)
- [x] 2.2 Add `DELETE /systems/{id}` endpoint in `backend/app/modules/systems/router.py` returning 204 on success, 409 on conflict, 404 on not found
- [x] 2.3 Add repository helper `has_associated_data` in `backend/app/modules/systems/repository.py` to check for assets, manifests, and workflow instances
- [x] 2.4 Add backend tests for restricted deletion in `backend/tests/modules/systems/test_systems_api.py` (empty system delete, system with assets 409, system with workflow 409, not found 404)

## 3. Backend: system_no Concurrent Safety

- [x] 3.1 Wrap `create_system` in `backend/app/modules/systems/service.py` with IntegrityError catch, mapping to 409 Conflict with retry hint
- [x] 3.2 Add backend test for concurrent system_no collision handling

## 4. Frontend: Project Layout and WebSocket

- [x] 4.1 Create `frontend/app/projects/[projectId]/layout.tsx` with project-level WebSocket provider and shared container styles
- [x] 4.2 Create `frontend/components/layout/ProjectBreadcrumb.tsx` breadcrumb component (Projects > Project Name > System Title)
- [x] 4.3 Integrate breadcrumb into project layout, resolving labels from projectDetail cache
- [x] 4.4 Refactor existing system workbench page to remove duplicated container styles (now provided by layout)

## 5. Frontend: Dashboard Enhancement

- [x] 5.1 Extract `deriveGateItems` from system workbench page to `frontend/lib/gates.ts` shared utility
- [x] 5.2 Create `frontend/components/dashboard/SystemCard.tsx` with gate progress bar, status badge, system title/number, and last update
- [x] 5.3 Create `frontend/components/dashboard/ProjectStats.tsx` with completion progress (X/3), introduction unlock indicator
- [x] 5.4 Refactor `frontend/app/projects/[projectId]/page.tsx` to use new SystemCard and ProjectStats components
- [x] 5.5 Add `useDeleteSystem` hook in `frontend/hooks/useProjects.ts` with React Query mutation and cache invalidation
- [x] 5.6 Add delete confirmation dialog to SystemCard with 409 error handling (descriptive toast)

## 6. Frontend: React Query and WebSocket Integration

- [x] 6.1 Add project-level WebSocket event handler that invalidates `projectDetail` query on `gate.passed`, `workflow.state_changed`, `task.succeeded` events (debounced 500ms)
- [x] 6.2 Ensure `useCreateSystem` and `useDeleteSystem` mutations invalidate `projectDetail` query on success
- [x] 6.3 Update `useProjectDetail` hook to include new `completedSystemCount` and `introductionUnlocked` fields in type definition

## 7. Testing and Verification

- [x] 7.1 Run `npm run typecheck` in frontend and verify zero errors
- [x] 7.2 Run backend test suite (`pytest backend/tests/modules/projects/ backend/tests/modules/systems/`) and verify all pass
- [x] 7.3 Add frontend smoke test for ProjectStats component (completedSystemCount display, introduction unlock state)
