{
 "name": "QC Quarantine Integrity",
 "report_type": "Script Report",
 "module": "Quality",
 "ref_doctype": "QC Inspection",
 "is_standard": "Yes",
 "filters": [
  {
   "fieldname": "company",
   "fieldtype": "Link",
   "label": "Company",
   "options": "Books Company"
  },
  {
   "fieldname": "check_type",
   "fieldtype": "Select",
   "label": "Check",
   "options": "\nOrphan Quarantine Stock\nUnauthorized Quarantine Movement",
   "default": ""
  }
 ],
 "doctype": "Report"
}