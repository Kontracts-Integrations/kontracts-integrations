"""
Demo/fixture data for TRIRIGA client when DEMO_MODE=true.
"""
from typing import Any, Dict, List

DEMO_MODULES = [
    {"name": "triRealEstateLease", "label": "Real Estate Lease", "category": "Real Estate"},
    {"name": "triBuilding", "label": "Building", "category": "Real Estate"},
    {"name": "triFloor", "label": "Floor", "category": "Real Estate"},
    {"name": "triSpace", "label": "Space", "category": "Real Estate"},
    {"name": "triPeople", "label": "People", "category": "HR"},
    {"name": "triWorkTask", "label": "Work Task", "category": "Facilities"},
    {"name": "triWorkOrder", "label": "Work Order", "category": "Facilities"},
    {"name": "triContract", "label": "Contract", "category": "Contracts"},
    {"name": "triAsset", "label": "Asset", "category": "Assets"},
    {"name": "triLocation", "label": "Location", "category": "Real Estate"},
]

DEMO_FIELDS_BY_MODULE: Dict[str, List[Dict[str, Any]]] = {
    "triRealEstateLease": [
        {"name": "triRecordIdSY", "label": "Record ID", "type": "number", "required": True},
        {"name": "triNameTX", "label": "Lease Name", "type": "string", "required": True},
        {"name": "triLeaseTypeCL", "label": "Lease Type", "type": "string", "required": False},
        {"name": "triCommenceDateDT", "label": "Commencement Date", "type": "date", "required": True},
        {"name": "triExpirationDateDT", "label": "Expiration Date", "type": "date", "required": True},
        {"name": "triLeasedAreaNU", "label": "Leased Area (SF)", "type": "number", "required": False},
        {"name": "triBaseRentAmountNU", "label": "Base Rent Amount", "type": "currency", "required": False},
        {"name": "triRentFrequencyCL", "label": "Rent Frequency", "type": "string", "required": False},
        {"name": "triCurrencyCL", "label": "Currency", "type": "string", "required": False},
        {"name": "triDiscountRateNU", "label": "Discount Rate (%)", "type": "number", "required": False},
        {"name": "triLandlordTX", "label": "Landlord Name", "type": "string", "required": False},
        {"name": "triTenantTX", "label": "Tenant Name", "type": "string", "required": False},
        {"name": "triStatusCL", "label": "Status", "type": "string", "required": False},
        {"name": "triAddressTX", "label": "Property Address", "type": "string", "required": False},
        {"name": "triCityTX", "label": "City", "type": "string", "required": False},
        {"name": "triStateProvinceListTX", "label": "State/Province", "type": "string", "required": False},
        {"name": "triCountryCL", "label": "Country", "type": "string", "required": False},
        {"name": "triPostalCodeTX", "label": "Postal Code", "type": "string", "required": False},
        {"name": "triRenewalOptionsBL", "label": "Has Renewal Options", "type": "boolean", "required": False},
        {"name": "triRenewalTermNU", "label": "Renewal Term (months)", "type": "number", "required": False},
        {"name": "triPurchaseOptionBL", "label": "Has Purchase Option", "type": "boolean", "required": False},
        {"name": "triSubleaseOptionBL", "label": "Has Sublease Option", "type": "boolean", "required": False},
        {"name": "triCreatedByTX", "label": "Created By", "type": "string", "required": False},
        {"name": "triCreatedDateDT", "label": "Created Date", "type": "datetime", "required": False},
        {"name": "triModifiedDateDT", "label": "Modified Date", "type": "datetime", "required": False},
    ],
    "triBuilding": [
        {"name": "triRecordIdSY", "label": "Record ID", "type": "number", "required": True},
        {"name": "triNameTX", "label": "Building Name", "type": "string", "required": True},
        {"name": "triAddressTX", "label": "Address", "type": "string", "required": False},
        {"name": "triGrossAreaNU", "label": "Gross Area (SF)", "type": "number", "required": False},
        {"name": "triYearBuiltNU", "label": "Year Built", "type": "number", "required": False},
    ],
}

