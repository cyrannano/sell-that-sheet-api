import os
import tempfile
from django.conf import settings
from django.http import FileResponse
from django.core.management import call_command
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status

from .services.rows_to_columns import rows_to_columns
from .tasks import export_allegro_catalogue_task, export_auctions_task


class ConvertRowsToColumnsView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response(
                {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as src:
            for chunk in uploaded.chunks():
                src.write(chunk)

        dst = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        try:
            rows_to_columns(src.name, dst.name)
            dst.seek(0)
            response = FileResponse(
                open(dst.name, "rb"), as_attachment=True, filename="converted.xlsx"
            )
        finally:
            os.unlink(src.name)
        return response


class ExportAllegroStartView(APIView):
    def post(self, request):
        task = export_allegro_catalogue_task.delay()
        return Response({"task_id": task.id})


class DownloadAllegroExportView(APIView):
    def get(self, request):
        path = os.path.join(settings.BASE_DIR, "full_catalogue.xlsx")
        if not os.path.exists(path):
            return Response(
                {"error": "File not found"}, status=status.HTTP_404_NOT_FOUND
            )
        return FileResponse(
            open(path, "rb"), as_attachment=True, filename="full_catalogue.xlsx"
        )


class ExportAuctionsView(APIView):
    def get(self, request):
        task = export_auctions_task.delay()
        return Response({"task_id": task.id})


class DownloadAuctionsExportView(APIView):
    def get(self, request):
        path = os.path.join(settings.BASE_DIR, "auctions_export.xlsx")
        if not os.path.exists(path):
            return Response(
                {"error": "File not found"}, status=status.HTTP_404_NOT_FOUND
            )
        return FileResponse(
            open(path, "rb"), as_attachment=True, filename="auctions_export.xlsx"
        )
