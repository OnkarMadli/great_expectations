import logging
from typing import List, Union

import pandas as pd
import pytest

from great_expectations.checkpoint.types.checkpoint_result import CheckpointResult
from great_expectations.core import (
    ExpectationConfiguration,
    ExpectationSuiteValidationResult,
)
from great_expectations.core.yaml_handler import YAMLHandler
from great_expectations.data_context.data_context.data_context import DataContext
from great_expectations.data_context.types.base import CheckpointConfig
from great_expectations.exceptions import CheckpointError
from great_expectations.util import filter_properties_dict

yaml = YAMLHandler()

logger = logging.getLogger(__name__)


@pytest.fixture()
def reference_checkpoint_config_for_unexpected_column_names() -> dict:
    """
    This is a reference checkpoint dict. It connects to Datasource defined in
    data_context_with_connection_to_animal_names_db fixture
    """
    checkpoint_dict: dict = {
        "name": "my_checkpoint",
        "config_version": 1.0,
        "class_name": "Checkpoint",
        "module_name": "great_expectations.checkpoint",
        "template_name": None,
        "run_name_template": "%Y-%M-foo-bar-template-test",
        "expectation_suite_name": None,
        "batch_request": None,
        "action_list": [],
        "profilers": [],
        "action_list": [
            {
                "name": "store_validation_result",
                "action": {"class_name": "StoreValidationResultAction"},
            },
            {
                "name": "store_evaluation_params",
                "action": {"class_name": "StoreEvaluationParametersAction"},
            },
            {
                "name": "update_data_docs",
                "action": {"class_name": "UpdateDataDocsAction"},
            },
        ],
        "validations": [],
        "runtime_configuration": {},
    }
    return checkpoint_dict


@pytest.fixture()
def reference_sql_checkpoint_config_for_unexpected_column_names(
    reference_checkpoint_config_for_unexpected_column_names,
) -> dict:
    """
    This is a reference checkpoint dict. It connects to Datasource defined in
    data_context_with_connection_to_animal_names_db fixture
    """
    reference_checkpoint_config_for_unexpected_column_names["validations"] = [
        {
            "batch_request": {
                "datasource_name": "my_datasource",
                "data_connector_name": "my_sql_data_connector",
                "data_asset_name": "my_asset",
            },
            "expectation_suite_name": "animal_names_exp",
        }
    ]
    return reference_checkpoint_config_for_unexpected_column_names


@pytest.fixture()
def expectation_config_expect_column_values_to_be_in_set() -> ExpectationConfiguration:
    return ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={
            "column": "animals",
            "value_set": ["cat", "fish", "dog"],
        },
    )


@pytest.fixture()
def expectation_config_expect_column_values_to_not_be_in_set() -> ExpectationConfiguration:
    return ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_in_set",
        kwargs={
            "column": "animals",
            "value_set": ["giraffe", "lion", "zebra"],
        },
    )


@pytest.fixture()
def batch_request_for_pandas_unexpected_rows_and_index(
    pandas_animals_dataframe_for_unexpected_rows_and_index,
) -> dict:
    dataframe: pd.DataFrame = pandas_animals_dataframe_for_unexpected_rows_and_index
    return {
        "datasource_name": "pandas_datasource",
        "data_connector_name": "runtime_data_connector",
        "data_asset_name": "IN_MEMORY_DATA_ASSET",
        "runtime_parameters": {
            "batch_data": dataframe,
        },
        "batch_identifiers": {
            "id_key_0": 1234567890,
        },
    }


