import json

from django.core.management.base import BaseCommand
from django.conf import settings
from celery import Celery
from restkit import Resource

from corehq.util.soft_assert import soft_assert
from corehq.apps.hqadmin.utils import parse_celery_workers, parse_celery_pings

_soft_assert = soft_assert(
    to='{}@{}'.format('brudolph', 'dimagi.com'),
    exponential_backoff=False,
)


class Command(BaseCommand):
    help = "Kills stale celery workers"

    def handle(self, *args, **options):
        _kill_stale_workers()


def _kill_stale_workers():
    celery_monitoring = getattr(settings, 'CELERY_FLOWER_URL', None)
    if celery_monitoring:
        cresource = Resource(celery_monitoring, timeout=3)
        t = cresource.get("api/workers", params_dict={'status': True}).body_string()
        all_workers = json.loads(t)
        expected_running, expected_stopped = parse_celery_workers(all_workers)

        celery = Celery()
        celery.config_from_object(settings)
        worker_responses = celery.control.ping(timeout=10)
        pings = parse_celery_pings(worker_responses)

        hosts_to_stop = filter(lambda hostname: hostname in pings, expected_stopped)
        if hosts_to_stop:
            celery.control.broadcast('shutdown', destination=hosts_to_stop)
            _soft_assert(False, 'Used kill stale for: {}'.format(', '.join(hosts_to_stop)))
