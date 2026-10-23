# Toàn bộ API v1 trong source

Chưa đo runtime từng route. Cờ source là mục cần xem xét, không khẳng định lỗi. Đọc README.md để phân biệt phần đã sửa và phần còn tồn tại.

| Method | Route | Source | Pagination params | Source flags |
|---|---|---|---|---|
| POST | `/api/v1/admin-api/test-connection` | app/api/v1/endpoints/admin_helpers.py:325 | — | — |
| GET | `/api/v1/admin-api/connections-by-provider/{provider_id}` | app/api/v1/endpoints/admin_helpers.py:570 | — | materializes_all_review |
| GET | `/api/v1/admin-api/provider-models/{provider_id}` | app/api/v1/endpoints/admin_helpers.py:597 | — | materializes_all_review |
| POST | `/api/v1/admin-api/provider-models/{model_id}/priority` | app/api/v1/endpoints/admin_helpers.py:613 | — | — |
| POST | `/api/v1/admin-api/provider-models/reorder` | app/api/v1/endpoints/admin_helpers.py:641 | — | await_in_loop_review |
| POST | `/api/v1/admin-api/connections/{connection_id}/toggle-active` | app/api/v1/endpoints/admin_helpers.py:661 | — | — |
| POST | `/api/v1/admin-api/test-websearch` | app/api/v1/endpoints/admin_helpers.py:701 | — | — |
| POST | `/api/v1/admin-api/detect-key` | app/api/v1/endpoints/admin_helpers.py:772 | — | — |
| GET | `/api/v1/admin-api/providers-summary` | app/api/v1/endpoints/admin_helpers.py:933 | — | materializes_all_review |
| GET | `/api/v1/admin-api/antigravity/auth-url` | app/api/v1/endpoints/admin_helpers.py:963 | — | — |
| GET | `/api/v1/admin-api/antigravity/check-status` | app/api/v1/endpoints/admin_helpers.py:972 | — | — |
| POST | `/api/v1/admin-api/antigravity/exchange` | app/api/v1/endpoints/admin_helpers.py:1020 | — | — |
| GET | `/api/v1/admin-api/antigravity/callback` | app/api/v1/endpoints/admin_helpers.py:1118 | — | — |
| GET | `/api/v1/ads/check` | app/api/v1/endpoints/ads.py:56 | — | — |
| POST | `/api/v1/ads/complete` | app/api/v1/endpoints/ads.py:84 | — | — |
| POST | `/api/v1/ads/track-download` | app/api/v1/endpoints/ads.py:123 | — | — |
| GET | `/api/v1/ads/config` | app/api/v1/endpoints/ads.py:161 | — | — |
| POST | `/api/v1/analyze/start` | app/api/v1/endpoints/analyze.py:82 | — | materializes_all_review |
| POST | `/api/v1/analyze/stream` | app/api/v1/endpoints/analyze.py:260 | — | materializes_all_review |
| POST | `/api/v1/analyze/generate-quotation-cad` | app/api/v1/endpoints/analyze.py:490 | — | — |
| POST | `/api/v1/analyze/generate-quotation-cad/stream` | app/api/v1/endpoints/analyze.py:547 | — | — |
| GET | `/api/v1/analyze/project/{project_id}/latest` | app/api/v1/endpoints/analyze.py:620 | — | — |
| POST | `/api/v1/analyze/refine` | app/api/v1/endpoints/analyze.py:649 | — | — |
| POST | `/api/v1/analyze/finalize` | app/api/v1/endpoints/analyze.py:686 | — | — |
| GET | `/api/v1/analyze/project/{project_id}/sessions` | app/api/v1/endpoints/analyze.py:696 | skip, limit | — |
| GET | `/api/v1/analyze/iteration/{iteration_id}` | app/api/v1/endpoints/analyze.py:769 | — | — |
| DELETE | `/api/v1/analyze/iteration/{iteration_id}` | app/api/v1/endpoints/analyze.py:811 | — | — |
| GET | `/api/v1/analyze/history/{session_id}` | app/api/v1/endpoints/analyze.py:841 | skip, limit | — |
| DELETE | `/api/v1/analyze/project/{project_id}/session` | app/api/v1/endpoints/analyze.py:879 | — | materializes_all_review, await_in_loop_review |
| POST | `/api/v1/analyze/prompt` | app/api/v1/endpoints/analyze.py:925 | — | — |
| POST | `/api/v1/analyze/async-start` | app/api/v1/endpoints/analyze.py:1265 | — | — |
| GET | `/api/v1/analyze/task/{task_id}` | app/api/v1/endpoints/analyze.py:1273 | — | — |
| POST | `/api/v1/analyze/task/{task_id}/cancel` | app/api/v1/endpoints/analyze.py:1288 | — | — |
| POST | `/api/v1/analyze/start-multi-agent` | app/api/v1/endpoints/analyze_multi_agent.py:36 | — | materializes_all_review |
| GET | `/api/v1/analyze/test-multi-agent` | app/api/v1/endpoints/analyze_multi_agent.py:203 | — | — |
| GET | `/api/v1/articles` | app/api/v1/endpoints/articles.py:34 | page, page_size | — |
| GET | `/api/v1/articles/{slug}` | app/api/v1/endpoints/articles.py:56 | — | — |
| POST | `/api/v1/auth/send-otp` | app/api/v1/endpoints/auth.py:49 | — | — |
| POST | `/api/v1/auth/register` | app/api/v1/endpoints/auth.py:77 | — | — |
| POST | `/api/v1/auth/login` | app/api/v1/endpoints/auth.py:139 | — | — |
| POST | `/api/v1/auth/refresh` | app/api/v1/endpoints/auth.py:175 | — | — |
| POST | `/api/v1/auth/logout` | app/api/v1/endpoints/auth.py:201 | — | — |
| POST | `/api/v1/auth/google` | app/api/v1/endpoints/auth.py:205 | — | — |
| POST | `/api/v1/bom/calculate` | app/api/v1/endpoints/bom.py:26 | — | — |
| GET | `/api/v1/bom/topology/{project_id}` | app/api/v1/endpoints/bom.py:122 | — | — |
| GET | `/api/v1/bom/enclosure-preview/{project_id}` | app/api/v1/endpoints/bom.py:129 | — | — |
| GET | `/api/v1/cabinet-templates` | app/api/v1/endpoints/cabinet_templates.py:28 | — | — |
| GET | `/api/v1/cabinet-templates/separation-forms` | app/api/v1/endpoints/cabinet_templates.py:39 | — | — |
| GET | `/api/v1/cabinet-templates/catalog` | app/api/v1/endpoints/cabinet_templates.py:47 | — | — |
| POST | `/api/v1/cabinet-templates/generate` | app/api/v1/endpoints/cabinet_templates.py:56 | — | — |
| GET | `/api/v1/cabinet-templates/{template_id}/source` | app/api/v1/endpoints/cabinet_templates.py:71 | — | — |
| GET | `/api/v1/cabinet-templates/{template_id}/preview` | app/api/v1/endpoints/cabinet_templates.py:80 | — | — |
| GET | `/api/v1/cad-agent/providers` | app/api/v1/endpoints/cad_agent.py:17 | — | materializes_all_review |
| GET | `/api/v1/cad-agent/providers/{provider_id}/models` | app/api/v1/endpoints/cad_agent.py:42 | — | — |
| POST | `/api/v1/cad-agent/providers/{provider_id}/inference` | app/api/v1/endpoints/cad_agent.py:53 | — | — |
| GET | `/api/v1/cad-library/catalog-tb` | app/api/v1/endpoints/cad_library.py:78 | — | — |
| GET | `/api/v1/cad-library/catalog-tb/view/{view_id}/preview` | app/api/v1/endpoints/cad_library.py:94 | — | — |
| GET | `/api/v1/cad-library/catalog-tb/view/{view_id}/insert-dxf` | app/api/v1/endpoints/cad_library.py:102 | — | — |
| GET | `/api/v1/cad-library` | app/api/v1/endpoints/cad_library.py:184 | — | — |
| GET | `/api/v1/cad-library/categories` | app/api/v1/endpoints/cad_library.py:193 | — | — |
| GET | `/api/v1/cad-library/{asset_id}/dxf` | app/api/v1/endpoints/cad_library.py:203 | — | — |
| GET | `/api/v1/cad-library/grouped` | app/api/v1/endpoints/cad_library.py:233 | skip, limit | — |
| GET | `/api/v1/cad-library/{asset_id}/preview` | app/api/v1/endpoints/cad_library.py:244 | — | — |
| GET | `/api/v1/cad-library/{asset_id}/insert-dxf` | app/api/v1/endpoints/cad_library.py:251 | — | — |
| GET | `/api/v1/catalog-prices/custom-prices` | app/api/v1/endpoints/catalog_prices.py:82 | — | — |
| POST | `/api/v1/catalog-prices/custom-prices` | app/api/v1/endpoints/catalog_prices.py:95 | — | — |
| PUT | `/api/v1/catalog-prices/custom-prices/{key:path}` | app/api/v1/endpoints/catalog_prices.py:119 | — | — |
| DELETE | `/api/v1/catalog-prices/custom-prices/{key:path}` | app/api/v1/endpoints/catalog_prices.py:142 | — | — |
| POST | `/api/v1/catalog-prices/custom-prices/web-search` | app/api/v1/endpoints/catalog_prices.py:158 | — | materializes_all_review |
| POST | `/api/v1/catalog-prices/catalog/resolve-price` | app/api/v1/endpoints/catalog_prices.py:213 | — | — |
| GET | `/api/v1/catalog-prices/cad-registry/groups` | app/api/v1/endpoints/catalog_prices.py:241 | — | — |
| GET | `/api/v1/catalog-prices/cad-registry/search` | app/api/v1/endpoints/catalog_prices.py:254 | — | — |
| GET | `/api/v1/catalog-prices/catalog/missing-prices` | app/api/v1/endpoints/catalog_prices.py:266 | — | — |
| POST | `/api/v1/chat/` | app/api/v1/endpoints/chat.py:46 | — | — |
| GET | `/api/v1/curated-library` | app/api/v1/endpoints/curated_library.py:9 | — | — |
| GET | `/api/v1/curated-library/product/dxf` | app/api/v1/endpoints/curated_library.py:13 | — | — |
| GET | `/api/v1/curated-library/shell/{template_id}/dxf` | app/api/v1/endpoints/curated_library.py:20 | — | — |
| GET | `/api/v1/curated-library/asset/{asset_id}/dxf` | app/api/v1/endpoints/curated_library.py:27 | — | — |
| GET | `/api/v1/device-catalog` | app/api/v1/endpoints/device_catalog.py:13 | skip, limit | — |
| GET | `/api/v1/device-catalog/documents/{document_id}` | app/api/v1/endpoints/device_catalog.py:41 | — | — |
| GET | `/api/v1/device-library/brands` | app/api/v1/endpoints/devices.py:102 | — | materializes_all_review |
| GET | `/api/v1/device-library/categories` | app/api/v1/endpoints/devices.py:110 | — | materializes_all_review |
| GET | `/api/v1/device-library/series` | app/api/v1/endpoints/devices.py:118 | — | materializes_all_review |
| GET | `/api/v1/device-library/models` | app/api/v1/endpoints/devices.py:190 | skip, limit | — |
| GET | `/api/v1/device-library/browse` | app/api/v1/endpoints/devices.py:286 | skip, limit | materializes_all_review |
| PATCH | `/api/v1/device-library/model-details/{model_id}` | app/api/v1/endpoints/devices.py:351 | — | — |
| GET | `/api/v1/device-library/model-details/{model_id}` | app/api/v1/endpoints/devices.py:393 | — | — |
| GET | `/api/v1/device-library/models/{sku}` | app/api/v1/endpoints/devices.py:402 | — | — |
| GET | `/api/v1/device-library/models/{model_id}/views` | app/api/v1/endpoints/devices.py:419 | — | — |
| POST | `/api/v1/device-library/busbar-calc` | app/api/v1/endpoints/devices.py:450 | — | — |
| GET | `/api/v1/device-library/user-items` | app/api/v1/endpoints/devices.py:523 | — | materializes_all_review |
| POST | `/api/v1/device-library/user-items` | app/api/v1/endpoints/devices.py:534 | — | — |
| DELETE | `/api/v1/device-library/user-items/{id}` | app/api/v1/endpoints/devices.py:554 | — | — |
| GET | `/api/v1/equipment-library/{equipment_id}/catalog-information` | app/api/v1/endpoints/equipment_library.py:19 | skip, limit | — |
| GET | `/api/v1/equipment-library/browser-data` | app/api/v1/endpoints/equipment_library.py:51 | skip, limit | — |
| GET | `/api/v1/equipment-library/projection-catalog` | app/api/v1/endpoints/equipment_library.py:61 | — | — |
| GET | `/api/v1/equipment-library/browse` | app/api/v1/endpoints/equipment_library.py:167 | skip, limit | — |
| GET | `/api/v1/equipment-library/{catalog_id}/drawing-source` | app/api/v1/endpoints/equipment_library.py:269 | — | — |
| GET | `/api/v1/equipment-library/{catalog_id}/preview` | app/api/v1/endpoints/equipment_library.py:309 | — | — |
| GET | `/api/v1/equipment-library/{catalog_id}/dxf` | app/api/v1/endpoints/equipment_library.py:336 | — | — |
| GET | `/api/v1/equipment-library/{catalog_id}/dwg` | app/api/v1/endpoints/equipment_library.py:342 | — | — |
| GET | `/api/v1/equipment-library/{catalog_id}/views/{view_id}/preview` | app/api/v1/endpoints/equipment_library.py:348 | — | — |
| GET | `/api/v1/equipment-library/{catalog_id}/views/{view_id}/dxf` | app/api/v1/endpoints/equipment_library.py:354 | — | — |
| GET | `/api/v1/equipment-library/{catalog_id}/views/{view_id}/dwg` | app/api/v1/endpoints/equipment_library.py:362 | — | — |
| GET | `/api/v1/equipment-library/manifest` | app/api/v1/endpoints/equipment_library.py:370 | — | — |
| GET | `/api/v1/equipment-library/search` | app/api/v1/endpoints/equipment_library.py:378 | limit | — |
| GET | `/api/v1/equipment-library/{catalog_id}` | app/api/v1/endpoints/equipment_library.py:388 | — | — |
| POST | `/api/v1/export/match-quotation` | app/api/v1/endpoints/export.py:30 | — | — |
| POST | `/api/v1/export/excel` | app/api/v1/endpoints/export.py:68 | — | — |
| POST | `/api/v1/export/save-to-project` | app/api/v1/endpoints/export.py:141 | — | — |
| POST | `/api/v1/export/quotation` | app/api/v1/endpoints/export.py:198 | — | — |
| GET | `/api/v1/export/download/{filename}` | app/api/v1/endpoints/export.py:243 | — | — |
| GET | `/api/v1/notifications` | app/api/v1/endpoints/notifications.py:14 | limit | — |
| POST | `/api/v1/notifications/read-all` | app/api/v1/endpoints/notifications.py:23 | — | — |
| POST | `/api/v1/notifications/{notification_id}/read` | app/api/v1/endpoints/notifications.py:30 | — | — |
| POST | `/api/v1/payments/create` | app/api/v1/endpoints/payments.py:131 | — | — |
| GET | `/api/v1/payments/{payment_id}/status` | app/api/v1/endpoints/payments.py:248 | — | — |
| POST | `/api/v1/payments/sepay-webhook` | app/api/v1/endpoints/payments.py:287 | — | materializes_all_review |
| POST | `/api/v1/payments/{payment_id}/cancel` | app/api/v1/endpoints/payments.py:419 | — | — |
| GET | `/api/v1/payments/history` | app/api/v1/endpoints/payments.py:440 | — | — |
| POST | `/api/v1/payments/test-simulate-success/{payment_id}` | app/api/v1/endpoints/payments.py:474 | — | — |
| GET | `/api/v1/plans` | app/api/v1/endpoints/plans.py:55 | — | materializes_all_review |
| GET | `/api/v1/plans/{plan_id}` | app/api/v1/endpoints/plans.py:62 | — | — |
| POST | `/api/v1/plans/subscribe/{plan_id}` | app/api/v1/endpoints/plans.py:72 | — | — |
| GET | `/api/v1/plans/user/my-subscription` | app/api/v1/endpoints/plans.py:142 | — | — |
| GET | `/api/v1/projects` | app/api/v1/endpoints/projects.py:95 | skip, limit | — |
| GET | `/api/v1/projects/stats` | app/api/v1/endpoints/projects.py:140 | — | — |
| POST | `/api/v1/projects` | app/api/v1/endpoints/projects.py:167 | — | — |
| GET | `/api/v1/projects/{id}` | app/api/v1/endpoints/projects.py:220 | — | — |
| PUT | `/api/v1/projects/{id}` | app/api/v1/endpoints/projects.py:229 | — | — |
| DELETE | `/api/v1/projects/{id}` | app/api/v1/endpoints/projects.py:269 | — | — |
| POST | `/api/v1/projects/{id}/upload` | app/api/v1/endpoints/projects.py:286 | — | — |
| POST | `/api/v1/projects/{id}/cad/blank` | app/api/v1/endpoints/projects.py:360 | — | — |
| GET | `/api/v1/projects/{id}/files` | app/api/v1/endpoints/projects.py:432 | — | materializes_all_review |
| DELETE | `/api/v1/projects/{id}/files/{file_id}` | app/api/v1/endpoints/projects.py:448 | — | — |
| GET | `/api/v1/projects/{id}/files/{file_id}/download` | app/api/v1/endpoints/projects.py:484 | — | — |
| GET | `/api/v1/providers` | app/api/v1/endpoints/providers.py:47 | — | materializes_all_review |
| GET | `/api/v1/providers/priority-models` | app/api/v1/endpoints/providers.py:66 | — | materializes_all_review |
| GET | `/api/v1/providers/{provider_id}/models` | app/api/v1/endpoints/providers.py:93 | — | materializes_all_review |
| GET | `/api/v1/user-library/files` | app/api/v1/endpoints/user_library.py:29 | — | materializes_all_review |
| POST | `/api/v1/user-library/files` | app/api/v1/endpoints/user_library.py:40 | — | — |
| DELETE | `/api/v1/user-library/files/{file_id}` | app/api/v1/endpoints/user_library.py:69 | — | — |
| GET | `/api/v1/user-library/files/{file_id}` | app/api/v1/endpoints/user_library.py:96 | — | — |
| GET | `/api/v1/users/me` | app/api/v1/endpoints/users.py:40 | — | — |
| PUT | `/api/v1/users/me` | app/api/v1/endpoints/users.py:62 | — | — |
| GET | `/api/v1/users` | app/api/v1/endpoints/users.py:80 | skip, limit | — |
| GET | `/api/v1/users/{user_id}` | app/api/v1/endpoints/users.py:93 | — | — |
| PUT | `/api/v1/users/{user_id}` | app/api/v1/endpoints/users.py:107 | — | — |
| DELETE | `/api/v1/users/{user_id}` | app/api/v1/endpoints/users.py:132 | — | — |
| POST | `/api/v1/analyze/device-details` | app/api/v1/endpoints/workspace_library.py:39 | — | — |
| POST | `/api/v1/analyze/device-recommendations` | app/api/v1/endpoints/workspace_library.py:87 | — | — |
| POST | `/api/v1/analyze/manufacturer-information` | app/api/v1/endpoints/workspace_library.py:104 | — | — |
| GET | `/api/v1/analyze/cad-candidates` | app/api/v1/endpoints/workspace_library.py:136 | — | — |
| GET | `/api/v1/analyze/cabinet-templates/{template_id}/preview-cad` | app/api/v1/endpoints/workspace_library.py:155 | — | — |
| GET | `/api/v1/library-access` | app/api/v1/api_router.py:14 | — | — |