DEMO_RECORDS = [
    {
        "triRecordIdSY": 100001,
        "triNameTX": "HQ Office Lease - New York",
        "triLeaseTypeCL": "Operating",
        "triCommenceDateDT": "2020-01-01",
        "triExpirationDateDT": "2025-12-31",
        "triLeasedAreaNU": 25000.0,
        "triBaseRentAmountNU": 75000.00,
        "triRentFrequencyCL": "Monthly",
        "triCurrencyCL": "USD",
        "triDiscountRateNU": 3.5,
        "triLandlordTX": "Empire State Properties LLC",
        "triTenantTX": "Verizon Communications Inc",
        "triStatusCL": "Active",
        "triAddressTX": "350 Fifth Avenue",
        "triCityTX": "New York",
        "triStateProvinceListTX": "NY",
        "triCountryCL": "United States",
        "triPostalCodeTX": "10118",
        "triRenewalOptionsBL": True,
        "triRenewalTermNU": 60,
        "triPurchaseOptionBL": False,
        "triSubleaseOptionBL": True,
        "triCreatedByTX": "admin@verizon.com",
        "triCreatedDateDT": "2020-01-15T09:00:00Z",
        "triModifiedDateDT": "2023-06-01T14:30:00Z",
    },
    {
        "triRecordIdSY": 100002,
        "triNameTX": "Chicago Data Center Lease",
        "triLeaseTypeCL": "Finance",
        "triCommenceDateDT": "2019-07-01",
        "triExpirationDateDT": "2029-06-30",
        "triLeasedAreaNU": 15000.0,
        "triBaseRentAmountNU": 45000.00,
        "triRentFrequencyCL": "Monthly",
        "triCurrencyCL": "USD",
        "triDiscountRateNU": 4.2,
        "triLandlordTX": "Midwest Commercial Realty",
        "triTenantTX": "Verizon Communications Inc",
        "triStatusCL": "Active",
        "triAddressTX": "200 S Wacker Drive",
        "triCityTX": "Chicago",
        "triStateProvinceListTX": "IL",
        "triCountryCL": "United States",
        "triPostalCodeTX": "60606",
        "triRenewalOptionsBL": True,
        "triRenewalTermNU": 36,
        "triPurchaseOptionBL": True,
        "triSubleaseOptionBL": False,
        "triCreatedByTX": "admin@verizon.com",
        "triCreatedDateDT": "2019-07-10T08:00:00Z",
        "triModifiedDateDT": "2023-07-01T10:00:00Z",
    },
    {
        "triRecordIdSY": 100003,
        "triNameTX": "San Francisco Branch Office",
        "triLeaseTypeCL": "Operating",
        "triCommenceDateDT": "2021-03-01",
        "triExpirationDateDT": "2026-02-28",
        "triLeasedAreaNU": 8500.0,
        "triBaseRentAmountNU": 42500.00,
        "triRentFrequencyCL": "Monthly",
        "triCurrencyCL": "USD",
        "triDiscountRateNU": 3.25,
        "triLandlordTX": "Bay Area Commercial LLC",
        "triTenantTX": "Verizon Communications Inc",
        "triStatusCL": "Active",
        "triAddressTX": "101 California Street",
        "triCityTX": "San Francisco",
        "triStateProvinceListTX": "CA",
        "triCountryCL": "United States",
        "triPostalCodeTX": "94111",
        "triRenewalOptionsBL": False,
        "triRenewalTermNU": 0,
        "triPurchaseOptionBL": False,
        "triSubleaseOptionBL": False,
        "triCreatedByTX": "admin@verizon.com",
        "triCreatedDateDT": "2021-03-05T09:30:00Z",
        "triModifiedDateDT": "2022-12-01T11:00:00Z",
    },
]

DEMO_RECORD = DEMO_RECORDS[0]

DEMO_WSDL_STRUCTURE = {
    "services": [
        {
            "name": "TririgaWS",
            "ports": [
                {
                    "name": "TririgaWSPort",
                    "operations": [
                        {"name": "runNamedQuery"},
                        {"name": "saveRecord"},
                        {"name": "getModules"},
                    ],
                }
            ],
        }
    ]
}


def get_demo_fields(module_name: str):
    return DEMO_FIELDS_BY_MODULE.get(
        module_name,
        DEMO_FIELDS_BY_MODULE.get("triRealEstateLease", []),
    )


def get_demo_records(module_name: str, query_name: str, max_records: int):
    return DEMO_RECORDS[:max_records]
