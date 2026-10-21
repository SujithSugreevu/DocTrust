"""
URL configuration for DocTrust document and folder endpoints.

All endpoints require authentication + active EMPLOYEE role.
ADMIN accounts are explicitly denied by the IsEmployee permission.

Endpoint map:
  GET/POST   /api/documents/folders/                  FolderListCreateView
  GET/PATCH/DELETE /api/documents/folders/<uuid:pk>/  FolderDetailView
  GET/POST   /api/documents/                          DocumentListCreateView
  GET/PATCH  /api/documents/<uuid:pk>/                DocumentDetailView
  GET        /api/documents/<uuid:pk>/download/       DocumentDownloadView
  DELETE     /api/documents/<uuid:pk>/                DocumentDeleteView
  POST       /api/documents/<uuid:pk>/archive/        DocumentArchiveView (action=archive)
  POST       /api/documents/<uuid:pk>/restore/        DocumentArchiveView (action=restore)
  POST       /api/documents/<uuid:pk>/purge/          DocumentPurgeView
"""

from django.urls import path

from documents.views import (
    DocumentArchiveView,
    DocumentDeleteView,
    DocumentDetailView,
    DocumentDownloadView,
    DocumentListCreateView,
    DocumentPurgeView,
    FolderDetailView,
    FolderListCreateView,
)

urlpatterns = [
    # Folders - support both /api/folders/ and /api/documents/folders/
    path("folders/", FolderListCreateView.as_view(), name="folder-list-create"),
    path("folders/<uuid:pk>/", FolderDetailView.as_view(), name="folder-detail"),
    path("documents/folders/", FolderListCreateView.as_view(), name="doc-folder-list-create"),
    path("documents/folders/<uuid:pk>/", FolderDetailView.as_view(), name="doc-folder-detail"),

    # Documents
    path("documents/", DocumentListCreateView.as_view(), name="document-list-create"),
    path("documents/<uuid:pk>/", DocumentDetailView.as_view(), name="document-detail"),
    path("documents/<uuid:pk>/download/", DocumentDownloadView.as_view(), name="document-download"),
    path("documents/<uuid:pk>/delete/", DocumentDeleteView.as_view(), name="document-delete"),
    path("documents/<uuid:pk>/archive/", DocumentArchiveView.as_view(), {"action": "archive"}, name="document-archive"),
    path("documents/<uuid:pk>/restore/", DocumentArchiveView.as_view(), {"action": "restore"}, name="document-restore"),
    path("documents/<uuid:pk>/purge/", DocumentPurgeView.as_view(), name="document-purge"),
]
