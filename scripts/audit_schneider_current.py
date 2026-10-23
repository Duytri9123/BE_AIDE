"""Run the source/file/pricebook audit for Schneider alone."""
import audit_abb_ls_chint_current as audit
import sys
audit.BRANDS={'Schneider Electric'}
audit.FOLDER_BRANDS={'Schneider':'Schneider Electric'}
audit.OUT=audit.ROOT/'docs/schneider-current-audit-2026-10-21'
if '--after' in sys.argv:audit.OUT=audit.ROOT/'docs/schneider-update-2026-10-21/after-audit'
if __name__=='__main__':audit.main()
