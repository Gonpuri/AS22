from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("personal", views.PersonalViewSet, basename="personal")
router.register("designaciones", views.DesignacionViewSet, basename="designacion")
router.register("asignaciones", views.AsignacionDocenteViewSet, basename="asignacion")
router.register("preceptores", views.AsignacionPreceptorViewSet, basename="preceptor")

urlpatterns = router.urls
