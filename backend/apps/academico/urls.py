from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("orientaciones", views.OrientacionViewSet)
router.register("anios", views.AnioViewSet)
router.register("divisiones", views.DivisionViewSet)
router.register("materias", views.MateriaViewSet)

urlpatterns = router.urls
