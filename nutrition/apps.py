from django.apps import AppConfig


class NutritionConfig(AppConfig):
    name = 'nutrition'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        import nutrition.signals
