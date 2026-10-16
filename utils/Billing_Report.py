from rich import print  # Use this to print with color and nice format
from alm_ccm.task import TaskProperty
from alm_ccm.base import reference
from alm_ccm.__init__ import Project
from urllib.parse import urlparse
from utils.convert_lib import ConvertLib
from utils.dateverf import UserInputDateVerify
import os
import shutil
import re
import pandas
pandas.options.mode.chained_assignment = None  # default='warn' --> to suppress warning for modifying data frame with calculation purpose
from typing import List
from datetime import datetime, timezone
import argparse
import pytz
from utils.ALM_Management import ALMManagement
from difflib import get_close_matches
import xml.etree.ElementTree as ET
import http.client
import base64
import sys
import calendar
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed



RGR_ID_FBL = "1023746"
GENERAL_CMT_FBL = "[FBL-MB-CN]"

WorkItems_Type = {
    'Defect'            : 'defect',
    'Problem'           : 'com.bosch.rtc.configuration.workitemtype.type.problem',
    'Review'            : 'com.bosch.rtc.configuration.workitemtype.type.review',
    'Defect Fix'        : 'com.bosch.rtc.configuration.workitemtype.type.defectfix',
    'Task'              : 'task',
    'issue'             : 'issue',
    'Milestone'         : 'com.ibm.team.workitem.workItemType.milestone',
    'Release'           : 'com.bosch.rtc.configuration.workitemtype.type.release',
    'Meeting'           : 'com.bosch.rtc.configuration.workitemtype.type.meeting',
    'Delivery'          : 'com.bosch.rtc.configuration.workitemtype.type.delivery',
    'Relevant Stream'   : 'com.bosch.rtc.configuration.workitemtype.type.relevantstream',
    'Defect Eval'       : 'com.bosch.rtc.configuration.workitemtype.type.defecteval',
    'Need'              : 'com.bosch.rtc.configuration.workitemtype.type.need',
    'Change Request'    : 'com.bosch.rtc.configuration.workitemtype.type.changerequest',
    'Adoption'          : 'com.bosch.rtc.configuration.workitemtype.type.adoption',
}
WorkItems_Attribute = {
    'Type'              : 'rtc_cm:type',
    'Task Type'         : 'rtc_ext:com.bosch.rtc.configuration.workitemtype.customattribute.tasktype',
    'Team Area'         : 'rtc_cm:teamArea',
    'Status'            : 'oslc_cm:status',  
}

