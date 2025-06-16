from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .services.allegroconnector import AllegroConnector
from django.core.management import call_command
import os
import json

STATUS_FILE = os.path.join(settings.BASE_DIR, "task_status.json")


def _load_statuses():
    try:
        with open(STATUS_FILE, "r") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}


def _save_statuses(data):
    with open(STATUS_FILE, "w") as fh:
        json.dump(data, fh)


def register_task(task_name: str, task_id: str):
    data = _load_statuses()
    data[task_name] = {
        "task_id": task_id,
        "status": "PENDING",
        "last_run": None,
    }
    _save_statuses(data)


def update_task_status(task_name: str, task_id: str, status: str):
    data = _load_statuses()
    record = data.get(task_name, {})
    record.update({"task_id": task_id, "status": status})
    if status in {"SUCCESS", "FAILURE"}:
        record["last_run"] = timezone.now().isoformat()
    data[task_name] = record
    _save_statuses(data)


@shared_task(bind=True)
def export_allegro_catalogue_task(self):
    update_task_status("export_allegro_catalogue_task", self.request.id, "STARTED")
    try:
        connector = AllegroConnector()
        connector.get_allegro_access_token()
        catalogue = connector.download_catalogue()
        parsed = connector.parse_catalogue(catalogue)
        output_path = os.path.join(settings.BASE_DIR, "full_catalogue.xlsx")
        connector.export_to_xlsx(parsed, output_path)
        update_task_status(
            "export_allegro_catalogue_task",
            self.request.id,
            "SUCCESS",
        )
        return output_path
    except Exception:
        update_task_status(
            "export_allegro_catalogue_task",
            self.request.id,
            "FAILURE",
        )
        raise


@shared_task(bind=True)
def export_auctions_task(self):
    update_task_status("export_auctions_task", self.request.id, "STARTED")
    try:
        call_command("export_auctions")
        update_task_status("export_auctions_task", self.request.id, "SUCCESS")
        return os.path.join(settings.BASE_DIR, "auctions_export.xlsx")
    except Exception:
        update_task_status("export_auctions_task", self.request.id, "FAILURE")
        raise


def get_tasks_status():
    """Return status information for all known tasks."""
    from celery.result import AsyncResult

    data = _load_statuses()
    statuses = {}
    for task_name, info in data.items():
        task_id = info.get("task_id")
        result = AsyncResult(task_id) if task_id else None
        statuses[task_name] = {
            "task_id": task_id,
            "state": result.state if result else "UNKNOWN",
            "result": result.result if result else None,
            "date_done": getattr(result, "date_done", None) if result else None,
            "last_run": info.get("last_run"),
        }
    return statuses
