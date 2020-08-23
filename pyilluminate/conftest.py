def pytest_configure(config):
    config.addinivalue_line(
        "markers", "device: mark a tests that requires a real device"
    )
