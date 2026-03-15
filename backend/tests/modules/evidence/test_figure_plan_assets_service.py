from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.modules.evidence import service


@pytest.mark.asyncio
async def test_list_figure_plan_assets_uses_joined_rows_without_n_plus_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding = SimpleNamespace(
        id="binding-1",
        figure_plan_id="plan-1",
        asset_id="asset-1",
        role="source_image",
        position=0,
        created_at=datetime.now(UTC),
    )
    asset = SimpleNamespace(
        id="asset-1",
        file_name="asset.png",
        mime_type="image/png",
        storage_key="uploads/asset.png",
    )

    async def fake_get_figure_plan(_session, plan_id: str):
        return SimpleNamespace(id=plan_id)

    async def fake_list_figure_plan_assets_with_details(_session, plan_id: str):
        assert plan_id == "plan-1"
        return [(binding, asset)]

    async def fail_list_figure_plan_assets(*_args, **_kwargs):
        pytest.fail("list_figure_plan_assets_service 应使用 join 查询而不是先查 binding")

    async def fail_get_asset(*_args, **_kwargs):
        pytest.fail("list_figure_plan_assets_service 不应对每个 binding 单独查询 asset")

    monkeypatch.setattr(service.repository, "get_figure_plan", fake_get_figure_plan)
    monkeypatch.setattr(
        service.repository,
        "list_figure_plan_assets_with_details",
        fake_list_figure_plan_assets_with_details,
        raising=False,
    )
    monkeypatch.setattr(service.repository, "list_figure_plan_assets", fail_list_figure_plan_assets)
    monkeypatch.setattr(service.repository, "get_asset", fail_get_asset)
    monkeypatch.setattr(service, "generate_presigned_url", lambda storage_key: f"https://example.test/{storage_key}")

    results = await service.list_figure_plan_assets(object(), "plan-1")

    assert len(results) == 1
    assert results[0].id == "binding-1"
    assert results[0].asset_id == "asset-1"
    assert results[0].file_name == "asset.png"
    assert results[0].preview_url == "https://example.test/uploads/asset.png"
