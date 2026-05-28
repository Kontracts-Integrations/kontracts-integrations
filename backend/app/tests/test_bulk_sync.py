import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sync_run import SyncRun, RecordStatus, RunStatus
from app.models.mapping import MappingTemplate, MappingVersion
from app.sync_service.service import SyncService

@pytest.mark.asyncio
async def test_bulk_sync_path_execution():
    # 1. Setup mock database session and runs
    db_mock = MagicMock(spec=AsyncSession)
    
    # Mock database results
    template = MappingTemplate(
        id=1,
        name="Bulk Payments",
        source_module="triCostItem",
        source_object="triPaymentLineItem",
        kontracts_endpoint="/api/v1/payments/bulk",
        kontracts_method="POST",
        fetch_associated=False,
    )
    
    version = MappingVersion(
        id=1,
        template_id=1,
        version_number=1,
        is_current=True,
        field_mappings={"mappings": [
            {"source_field": "triNameTX", "target_field": "description", "transform_type": "direct"},
            {"source_field": "triAmountNU", "target_field": "amount", "transform_type": "direct"},
            {"source_field": "triDueDateDA", "target_field": "due_date", "transform_type": "direct"}
        ]}
    )
    
    run = SyncRun(
        id=999,
        mapping_template_id=1,
        status=RunStatus.running,
        total_records=0,
        success_count=0,
        failed_count=0,
        skipped_count=0
    )
    
    # Mock DB executions
    db_mock.execute = AsyncMock()
    # Mocking preloaded lease_mappings (empty)
    mock_lease_rows = MagicMock()
    mock_lease_rows.fetchall.return_value = []
    db_mock.execute.return_value = mock_lease_rows
    
    # 2. Build SyncService
    service = SyncService(db_mock)
    
    # Mock internal load mapping
    service._load_mapping = AsyncMock(return_value=(template, version))
    
    # Mock clients
    tririga_client_mock = MagicMock()
    kontracts_client_mock = MagicMock()
    
    service._build_tririga_client = AsyncMock(return_value=tririga_client_mock)
    service._build_kontracts_client = AsyncMock(return_value=kontracts_client_mock)
    
    # Mock TRIRIGA data fetch - returns 3 payments
    tririga_client_mock.run_dynamic_query = AsyncMock(return_value=[
        {"triRecordId": "101", "triNameTX": "Rent Payment A", "triAmountNU": "1500", "triDueDateDA": "2026-05-28"},
        {"triRecordId": "102", "triNameTX": "Rent Payment B", "triAmountNU": "1600", "triDueDateDA": "2026-05-28"},
        {"triRecordId": "103", "triNameTX": "Rent Payment C", "triAmountNU": "1700", "triDueDateDA": "2026-05-28"},
    ])
    
    # Mock Kontracts push_bulk response
    kontracts_client_mock.push_bulk = AsyncMock(return_value={
        "created_count": 3,
        "payments": [
            {"id": "pay_101", "lease_id": "300", "description": "Rent Payment A", "amount": 1500},
            {"id": "pay_102", "lease_id": "300", "description": "Rent Payment B", "amount": 1600},
            {"id": "pay_103", "lease_id": "300", "description": "Rent Payment C", "amount": 1700},
        ],
        "failed_count": 0,
        "errors": []
    })
    
    # Mock save_record and log to prevent DB writes
    service._save_record = AsyncMock()
    service._log = AsyncMock()
    
    # 3. Execute the sync run!
    await service._run_sync(run)
    
    # 4. Assertions
    # Verify TRIRIGA query was made
    tririga_client_mock.run_dynamic_query.assert_called_once()
    
    # Verify push_bulk was called EXACTLY ONCE with the array of 3 payloads
    kontracts_client_mock.push_bulk.assert_called_once()
    args, kwargs = kontracts_client_mock.push_bulk.call_args
    assert kwargs["endpoint"] == "/api/v1/payments/bulk"
    assert kwargs["method"] == "POST"
    assert len(kwargs["payloads"]) == 3
    assert kwargs["payloads"][0]["description"] == "Rent Payment A"
    assert kwargs["payloads"][1]["description"] == "Rent Payment B"
    assert kwargs["payloads"][2]["description"] == "Rent Payment C"
    
    # Verify run statistics
    assert run.success_count == 3
    assert run.failed_count == 0
    assert run.skipped_count == 0
    
    # Verify save_record was called for each record
    assert service._save_record.call_count == 3