def _add_expectations_and_checkpoint(
    data_context: DataContext,
    checkpoint_config: dict,
    expectations_list: List[ExpectationConfiguration],
    dict_to_update_checkpoint: Union[dict, None] = None,
) -> DataContext:
    """
    Helper method for adding Checkpoint and Expectations to DataContext.

    Args:
        data_context (DataContext): data_context_with_connection_to_animal_names_db
        checkpoint_config : Checkpoint to add
        expectations_list : Expectations to add

    Returns:
        DataContext with updated config
    """
    if dict_to_update_checkpoint:
        checkpoint_config["runtime_configuration"] = dict_to_update_checkpoint

    context: DataContext = data_context
    context.create_expectation_suite(expectation_suite_name="animal_names_exp")
    animals_suite = context.get_expectation_suite(
        expectation_suite_name="animal_names_exp"
    )
    for expectation in expectations_list:
        animals_suite.add_expectation(expectation_configuration=expectation)
    context.save_expectation_suite(
        expectation_suite=animals_suite,
        expectation_suite_name="animal_names_exp",
        overwriting_existing=True,
    )
    checkpoint_config = CheckpointConfig(**checkpoint_config)
    context.add_checkpoint(
        **filter_properties_dict(
            properties=checkpoint_config.to_json_dict(),
            clean_falsy=True,
        ),
    )
    # noinspection PyProtectedMember
    context._save_project_config()
    return context


@pytest.mark.integration
def test_sql_result_format_in_checkpoint_pk_defined_one_expectation_complete_output(
    data_context_with_connection_to_animal_names_db,
    reference_sql_checkpoint_config_for_unexpected_column_names,
    expectation_config_expect_column_values_to_be_in_set,
):
    """
    What does this test?
        - unexpected_index_column defined in Checkpoint only.
        - COMPLETE output, which means we have `unexpected_index_list` and `partial_unexpected_index_list`
        - 1 Expectations added to suite
    """

    dict_to_update_checkpoint: dict = {
        "result_format": {
            "result_format": "COMPLETE",
            "unexpected_index_column_names": ["pk_1"],
        }
    }

    context: DataContext = _add_expectations_and_checkpoint(
        data_context=data_context_with_connection_to_animal_names_db,
        checkpoint_config=reference_sql_checkpoint_config_for_unexpected_column_names,
        expectations_list=[expectation_config_expect_column_values_to_be_in_set],
        dict_to_update_checkpoint=dict_to_update_checkpoint,
    )

    result: CheckpointResult = context.run_checkpoint(
        checkpoint_name="my_checkpoint",
    )
    evrs: List[ExpectationSuiteValidationResult] = result.list_validation_results()
    first_result_full_list = evrs[0]["results"][0]["result"]["unexpected_index_list"]
    assert first_result_full_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]
    first_result_partial_list = evrs[0]["results"][0]["result"][
        "partial_unexpected_index_list"
    ]
    assert first_result_partial_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]


@pytest.mark.integration
def test_sql_result_format_not_in_checkpoint_passed_into_run_checkpoint_one_expectation_complete_output(
    data_context_with_connection_to_animal_names_db,
    reference_sql_checkpoint_config_for_unexpected_column_names,
    expectation_config_expect_column_values_to_be_in_set,
):
    """
    What does this test?
        - unexpected_index_column not defined in Checkpoint config, but passed in at run_checkpoint.
        - COMPLETE output, which means we have `unexpected_index_list` and `partial_unexpected_index_list`
        - 1 Expectations added to suite
    """
    # intentionally empty, since we are updating at run_checkpoint()
    dict_to_update_checkpoint: dict = {}
    context: DataContext = _add_expectations_and_checkpoint(
        data_context=data_context_with_connection_to_animal_names_db,
        checkpoint_config=reference_sql_checkpoint_config_for_unexpected_column_names,
        expectations_list=[expectation_config_expect_column_values_to_be_in_set],
        dict_to_update_checkpoint=dict_to_update_checkpoint,
    )
    result_format: dict = {
        "result_format": "COMPLETE",
        "unexpected_index_column_names": ["pk_1"],
    }
    result: CheckpointResult = context.run_checkpoint(
        checkpoint_name="my_checkpoint", result_format=result_format
    )
    evrs: List[ExpectationSuiteValidationResult] = result.list_validation_results()
    first_result_full_list = evrs[0]["results"][0]["result"]["unexpected_index_list"]
    assert first_result_full_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]
    first_result_partial_list = evrs[0]["results"][0]["result"][
        "partial_unexpected_index_list"
    ]
    assert first_result_partial_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]


