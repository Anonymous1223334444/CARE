from django.urls import path
from .views import (
    PatientCreateAPIView,
    PatientConfirmAPIView,
    ActivateRedirectView,
    PatientCheckActiveAPIView,
    PatientListAPIView,
    PatientIndexingStatusView, 
    DocumentIndexingStatusView,
    DocumentRetryView
)

urlpatterns = [
    path('patients/', PatientCreateAPIView.as_view(), name='patient-create'),
    path('patients/list/', PatientListAPIView.as_view(), name='patient-list'),
    path('patients/confirm/', PatientConfirmAPIView.as_view(), name='patient-confirm'),
    path('patients/check-active/', PatientCheckActiveAPIView.as_view(), name='patient-check-active'),
    path('patients/activate/<uuid:token>/', ActivateRedirectView.as_view(), name='patient-activate'),
    path('patients/<int:patient_id>/indexing-status/', 
         PatientIndexingStatusView.as_view(), 
         name='patient-indexing-status'),
    path('documents/<int:document_id>/status/', 
         DocumentIndexingStatusView.as_view(), 
         name='document-status'),
    path('documents/<int:document_id>/retry/', 
     DocumentRetryView.as_view(), 
     name='document-retry'),
]