# Running Tests

## Prerequisites

Install pytest if not already installed:

```bash
pip install pytest
```

## Running Tests

### Run all tests
```bash
# From the backend directory
pytest technical_product_engine/tests/test_engine.py -v

# Or from the project root
python -m pytest backend/technical_product_engine/tests/test_engine.py -v
```

### Run specific test class
```bash
pytest technical_product_engine/tests/test_engine.py::TestModels -v
pytest technical_product_engine/tests/test_engine.py::TestLoaders -v
pytest technical_product_engine/tests/test_engine.py::TestDataAggregator -v
```

### Run specific test
```bash
pytest technical_product_engine/tests/test_engine.py::TestModels::test_campaign_creation -v
```

### Run with coverage (optional)
```bash
pip install pytest-cov
pytest technical_product_engine/tests/test_engine.py --cov=technical_product_engine --cov-report=html
```

## Test Coverage

The test suite covers:

### Models (TestModels)
- Campaign creation
- Client creation
- Product creation
- ClientProductContext creation with nested objects

### Loaders (TestLoaders)
- Loading campaigns from CSV
- Loading clients from CSV
- Loading products from CSV
- Loading potential from CSV
- Loading sales enriched from CSV with boolean handling
- Loading client-product features from CSV

### DataAggregator Service (TestDataAggregator)
- Initialization
- Loading all data from CSV files
- Getting data summary
- Filtering technical products
- Filtering all datasets by technical products
- Building client-product contexts (technical only)
- Building contexts for all products
- Including sales history in contexts

## Test Data

All tests use temporary CSV files created via pytest fixtures, so no external data files are required.