@pytest.mark.integration
def test_sql_result_format_not_in_checkpoint_passed_into_run_checkpoint_one_expectation_complete_output_limit_1(
    data_context_with_connection_to_animal_names_db,
    reference_sql_checkpoint_config_for_unexpected_column_names,
    expectation_config_expect_column_values_to_be_in_set,
):
    """
    What does this test?
        - unexpected_index_column not defined in Checkpoint config, but passed in at run_checkpoint.
        - COMPLETE output, which means we have `unexpected_index_list` and `partial_unexpected_index_list`
        - 1 Expectations added to suite
    """
    context: DataContext = _add_expectations_and_checkpoint(
        data_context=data_context_with_connection_to_animal_names_db,
        checkpoint_config=reference_sql_checkpoint_config_for_unexpected_column_names,
        expectations_list=[expectation_config_expect_column_values_to_be_in_set],
    )
    result_format: dict = {
        "result_format": "SUMMARY",
        "partial_unexpected_count": 1,
        "unexpected_index_column_names": ["pk_1"],
    }
    result: CheckpointResult = context.run_checkpoint(
        checkpoint_name="my_checkpoint", result_format=result_format
    )
    evrs: List[ExpectationSuiteValidationResult] = result.list_validation_results()
    first_result_partial_list = evrs[0]["results"][0]["result"][
        "partial_unexpected_index_list"
    ]
    assert first_result_partial_list == [{"pk_1": 3}]


@pytest.mark.integration
def test_sql_result_format_not_in_checkpoint_passed_into_run_checkpoint_one_expectation_complete_output_incorrect_column(
    data_context_with_connection_to_animal_names_db,
    reference_sql_checkpoint_config_for_unexpected_column_names,
    expectation_config_expect_column_values_to_be_in_set,
):
    """
    What does this test?
        - unexpected_index_column not defined in Checkpoint config, but passed in at run_checkpoint.
        - unexpected_index_column is passed in an incorrect column
    """
    context: DataContext = _add_expectations_and_checkpoint(
        data_context=data_context_with_connection_to_animal_names_db,
        checkpoint_config=reference_sql_checkpoint_config_for_unexpected_column_names,
        expectations_list=[expectation_config_expect_column_values_to_be_in_set],
    )

    result_format: dict = {
        "result_format": "COMPLETE",
        "unexpected_index_column_names": ["i_dont_exist"],
    }
    with pytest.raises(CheckpointError) as e:
        result: CheckpointResult = context.run_checkpoint(
            checkpoint_name="my_checkpoint",
            result_format=result_format,
            runtime_configuration={"catch_exceptions": False},
        )

    assert e.value.message == (
        "Exception occurred while running validation[0] of Checkpoint "
        "'my_checkpoint': Error: The unexpected_index_column: \"i_dont_exist\" in "
        "does not exist in SQL Table. Please check your configuration and try again.."
    )