class BillingReportHandling:
    def __init__(self, alm_url:str, userId:str, password:str) -> None:
        self.userId = userId
        self.password = password
        self._alm_host = urlparse(alm_url).netloc
        self.payload = ""
        self.alm_url = alm_url
        self.ALM = ALMManagement(alm_url, userId, password)
        self.project_database = None
        self.entity_dict_2_query = None
        self._title_cache = {}
        self._title_cache_lock = threading.Lock()
        
    def get_title_from_url(self, url, decryption_data=None):
        if decryption_data is None:
            # Parse the URL
            parsed_url = urlparse(url)
            # Extract the last part of the path
            return parsed_url.path.split('/')[-1]
        else:
            for key, value in decryption_data.items():
                if key in url:
                    return value
        return "can't found element"
    
    def extract_title_from_string(self, url_str, decryption_data=None):
        # Extract the URL using a regular expression
        url_match = re.search(r"uri='(.*?)'", url_str)
        if url_match:
            url = url_match.group(1)
            # Get the title from the URL
            return self.get_title_from_url(url, decryption_data)
        return "URL not found in the string"

    def find_mcr_ids(self, input_string):
        """
        Extracts MCR IDs from the given input string.

        An MCR ID is defined as a string that matches the format:
        BM-XXXXXXXX_XXX (ignores case for 'BM').

        Args:
            input_string (str): The string to search for MCR IDs.

        Returns:
            list: A list of extracted MCR IDs.
        """
        # Define the regex pattern for an MCR ID
        pattern = r'\b[Bb][Mm]-\d{8}_\d{3}\b'

        # Use re.findall to extract all matches
        mcr_ids = re.findall(pattern, input_string)

        # print error if multiple MCR ID found
        if (len(mcr_ids) > 1):
            print(f"multiple MCR in project: {mcr_ids}")
            return mcr_ids
        elif len(mcr_ids) == 1:
            if "bm" in mcr_ids[0]:
                return mcr_ids[0].replace("bm", "BM")
        else:
            return "N/A"
        # should not hit here
        return "N/A"

    def fetch_title_from_url(self, http_path: str):
        with self._title_cache_lock:
            if http_path in self._title_cache:
                return self._title_cache[http_path]

        encoded_credentials = base64.b64encode(f"{self.userId}:{self.password}".encode('utf-8')).decode('utf-8')
        headers = {
            "User-Agent": "Thunder Client (https://www.thunderclient.com)",
            "Accept": "application/xml",
            "OSLC-Core-Version": "2.0",
            "Authorization": f"Basic {encoded_credentials}",
        }
        url_path = urlparse(http_path).path

        title = None
        for attempt in range(3):
            try:
                conn = http.client.HTTPSConnection(self._alm_host)
                conn.request("GET", url_path, self.payload, headers)
                response = conn.getresponse()
                response_data = response.read()
                conn.close()

                root = ET.fromstring(response_data)
                namespaces = {'dcterms': 'http://purl.org/dc/terms/'}
                title_element = root.find('.//dcterms:title', namespaces)
                if title_element is not None:
                    title = title_element.text
                break

            except ET.ParseError as e:
                title = f"XML Parsing Error: {e}"
                time.sleep(2 ** attempt)

            except http.client.HTTPException as e:
                title = f"HTTP Request Error: {e}"
                time.sleep(2 ** attempt)

            except Exception as e:
                title = f"An unexpected error occurred: {e}"
                time.sleep(2 ** attempt)

        with self._title_cache_lock:
            self._title_cache[http_path] = title
        return title

    def get_general_comments(self, http_path: str, item_shortid: str):
        genernal_comment = "[ERROR] Fetching information failed"
        planned_for_title = self.fetch_title_from_url(http_path)
        if "error" in planned_for_title.lower():
            return genernal_comment
        else: 
            return GENERAL_CMT_FBL +" "+ planned_for_title+ "_" + item_shortid


    def get_project_title_by_area(self, area: str, projects: List[Project]) -> str:
        for project in projects:
            if project.area == area:
                return project.title
        return ""
             
    def query_billing_WI(self,WI_type, entity_id, billing_dict):   
        selection = [
            TaskProperty.closedate,
            TaskProperty.shortid,
            TaskProperty.dcterms__type,
            TaskProperty.contributor,
            TaskProperty.title,
            TaskProperty.subject,
            TaskProperty.timespent,
            TaskProperty.plannedfor
        ]
        # query and save wi to database    
        # set condition query
        clause_1 = TaskProperty.contributor == reference(f'{self.alm_url}/jts/users/{entity_id.lower()}')
        start_info = {
            'start_d':billing_dict['billing_time_info'][0].split('/')[0],
            'start_m':billing_dict['billing_time_info'][0].split('/')[1],
            'start_y':billing_dict['billing_time_info'][0].split('/')[2]
        }
        end_info = {
            'end_d':billing_dict['billing_time_info'][1].split('/')[0],
            'end_m':billing_dict['billing_time_info'][1].split('/')[1],
            'end_y':billing_dict['billing_time_info'][1].split('/')[2]
        }
        clause_2 = TaskProperty.closedate >= datetime(int(start_info['start_y']), int(start_info['start_m']), int(start_info['start_d']), 0, 0, 0, 0, tzinfo=timezone.utc)
        clause_3 = TaskProperty.closedate <= datetime(int(end_info['end_y']), int(end_info['end_m']), int(end_info['end_d']), 0, 0, 0, 0, tzinfo=timezone.utc)
        clause_4 = f' and {WorkItems_Attribute["Type"]}="{WI_type}"'
        where_clause = clause_1 & clause_2 & clause_3
        where_clause.value += clause_4
        return self.ALM.query_wi(where_clause, selection, float('inf'))

    def split_into_billing_date_ranges(self, time_info: list) -> list[dict]:
        months = []
        if len(time_info) > 1:
            start_m, start_y = map(int, time_info[0].split("/"))
            end_m, end_y = map(int, time_info[1].split("/"))
            current_m, current_y = start_m, start_y
            while (current_y, current_m) <= (end_y, end_m):
                months.append((current_m, current_y))
                current_m += 1
                if current_m > 12:
                    current_m = 1
                    current_y += 1
        elif len(time_info) == 1:
            m, y = map(int, time_info[0].split("/"))
            months.append((m, y))

        ranges = []
        for (m, y) in months:
            prev_m = m - 1 if m > 1 else 12
            prev_y = y if m > 1 else y - 1
            ranges.append({
                'month': f"{m}/{y}",
                'billing_time_info': [f"21/{prev_m}/{prev_y}", f"21/{m}/{y}"]
            })
        return ranges

    def _build_row(self, result, entity_name):
        if ConvertLib.convert_milliseconds_to_hours(result.timespent) <= 0:
            return None
        gen_comment = self.get_general_comments(result.plannedfor.uri, result.shortid)
        return [
            str(ConvertLib.convert_to_GMT7(result.closedate).strftime("%Y")),   # Column: Year
            str(ConvertLib.convert_to_GMT7(result.closedate).strftime("%m")),   # Column: Month
            str(ConvertLib.convert_to_GMT7(result.closedate).strftime("%d")),   # Column: Day
            result.dcterms__type,                                               # Column: Type
            entity_name,                                                        # Column: Full Name
            result.title,                                                       # Column: Summary
            self.find_mcr_ids(result.subject),                                  # Column: MCR-ID
            None,                                                               # Column: Task-ID -> to be blank as requested
            RGR_ID_FBL,                                                         # Column: RGR-ID
            None,                                                               # Column: Kind of activity
            result.shortid,                                                     # Column: RQMS-No
            gen_comment,                                                        # Column: General comments
            ConvertLib.convert_milliseconds_to_hours(result.timespent),         # Column: Hours
            result.shortid + " " + gen_comment                                  # Column: Additional info
        ]

    def generate_task_billing_report_by_PA(self, database, output_path, time_info):
        wi_filter = [WorkItems_Type["Task"], WorkItems_Type["Review"]]
        for entity_dict in self.entity_dict_2_query:
            try:
                query_result = []
                total_queries = 0
                user_msg = f"[DONE] Billing query for {entity_dict['Entity_Id']} - {entity_dict['Name']}"
                billing_dict_list = self.split_into_billing_date_ranges(time_info)
                t_query_start = time.perf_counter()
                for wi_type in wi_filter:
                    for billing_dict in billing_dict_list:
                        query = self.query_billing_WI(wi_type, entity_dict['Entity_Id'], billing_dict)
                        query_result.append(query)
                        total_queries = total_queries + len(query)
                t_query = time.perf_counter() - t_query_start
                print(f"\r{user_msg} - Total queries: {total_queries}")

                t_process_start = time.perf_counter()
                all_results = [r for batch in query_result for r in batch]
                with ThreadPoolExecutor(max_workers=16) as executor:
                    futures = [executor.submit(self._build_row, r, entity_dict['Name']) for r in all_results]
                    for future in as_completed(futures):
                        row = future.result()
                        if row is not None:
                            database.append(row)
                t_process = time.perf_counter() - t_process_start
                print(f"[TIME] {entity_dict['Entity_Id']} | Query: {t_query:.2f}s | Process: {t_process:.2f}s | Total: {t_query + t_process:.2f}s")
            except Exception as e:
                print(f"[ERROR] Skipping {entity_dict['Entity_Id']} - {entity_dict['Name']}: {e}")
                continue
            
    def process_combined_df(self, data_frame, time_info, output_path):
        df = pandas.DataFrame(data_frame)
        df = df.drop_duplicates()

        new_header = df.iloc[0]
        df = df[1:]
        df.columns = new_header
        df.reset_index(drop=True, inplace=True)
        df['Day'] = pandas.to_numeric(df['Day'], errors='coerce')
        df['Month'] = pandas.to_numeric(df['Month'], errors='coerce')
        df['Hours'] = pandas.to_numeric(df['Hours'], errors='coerce')

        billing_ranges = self.split_into_billing_date_ranges(time_info)
        result_list = []
        month_meta = []  # stores (month_int, year_int) per entry for pivot ordering and sheet naming

        for entry in billing_ranges:
            m, y = map(int, entry['month'].split("/"))
            start_day, start_m, start_y = map(int, entry['billing_time_info'][0].split("/"))
            end_day, end_m, end_y = map(int, entry['billing_time_info'][1].split("/"))

            # Records from previous month on or after the 21st, rebilled into current month
            prev_rows = df[(df['Day'] >= start_day) & (df['Month'] == start_m)].copy()
            prev_rows['Month'] = m
            prev_rows['Year'] = str(y)

            # Records from current month up to and including the 20th
            curr_rows = df[(df['Day'] <= end_day) & (df['Month'] == end_m)].copy()

            month_df = pandas.concat([prev_rows, curr_rows])
            result_list.append(month_df)
            month_meta.append((m, y))

        combined_df = pandas.concat(result_list, ignore_index=True)
        selected_months = [m for m, _ in month_meta]

        pivot_table = pandas.pivot_table(
            combined_df,
            values='Hours',
            index='Full Name',
            columns='Month',
            aggfunc='sum',
            fill_value=0
        )
        existing_cols = [col for col in selected_months if col in pivot_table.columns]
        pivot_table = pivot_table[existing_cols]
        pivot_table['Grand Total'] = pivot_table.sum(axis=1)
        pivot_table.loc['Grand Total'] = pivot_table.sum(numeric_only=True)

        with pandas.ExcelWriter('FBL_VMMB_COEM_MasterBilling.xlsx', engine='openpyxl') as writer:
            pivot_table.to_excel(writer, sheet_name='Summary')
            for df_obj, (m, y) in zip(result_list, month_meta):
                df_dropped = df_obj.drop('Day', axis=1)
                sheet_name = f'FBL_MCR_MyTime_Mass_Upload_{calendar.month_abbr[m]}'
                df_dropped.to_excel(writer, sheet_name=sheet_name, index=False)
                
        os.makedirs(output_path, exist_ok=True)
        shutil.copy('FBL_VMMB_COEM_MasterBilling.xlsx', output_path)
        os.remove('FBL_VMMB_COEM_MasterBilling.xlsx')
        print("[DONE] Billing report generation completed..")


