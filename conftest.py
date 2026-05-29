from hypothesis import HealthCheck, settings


settings.register_profile(
    "scripty",
    suppress_health_check=[HealthCheck.data_too_large],
)
settings.load_profile("scripty")