@pytest.mark.integration
def test_sql_result_format_in_checkpoint_pk_defined_two_expectation_complete_output(
    data_context_with_connection_to_animal_names_db,
    reference_sql_checkpoint_config_for_unexpected_column_names,
    expectation_config_expect_column_values_to_be_in_set,
    expectation_config_expect_column_values_to_not_be_in_set,
):
    """
    What does this test?
        - unexpected_index_column not defined in Checkpoint config, but passed in at run_checkpoint.
        - COMPLETE output, which means we have `unexpected_index_list` and `partial_unexpected_index_list`
        - 2 Expectations added to suite
    """
    context: DataContext = _add_expectations_and_checkpoint(
        data_context=data_context_with_connection_to_animal_names_db,
        checkpoint_config=reference_sql_checkpoint_config_for_unexpected_column_names,
        expectations_list=[
            expectation_config_expect_column_values_to_be_in_set,
            expectation_config_expect_column_values_to_not_be_in_set,
        ],
    )
    result_format: dict = {
        "result_format": "COMPLETE",
        "unexpected_index_column_names": ["pk_1"],
    }

    result: CheckpointResult = context.run_checkpoint(
        checkpoint_name="my_checkpoint", result_format=result_format
    )
    evrs: List[ExpectationSuiteValidationResult] = result.list_validation_results()

    # first and second expectations have same results. Although one is "expect_to_be"
    # and the other is "expect_to_not_be", they have opposite value_sets
    first_result_full_list = evrs[0]["results"][0]["result"]["unexpected_index_list"]
    assert first_result_full_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]
    first_result_partial_list = evrs[0]["results"][0]["result"][
        "partial_unexpected_index_list"
    ]
    assert first_result_partial_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]

    second_result_full_list = evrs[0]["results"][1]["result"]["unexpected_index_list"]
    assert second_result_full_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]
    second_result_partial_list = evrs[0]["results"][1]["result"][
        "partial_unexpected_index_list"
    ]
    assert second_result_partial_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]


@pytest.mark.integration
def test_sql_result_format_in_checkpoint_pk_defined_one_expectation_summary_output(
    data_context_with_connection_to_animal_names_db,
    reference_sql_checkpoint_config_for_unexpected_column_names,
    expectation_config_expect_column_values_to_be_in_set,
):
    """
    What does this test?
        - unexpected_index_column defined in Checkpoint only.
        - SUMMARY output, which means we have `partial_unexpected_index_list` only
        - 1 Expectations added to suite
    """
    dict_to_update_checkpoint: dict = {
        "result_format": {
            "result_format": "SUMMARY",
            "unexpected_index_column_names": ["pk_1"],
        }
    }
    context: DataContext = _add_expectations_and_checkpoint(
        data_context=data_context_with_connection_to_animal_names_db,
        checkpoint_config=reference_sql_checkpoint_config_for_unexpected_column_names,
        expectations_list=[expectation_config_expect_column_values_to_be_in_set],
        dict_to_update_checkpoint=dict_to_update_checkpoint,
    )

    result: CheckpointResult = context.run_checkpoint(
        checkpoint_name="my_checkpoint",
    )
    evrs: List[ExpectationSuiteValidationResult] = result.list_validation_results()
    first_result_full_list = evrs[0]["results"][0]["result"].get(
        "unexpected_index_list"
    )
    assert not first_result_full_list
    first_result_partial_list = evrs[0]["results"][0]["result"][
        "partial_unexpected_index_list"
    ]
    assert first_result_partial_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]


@pytest.mark.integration
def test_sql_result_format_in_checkpoint_pk_defined_one_expectation_basic_output(
    data_context_with_connection_to_animal_names_db,
    reference_sql_checkpoint_config_for_unexpected_column_names,
    expectation_config_expect_column_values_to_be_in_set,
):
    """
    What does this test?
        - unexpected_index_column defined in Checkpoint only.
        - BASIC output, which means we have no unexpected_index_list output
        - 1 Expectations added to suite
    """
    dict_to_update_checkpoint: dict = {
        "result_format": {
            "result_format": "BASIC",
            "unexpected_index_column_names": ["pk_1"],
        }
    }
    context: DataContext = _add_expectations_and_checkpoint(
        data_context=data_context_with_connection_to_animal_names_db,
        checkpoint_config=reference_sql_checkpoint_config_for_unexpected_column_names,
        expectations_list=[expectation_config_expect_column_values_to_be_in_set],
        dict_to_update_checkpoint=dict_to_update_checkpoint,
    )

    result: CheckpointResult = context.run_checkpoint(
        checkpoint_name="my_checkpoint",
    )
    evrs: List[ExpectationSuiteValidationResult] = result.list_validation_results()
    first_result_full_list = evrs[0]["results"][0]["result"].get(
        "unexpected_index_list"
    )
    assert not first_result_full_list
    first_result_partial_list = evrs[0]["results"][0]["result"].get(
        "partial_unexpected_index_list"
    )
    assert not first_result_partial_list


