import os
_bosch_hosts = "rb-alm-06-p.de.bosch.com,rb-alm-28-p.de.bosch.com"
_existing_no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
os.environ["NO_PROXY"] = ",".join(filter(None, [_existing_no_proxy, _bosch_hosts]))
os.environ["no_proxy"] = os.environ["NO_PROXY"]

from utils.Billing_Report import BillingReportHandling
from utils.KPI_Report import KPIReportHandling
from utils.get_userinput import GetUserInput
from utils.dateverf import DateVerify
from utils.auto_update import check_and_update
import getpass
import sys

ALM_06 = "https://rb-alm-06-p.de.bosch.com"
ALM_28 = "https://rb-alm-28-p.de.bosch.com"

def main():
# --- ALM Server Selection ---
    print("*************************************")
    print("*         SELECT ALM SERVER         *")
    print("* Option:                           *")
    print('* 1. ALM_06                         *')
    print("* 2. ALM_28                         *")
    print("*************************************")
    server_choice = None
    while server_choice not in ("1", "2"):
        server_choice = input("[INFO] Enter option (1 or 2): ").strip()
        if server_choice not in ("1", "2"):
            print("[ERROR] Invalid option, please enter 1 or 2.")

    if server_choice == "1":
        alm_url = ALM_06
        sheet_name = "alm_06"
        print("[INFO] Selected ALM server: ALM_06")
    else:
        alm_url = ALM_28
        sheet_name = "alm_28"
        print("[INFO] Selected ALM server: ALM_28")

    # --- Login ---
    print("*************************************")
    print("*            LOGIN                  *")
    print("*************************************")
    entity_id = input("[INFO] Enter Entity id: ")
    password = getpass.getpass("[INFO] Enter Password: ")

    billing_obj = BillingReportHandling(alm_url, entity_id, password)
    kpi_obj = KPIReportHandling(alm_url, entity_id, password)

    # --- Read input file for selected server ---
    user_input = GetUserInput(sheet_name)
    project_area_entities = user_input.get_project_area_entities()
    if not project_area_entities:
        print(f"[WARNING] No valid data found in input file for {sheet_name}. Exiting.")
        sys.exit(0)

    alm_obj = billing_obj.ALM

    # --- Billing Month ---
    print("**************************************")
    print("*            SELECT MONTH            *")
    print("* Option:                            *")
    print("* 1.Multiple months: m1/y1-m2/y2     *")
    print("* 2.Single month: m/y                *")
    print("**************************************")
    date_format_correct = False
    time_info = None
    while not date_format_correct:
        billing_month = input("[INFO] Enter month of billing: ")
        date_format_correct = DateVerify.validate(billing_month)
        if not date_format_correct:
            print("[ERROR] Wrong data format please try again.. ")
        else:
            time_info = billing_month.split("-")

    is_single_month = len(time_info) == 1

    # --- Report Type Selection ---
    print("*************************************")
    print("*        SELECT REPORT TYPE         *")
    print("* Option:                           *")
    print("* 1. MCR Mass upload report         *")
    print("* 2. KPI Status report              *")
    print("* 3. Both reports                   *")
    print("*************************************")
    report_choice = None
    while report_choice not in ("1", "2", "3"):
        report_choice = input("[INFO] Enter option (1, 2 or 3): ").strip()
        if report_choice not in ("1", "2", "3"):
            print("[ERROR] Invalid option, please enter 1, 2 or 3.")

    do_mcr = report_choice in ("1", "3")
    do_kpi = report_choice in ("2", "3")

  

    # --- Per project area processing ---
    mcr_header_df = [["Year", "Month", "Day", "Type", "Full Name", "Summary", "MCR-ID", "Task-ID", "RGR-ID", "Kind of activity", "RQMS-No", "General comments", "Hours","Addtional info"]]
    kpi_header_df = []
    out_path = r'_result'

    for project_area, entities in project_area_entities.items():
        print("*************************************")
        print("*            ALM CONNECT            *")
        print("*************************************")
        print(f"[INFO] Connecting to project area: {project_area}")
        alm_obj.set_user_info(entity_id, password, project_area)
        connect_status = alm_obj.alm_connect()
        if not connect_status:
            print(f"[WARNING] You don't have the permission to this project area: {project_area}")
            print("*************************************")
            continue

        print(f"[INFO] Connected to ALM - Project area: {project_area} --> [OK]")
        alm_obj.reset_permission_project_area()

        billing_obj.entity_dict_2_query = entities
        kpi_obj.entity_dict_2_query = entities
        kpi_obj.ALM = alm_obj

        print("*************************************")
        print(f"[INFO] Fetching data from project area: {project_area}..")

        if do_mcr:
            print(f"[INFO] Executing billing report generation..")
            billing_obj.generate_task_billing_report_by_PA(database=mcr_header_df, output_path=out_path, time_info=time_info)
            print(f"[DONE] Data queries for all inputs are completed..")


        if do_kpi:
            print(f"[INFO] Executing KPI report generation..")
            kpi_obj.generate_kpi_report_by_PA(header_df=kpi_header_df, project_area_name=project_area, time_info=time_info)
            print(f"[DONE] Data queries for all inputs are completed..")


        print("*************************************")
         
    if do_mcr:   
        print(f"[INFO] Executing Excel file generation..")
        billing_obj.process_combined_df(mcr_header_df, time_info, output_path=out_path)
    if do_kpi:
        print(f"[INFO] Executing Excel file generation..")
        kpi_obj.process_kpi_df(kpi_header_df, time_info, output_path=out_path)
if __name__ == "__main__":
    check_and_update()
    main()
