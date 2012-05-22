from django.core.urlresolvers import reverse
import pytz
from corehq.apps.reports.datatables import DataTablesHeader, DataTablesColumn
from corehq.apps.reports.standard import StandardDateHQReport, PaginatedHistoryHQReport
from dimagi.utils.timezones import utils as tz_utils
from couchforms.models import XFormError
from corehq.apps.receiverwrapper.fields import SubmissionErrorType,\
    SubmissionTypeField
from dimagi.utils.couch.pagination import FilteredPaginator, CouchFilter

def compare_submissions(x, y):
    # these are backwards because we want most recent to come first
    return cmp(y.received_on, x.received_on)

class SubmitFilter(CouchFilter):
    
    def __init__(self, domain, doc_type):
        self.domain = domain
        self.doc_type = doc_type
        self._kwargs = { "endkey":       [self.domain, "by_type", self.doc_type],
                         "startkey":     [self.domain, "by_type", self.doc_type, {}],
                         "reduce":       False,
                         "descending":   True }
        
    
    def get_total(self):
        return XFormError.view("receiverwrapper/all_submissions_by_domain", 
                               **self._kwargs).count()

    def get(self, count):
        # this is a hack, but override the doc type because there is an
        # equivalent doc type in the view
        def _update_doc_type(form):
            form.doc_type = self.doc_type
            return form 
        return [_update_doc_type(form) for form in \
                 XFormError.view("receiverwrapper/all_submissions_by_domain",
                                 include_docs=True,
                                 limit=count,
                                 **self._kwargs)]


class SubmissionErrorReport(PaginatedHistoryHQReport, StandardDateHQReport):
    name = "Raw Forms, Errors &amp; Duplicates"
    slug = "submit_errors"
    fields = ['corehq.apps.receiverwrapper.fields.SubmissionTypeField',
              # 'corehq.apps.reports.fields.GroupField',
              #'corehq.apps.reports.fields.DatespanField']
              ]
    
    def get_headers(self):
        headers = DataTablesHeader(DataTablesColumn("View Form"),
                                   DataTablesColumn("Username"),
                                   DataTablesColumn("Submit Time"),
                                   DataTablesColumn("Error Type"),
                                   DataTablesColumn("Error Message"))
        headers.no_sort = True
        return headers
    
    def get_parameters(self):
        self.submitfilter = SubmissionTypeField.get_filter_toggle(self.request)
        
    def get_report_context(self):
        super(SubmissionErrorReport, self).get_report_context()
        self.context['ajax_params'].append({'name': SubmissionTypeField.slug, 'value': [f.type for f in self.submitfilter if f.show]})
    
    def paginate_rows(self, skip, limit):
        EMPTY_ERROR = "No Error"
        EMPTY_USER = "No User"
        
        filters = [SubmitFilter(self.domain, toggle.doc_type) for toggle in self.submitfilter if toggle.show]
        paginator = FilteredPaginator(filters, compare_submissions)
        items = paginator.get(skip, limit)
        
        self._total_count = XFormError.view("receiverwrapper/all_submissions_by_domain", 
                                            startkey=[self.domain, "by_type"],
                                            endkey=[self.domain, "by_type", {}],
                                            reduce=False).count()
        self.count = paginator.total
        
        def _to_row(error_doc):
            def _fmt_url(doc_id):
                return "<a class='ajax_dialog' href='%s'>View Form</a>" % reverse('download_form', args=[self.domain, doc_id])
            
            def _fmt_date(somedate):
                time = tz_utils.adjust_datetime_to_timezone(somedate, pytz.utc.zone, self.timezone.zone)
                return time.strftime("%Y-%m-%d %H:%M:%S")
            
            return [_fmt_url(error_doc.get_id), 
                    error_doc.metadata.username if error_doc.metadata else EMPTY_USER,
                    _fmt_date(error_doc.received_on),
                    SubmissionErrorType.display_name_by_doc_type(error_doc.doc_type),
                    error_doc.problem or EMPTY_ERROR]
        
        return [_to_row(error_doc) for error_doc in items]