# pandas
@pytest.mark.integration
def test_pandas_result_format_in_checkpoint_pk_defined_one_expectation_complete_output(
    in_memory_runtime_context,
    batch_request_for_pandas_unexpected_rows_and_index,
    reference_checkpoint_config_for_unexpected_column_names,
    expectation_config_expect_column_values_to_be_in_set,
):
    """ """
    dict_to_update_checkpoint: dict = {
        "result_format": {
            "result_format": "COMPLETE",
            "unexpected_index_column_names": ["pk_1"],
        }
    }
    context: DataContext = _add_expectations_and_checkpoint(
        data_context=in_memory_runtime_context,
        checkpoint_config=reference_checkpoint_config_for_unexpected_column_names,
        expectations_list=[expectation_config_expect_column_values_to_be_in_set],
        dict_to_update_checkpoint=dict_to_update_checkpoint,
    )

    result: CheckpointResult = context.run_checkpoint(
        checkpoint_name="my_checkpoint",
        expectation_suite_name="animal_names_exp",
        batch_request=batch_request_for_pandas_unexpected_rows_and_index,
    )
    evrs: List[ExpectationSuiteValidationResult] = result.list_validation_results()
    first_result_full_list = evrs[0]["results"][0]["result"]["unexpected_index_list"]
    assert first_result_full_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]
    first_result_partial_list = evrs[0]["results"][0]["result"][
        "partial_unexpected_index_list"
    ]
    assert first_result_partial_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]


@pytest.mark.integration
def test_pandas_result_format_not_in_checkpoint_passed_into_run_checkpoint_one_expectation_complete_output(
    in_memory_runtime_context,
    batch_request_for_pandas_unexpected_rows_and_index,
    reference_checkpoint_config_for_unexpected_column_names,
    expectation_config_expect_column_values_to_be_in_set,
):
    context: DataContext = _add_expectations_and_checkpoint(
        data_context=in_memory_runtime_context,
        checkpoint_config=reference_checkpoint_config_for_unexpected_column_names,
        expectations_list=[expectation_config_expect_column_values_to_be_in_set],
    )
    result_format: dict = {
        "result_format": "COMPLETE",
        "unexpected_index_column_names": ["pk_1"],
    }
    result: CheckpointResult = context.run_checkpoint(
        checkpoint_name="my_checkpoint",
        expectation_suite_name="animal_names_exp",
        result_format=result_format,
        batch_request=batch_request_for_pandas_unexpected_rows_and_index,
    )
    evrs: List[ExpectationSuiteValidationResult] = result.list_validation_results()
    first_result_full_list = evrs[0]["results"][0]["result"]["unexpected_index_list"]
    assert first_result_full_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]
    first_result_partial_list = evrs[0]["results"][0]["result"][
        "partial_unexpected_index_list"
    ]
    assert first_result_partial_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]


@pytest.mark.integration
def test_pandas_result_format_not_in_checkpoint_passed_into_run_checkpoint_one_expectation_summary_output_limit_1(
    in_memory_runtime_context,
    batch_request_for_pandas_unexpected_rows_and_index,
    reference_checkpoint_config_for_unexpected_column_names,
    expectation_config_expect_column_values_to_be_in_set,
):
    context: DataContext = _add_expectations_and_checkpoint(
        data_context=in_memory_runtime_context,
        checkpoint_config=reference_checkpoint_config_for_unexpected_column_names,
        expectations_list=[expectation_config_expect_column_values_to_be_in_set],
    )
    result_format: dict = {
        "result_format": "SUMMARY",
        "partial_unexpected_count": 1,
        "unexpected_index_column_names": ["pk_1"],
    }
    result: CheckpointResult = context.run_checkpoint(
        checkpoint_name="my_checkpoint",
        expectation_suite_name="animal_names_exp",
        result_format=result_format,
        batch_request=batch_request_for_pandas_unexpected_rows_and_index,
    )
    evrs: List[ExpectationSuiteValidationResult] = result.list_validation_results()
    first_result_partial_list = evrs[0]["results"][0]["result"][
        "partial_unexpected_index_list"
    ]
    assert first_result_partial_list == [{"pk_1": 3}]


