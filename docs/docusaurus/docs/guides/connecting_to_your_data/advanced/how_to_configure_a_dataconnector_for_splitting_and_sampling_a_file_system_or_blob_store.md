---
title: How to configure a DataConnector for splitting and sampling a file system or blob store
---
import Prerequisites from '../../connecting_to_your_data/components/prerequisites.jsx'
import TechnicalTag from '@site/docs/term_tags/_tag.mdx';

This guide will help you configure `Splitting` and `Sampling` for any files type data store (e.g., filesystem, cloud
blob storage) using a `Configured Asset Data Connector` (the same `Splitting` and `Sampling` configuration options can
be readily applied to an `Inferred Asset Data Connector`).

The `Splitting` and `Sampling` mechanisms provided by Great Expectations serve as additional tools for `Partitioning`
your data at various levels of granularity:
- `Splitting` provides the means of focusing the <TechnicalTag tag="batch" text="Batch" /> data on the values of certain dimensions of the data of interest.
- `Sampling` provides a means for reducing the amount of data in the retrieved batch to facilitate data analysis.

<Prerequisites>

- [Configured and loaded a Data Context](/docs/guides/setup/configuring_data_contexts/instantiating_data_contexts/how_to_quickly_instantiate_a_data_context)
- [Configured a Datasource and Data Connector](../../../terms/datasource.md)
- Reviewed [How to configure a DataConnector to introspect and partition a file system or blob store](../how_to_configure_a_dataconnector_to_introspect_and_partition_a_file_system_or_blob_store.md)

</Prerequisites>

This guide will use the <TechnicalTag tag="data_connector" text="Data Connector" /> named `configured_data_connector_name` that is part of the following
`Datasource` configuration as an example:

```python name="tests/integration/docusaurus/connecting_to_your_data/how_to_introspect_and_partition_your_data/files/yaml_example_complete.py datasource_yaml"
```

## Preliminary Steps

### 1. Instantiate your project's DataContext

Import these necessary packages and modules.

```python name="tests/integration/docusaurus/connecting_to_your_data/how_to_introspect_and_partition_your_data/files/yaml_example_complete.py imports"
```

Load your `DataContext` into memory using the `get_context()` method.

```python name="tests/integration/docusaurus/connecting_to_your_data/how_to_introspect_and_partition_your_data/files/yaml_example_complete.py get_context"
```

### 2. Configure your Datasource

Using the above example configuration, add in the path to a directory that contains your data.  Then run this code to
test your configuration:

```python name="tests/integration/docusaurus/connecting_to_your_data/how_to_introspect_and_partition_your_data/files/yaml_example_complete.py test_yaml_config"
```

Given that the `glob_directive` in the example configuration is `*.csv`, if you specified a directory containing CSV
files, then you will see them listed as `Available data_asset_names` in the output of `test_yaml_config()`.

Feel free to adjust your configuration and re-run `test_yaml_config()` as needed.

### 3. Save the Datasource configuration to your DataContext

Save the configuration into your `DataContext` by using the `add_datasource()` function.

```python name="tests/integration/docusaurus/connecting_to_your_data/how_to_introspect_and_partition_your_data/files/yaml_example_complete.py add_datasource"
```

## Splitting and Sampling

To configure `Splitting`, specify a dimension (i.e., `column_name` or `column_names`), the method of `Splitting`, and
parameters to be used by the specified `Splitting` method.

To configure `Sampling`, specify the method of `Sampling` and parameters to be used by the specified `Sampling` method.

```python name="tests/integration/docusaurus/connecting_to_your_data/how_to_introspect_and_partition_your_data/files/yaml_example_complete.py batch_request"
```

:::info
Currently, the configuration of `Splitting` and `Sampling` as part of the `YAML` configuration is not supported; it must
be done using `batch_spec_passthrough` as illustrated above.
:::

To customize the configuration for the present example, first, specify the `data_connector_query` to select the `Batch`
at the `Partitioning` level of granularity.

```python name="tests/integration/docusaurus/connecting_to_your_data/how_to_introspect_and_partition_your_data/files/yaml_example_complete.py batch_filter_parameters"
```

Next, specify `Splitting` and `Sampling` directives.

For the present example, we can split according to the "passenger_count" column with the focus on two-passenger rides:

