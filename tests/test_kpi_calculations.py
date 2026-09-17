from ingestion.fetch_sec_adv import planned_target_table
from ingestion.generate_synthetic import planned_table_prefix


def test_data_boundaries_are_named():
    assert planned_target_table() == "RAW.SEC_ADV_FIRMS"
    assert planned_table_prefix() == "RAW.SYNTHETIC_"