@pytest.mark.integration
def test_pandas_result_format_not_in_checkpoint_passed_into_run_checkpoint_one_expectation_complete_output_incorrect_column(
    in_memory_runtime_context,
    batch_request_for_pandas_unexpected_rows_and_index,
    reference_checkpoint_config_for_unexpected_column_names,
    expectation_config_expect_column_values_to_be_in_set,
):
    dict_to_update_checkpoint: dict = {
        "result_format": {
            "result_format": "COMPLETE",
            "unexpected_index_column_names": ["i_dont_exist"],
        }
    }
    context: DataContext = _add_expectations_and_checkpoint(
        data_context=in_memory_runtime_context,
        checkpoint_config=reference_checkpoint_config_for_unexpected_column_names,
        expectations_list=[expectation_config_expect_column_values_to_be_in_set],
        dict_to_update_checkpoint=dict_to_update_checkpoint,
    )
    with pytest.raises(CheckpointError) as e:
        result: CheckpointResult = context.run_checkpoint(
            checkpoint_name="my_checkpoint",
            expectation_suite_name="animal_names_exp",
            batch_request=batch_request_for_pandas_unexpected_rows_and_index,
            runtime_configuration={"catch_exceptions": False},
        )
    assert e.value.message == (
        "Exception occurred while running validation[0] of Checkpoint "
        "'my_checkpoint': Error: The unexpected_index_column \"i_dont_exist\" does "
        "not exist in Dataframe. Please check your configuration and try again.."
    )


@pytest.mark.integration
def test_pandas_result_format_in_checkpoint_pk_defined_two_expectation_complete_output(
    in_memory_runtime_context,
    batch_request_for_pandas_unexpected_rows_and_index,
    reference_checkpoint_config_for_unexpected_column_names,
    expectation_config_expect_column_values_to_be_in_set,
    expectation_config_expect_column_values_to_not_be_in_set,
):
    dict_to_update_checkpoint: dict = {
        "result_format": {
            "result_format": "COMPLETE",
            "unexpected_index_column_names": ["pk_1"],
        }
    }
    context: DataContext = _add_expectations_and_checkpoint(
        data_context=in_memory_runtime_context,
        checkpoint_config=reference_checkpoint_config_for_unexpected_column_names,
        expectations_list=[
            expectation_config_expect_column_values_to_be_in_set,
            expectation_config_expect_column_values_to_not_be_in_set,
        ],
        dict_to_update_checkpoint=dict_to_update_checkpoint,
    )

    result: CheckpointResult = context.run_checkpoint(
        checkpoint_name="my_checkpoint",
        expectation_suite_name="animal_names_exp",
        batch_request=batch_request_for_pandas_unexpected_rows_and_index,
    )
    evrs: List[ExpectationSuiteValidationResult] = result.list_validation_results()
    # first and second expectations have same results. Although one is "expect_to_be"
    # and the other is "expect_to_not_be", they have opposite value_sets
    first_result_full_list = evrs[0]["results"][0]["result"]["unexpected_index_list"]
    assert first_result_full_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]
    first_result_partial_list = evrs[0]["results"][0]["result"][
        "partial_unexpected_index_list"
    ]
    assert first_result_partial_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]

    second_result_full_list = evrs[0]["results"][1]["result"]["unexpected_index_list"]
    assert second_result_full_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]
    second_result_partial_list = evrs[0]["results"][1]["result"][
        "partial_unexpected_index_list"
    ]
    assert second_result_partial_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]