```python name="tests/integration/docusaurus/connecting_to_your_data/how_to_introspect_and_partition_your_data/files/yaml_example_complete.py split_on_column_value passenger_count"
```

We can then obtain a random `10%` of the rows in the batch:

```python name="tests/integration/docusaurus/connecting_to_your_data/how_to_introspect_and_partition_your_data/files/yaml_example_complete.py sample_using_random 10 pct"
```

Finally, confirm the expected number of batches was retrieved and the reduced size of a batch (due to `Sampling`):

```python name="tests/integration/docusaurus/connecting_to_your_data/how_to_introspect_and_partition_your_data/files/yaml_example_complete.py sampling batch size"
```

## Additional Notes

Available `Splitting` methods and their configuration parameters:

Note: Splitter methods can be specified with or without a preceding underscore.

| Method                          | Parameters                                                                                                    | Returned Batch Data                                                                                                                                                                                                               |
|---------------------------------|---------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| split_on_whole_table            | N/A                                                                                                           | Identical to original                                                                                                                                                                                                             |
| split_on_column_value           | `column_name='col', batch_identifiers={ 'col': value }`                                                       | Rows where value of column_name is equal to the value specified                                                                                                                                                                   |
| split_on_year                   | `column_name='col'`                                                                                           | Rows where the year of a datetime column are equal to the specified value                                                                                                                                                         |
| split_on_year_and_month         | `column_name='col'`                                                                                           | Rows where the year and month of a datetime column are equal to the specified value                                                                                                                                               |
| split_on_year_and_month_and_day | `column_name='col'`                                                                                           | Rows where the year, month and day of a datetime column are equal to the specified value                                                                                                                                          |
| split_on_date_parts             | `column_name='col', date_parts='<list[DatePart]>'`                                                            | Rows where the date parts of a datetime column are equal to the specified value. Date parts can be specified as DatePart objects or as their string equivalent e.g. "year", "month", "week", "day", "hour", "minute", or "second" |
| split_on_divided_integer        | `column_name='col', divisor=<int>, batch_identifiers={ 'col': matching_divisor }`                             | Rows where value of column_name divided (using integer division) by the given divisor are equal to matching_divisor provided for the column_name specified                                                                       |
| split_on_mod_integer            | `column_name='col', mod=<int>, batch_identifiers={ 'col': matching_mod_value }`                               | Rows where value of column_name divided (using modular division) by the given mod are equal to matching_mod_value provided for the column_name specified                                                                          |
| split_on_multi_column_values    | `column_names='<list[col]>', batch_identifiers={ 'col_0': value_0, 'col_1': value_1, 'col_2': value_2, ... }` | Rows where values of column_names are equal to values corresponding to each column name as specified                                                                                                                              |
| split_on_converted_datetime     | `column_name='col', date_format_string=<'%Y-%m-%d'>, batch_identifiers={ 'col': matching_string }`            | Rows where value of column_name converted to datetime using the given date_format_string are equal to matching string provided for the column_name specified                                                                      |
| split_on_hashed_column          | `column_name='col', hash_digits=<int>, hash_function_name=<'md5'> batch_identifiers={ 'hash_value': value }`  | Rows where value of column_name hashed (using specified hash_function_name) and retaining the stated number of hash_digits are equal to hash_value provided for the column_name specified                                          |


Available `Sampling` methods and their configuration parameters:

Note: Sampling methods can be specified with or without a preceding underscore.

| Method               | Parameters                                                                           | Returned Batch Data                                                                                                         |
|----------------------|--------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| sample_using_random | `p=fraction`                                                                         | Rows selected at random, whose number amounts to selected fraction of total number of rows in batch                         |
| sample_using_mod    | `column_name='col', mod=<int>`                                                       | Take the mod of named column, and only keep rows that match the given value                                                 |
| sample_using_a_list | `column_name='col', value_list=<list[val]>`                                          | Match the values in the named column against value_list, and only keep the matches                                          |
| sample_using_hash   | `column_name='col', hash_digits=<int>, hash_value=<str>, hash_function_name=<'md5'>` | Hash the values in the named column (using specified hash_function_name), and only keep rows that match the given hash_value |



To view the full script used in this page, see it on GitHub:

- [yaml_example_complete.py](https://github.com/great-expectations/great_expectations/blob/develop/tests/integration/docusaurus/connecting_to_your_data/how_to_introspect_and_partition_your_data/files/yaml_example_complete.py)
