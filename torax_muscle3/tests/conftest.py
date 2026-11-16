import os

DD_VERSION = "4.0.0"


def pytest_configure(config):
    # Every actor test JIT-compiles TORAX in a fresh subprocess; share the compiled
    # code between them (and between runs) through JAX's persistent cache.
    cache = getattr(config, "cache", None)
    if cache is not None:
        os.environ.setdefault("JAX_COMPILATION_CACHE_DIR", str(cache.mkdir("jax")))
        os.environ.setdefault("JAX_PERSISTENT_CACHE_MIN_COMPILE_TIME_SECS", "0")