@pytest.mark.integration
def test_pandas_result_format_in_checkpoint_pk_defined_one_expectation_summary_output(
    in_memory_runtime_context,
    batch_request_for_pandas_unexpected_rows_and_index,
    reference_checkpoint_config_for_unexpected_column_names,
    expectation_config_expect_column_values_to_be_in_set,
):
    dict_to_update_checkpoint: dict = {
        "result_format": {
            "result_format": "SUMMARY",
            "unexpected_index_column_names": ["pk_1"],
        }
    }
    context: DataContext = _add_expectations_and_checkpoint(
        data_context=in_memory_runtime_context,
        checkpoint_config=reference_checkpoint_config_for_unexpected_column_names,
        expectations_list=[expectation_config_expect_column_values_to_be_in_set],
        dict_to_update_checkpoint=dict_to_update_checkpoint,
    )

    result: CheckpointResult = context.run_checkpoint(
        checkpoint_name="my_checkpoint",
        expectation_suite_name="animal_names_exp",
        batch_request=batch_request_for_pandas_unexpected_rows_and_index,
    )
    evrs: List[ExpectationSuiteValidationResult] = result.list_validation_results()
    first_result_full_list = evrs[0]["results"][0]["result"].get(
        "unexpected_index_list"
    )
    assert not first_result_full_list
    first_result_partial_list = evrs[0]["results"][0]["result"][
        "partial_unexpected_index_list"
    ]
    assert first_result_partial_list == [{"pk_1": 3}, {"pk_1": 4}, {"pk_1": 5}]


@pytest.mark.integration
def test_pandas_result_format_in_checkpoint_pk_defined_one_expectation_basic_output(
    in_memory_runtime_context,
    batch_request_for_pandas_unexpected_rows_and_index,
    reference_checkpoint_config_for_unexpected_column_names,
    expectation_config_expect_column_values_to_be_in_set,
):
    dict_to_update_checkpoint: dict = {
        "result_format": {
            "result_format": "BASIC",
            "unexpected_index_column_names": ["pk_1"],
        }
    }
    context: DataContext = _add_expectations_and_checkpoint(
        data_context=in_memory_runtime_context,
        checkpoint_config=reference_checkpoint_config_for_unexpected_column_names,
        expectations_list=[expectation_config_expect_column_values_to_be_in_set],
        dict_to_update_checkpoint=dict_to_update_checkpoint,
    )

    result: CheckpointResult = context.run_checkpoint(
        checkpoint_name="my_checkpoint",
        expectation_suite_name="animal_names_exp",
        batch_request=batch_request_for_pandas_unexpected_rows_and_index,
    )
    evrs: List[ExpectationSuiteValidationResult] = result.list_validation_results()
    first_result_full_list = evrs[0]["results"][0]["result"].get(
        "unexpected_index_list"
    )
    assert not first_result_full_list
    first_result_partial_list = evrs[0]["results"][0]["result"].get(
        "partial_unexpected_index_list"
    )
    assert not first_result_partial_list


@pytest.mark.integration
def test_sql_result_format_in_checkpoint_pk_defined_one_expectation_summary_output(
    data_context_with_connection_to_animal_names_db,
    reference_sql_checkpoint_config_for_unexpected_column_names,
    expectation_config_expect_column_values_to_be_in_set,
):
    """
    What does this test?
        - unexpected_index_column defined in Checkpoint only.
        - SUMMARY output, which means we have `partial_unexpected_index_list` only
        - 1 Expectations added to suite
    """
    dict_to_update_checkpoint: dict = {
        "result_format": {
            "result_format": "COMPLETE",
            "unexpected_index_column_names": ["pk_1"],
        }
    }
    context: DataContext = _add_expectations_and_checkpoint(
        data_context=data_context_with_connection_to_animal_names_db,
        checkpoint_config=reference_sql_checkpoint_config_for_unexpected_column_names,
        expectations_list=[expectation_config_expect_column_values_to_be_in_set],
        dict_to_update_checkpoint=dict_to_update_checkpoint,
    )

    result: CheckpointResult = context.run_checkpoint(
        checkpoint_name="my_checkpoint",
    )
    print("helo")