@pytest.mark.asyncio
async def test_bulk_sync_chunked_execution():
    # Setup mock database session and runs
    db_mock = MagicMock(spec=AsyncSession)
    
    template = MappingTemplate(
        id=1,
        name="Bulk Payments Chunked",
        source_module="triCostItem",
        source_object="triPaymentLineItem",
        kontracts_endpoint="/api/v1/payments/bulk",
        kontracts_method="POST",
        fetch_associated=False,
    )
    
    version = MappingVersion(
        id=1,
        template_id=1,
        version_number=1,
        is_current=True,
        field_mappings={"mappings": [
            {"source_field": "triNameTX", "target_field": "description", "transform_type": "direct"},
            {"source_field": "triAmountNU", "target_field": "amount", "transform_type": "direct"},
            {"source_field": "triDueDateDA", "target_field": "due_date", "transform_type": "direct"}
        ]}
    )
    
    run = SyncRun(
        id=999,
        mapping_template_id=1,
        status=RunStatus.running,
        total_records=0,
        success_count=0,
        failed_count=0,
        skipped_count=0
    )
    
    db_mock.execute = AsyncMock()
    mock_lease_rows = MagicMock()
    mock_lease_rows.fetchall.return_value = []
    db_mock.execute.return_value = mock_lease_rows
    
    service = SyncService(db_mock)
    service._load_mapping = AsyncMock(return_value=(template, version))
    
    tririga_client_mock = MagicMock()
    kontracts_client_mock = MagicMock()
    
    service._build_tririga_client = AsyncMock(return_value=tririga_client_mock)
    service._build_kontracts_client = AsyncMock(return_value=kontracts_client_mock)
    
    # 2050 records to trigger 3 chunks (1000, 1000, 50)
    records = []
    for idx in range(2050):
        records.append({
            "triRecordId": str(1000 + idx),
            "triNameTX": f"Rent Payment {idx}",
            "triAmountNU": "100",
            "triDueDateDA": "2026-05-28"
        })
    tririga_client_mock.run_dynamic_query = AsyncMock(return_value=records)
    
    async def push_bulk_side_effect(endpoint, method, payloads):
        chunk_payments = [{"id": f"pay_{p['description'].split()[-1]}", "lease_id": "300", "description": p["description"], "amount": 100} for p in payloads]
        return {
            "created_count": len(payloads),
            "payments": chunk_payments,
            "failed_count": 0,
            "errors": []
        }
    
    kontracts_client_mock.push_bulk = AsyncMock(side_effect=push_bulk_side_effect)
    
    service._save_record = AsyncMock()
    service._log = AsyncMock()
    
    await service._run_sync(run)
    
    # Verify push_bulk was called exactly 3 times
    assert kontracts_client_mock.push_bulk.call_count == 3
    
    # First chunk (1000 records)
    first_call_args = kontracts_client_mock.push_bulk.call_args_list[0]
    assert len(first_call_args.kwargs["payloads"]) == 1000
    
    # Second chunk (1000 records)
    second_call_args = kontracts_client_mock.push_bulk.call_args_list[1]
    assert len(second_call_args.kwargs["payloads"]) == 1000
    
    # Third chunk (50 records)
    third_call_args = kontracts_client_mock.push_bulk.call_args_list[2]
    assert len(third_call_args.kwargs["payloads"]) == 50
    
    # Verify run statistics
    assert run.success_count == 2050
    assert run.failed_count == 0
    assert run.skipped_count == 0
    
    # Verify save_record was called for each record
    assert service._save_record.call_count == 2050

