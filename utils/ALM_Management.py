from alm_ccm import ProjectClient, Client
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import requests

class ALMManagement:
    def __init__(self, alm_url:str, userId:str, password:str) -> None:
        self.alm_url = alm_url
        self.project_permission_area = []
        self.user_select_prj = None
        self.continue_processing = False
        self.__username = userId
        self.__password = password
        self.__project_area = None
        self.__client = None
        self.__prjclient = None
        
    def set_user_info(self, user_name,password, project_area):
        self.__username, self.__password = user_name, password
        self.__project_area = project_area or self.__project_area

    def get_current_prj_area(self):
        return self.__project_area
    
    def alm_connect(self):
        self.reset_project_client()
        is_connected = False
        self.__client = Client(base_url=self.alm_url, username=self.__username, password=self.__password)
        projects = self.__client.get_all_projects()
        self.project_permission_area.extend(projects)
        is_connected = self.get_permission_project_area(self.__project_area)
        return is_connected

        
    def get_permission_project_area(self, project_area):

        permission_found = False
        for prj_area in self.project_permission_area:
            if  project_area in prj_area.title:
                permission_found = True
                self.user_select_prj = {
                    "base_url": prj_area.title,
                    "project_area": prj_area.area
                }
                break
        if permission_found == False:
            self.user_select_prj.clear()
            self.reset_permission_project_area()

        self.continue_processing = bool(self.user_select_prj)
        return True if self.continue_processing else False

    def reset_permission_project_area(self):
        self.project_permission_area.clear()
    

    def project_area_connect(self, project_area):
        if self.__prjclient is not None:
            return
        if self.continue_processing == True:
            self.__prjclient = ProjectClient(
                base_url= self.alm_url,
                project_area= self.user_select_prj['project_area'],
                username= self.__username,
                password= self.__password
            )
        else:
            logging(f"no permission access for {project_area}")

    def reset_project_client(self):
        self.__prjclient = None
            
    def get_workitem_info(self, work_item_number):
        self.project_area_connect(self.__project_area)
        wi_obj = self.__prjclient.get_workitem(work_item_number)
        return wi_obj
    
    def query_wi(self, where_clause, selection, size):
        PAGE_SIZE = 250
        try:
            self.project_area_connect(self.__project_area)
            first_page = self.__prjclient.query_workitems(
                select    = selection,
                paging    = True,
                page_size = PAGE_SIZE,
                where     = where_clause)

            result_list = list(first_page.results)

            if first_page.next_page is None:
                return result_list

            total = min(first_page.total_count, size)
            start_indices = range(PAGE_SIZE, total, PAGE_SIZE)

            pages = [None] * len(start_indices)

            def fetch_page(idx, start_index):
                thread_client = ProjectClient(
                    base_url=self.alm_url,
                    project_area=self.user_select_prj['project_area'],
                    username=self.__username,
                    password=self.__password
                )
                return idx, thread_client.get_query_page(first_page, start_index)

            with ThreadPoolExecutor() as executor:
                futures = {executor.submit(fetch_page, i, si): i for i, si in enumerate(start_indices)}
                for future in as_completed(futures):
                    idx, page = future.result()
                    pages[idx] = page

            for page in pages:
                if page is not None:
                    result_list.extend(page.results)

            return result_list

        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTPError: {e}")
            logging.error(f"Response content: {e.response.content}")

    def is_user_member_of_project_area(self, user_id: str) -> bool:
        """Check if a user ID is a member of the current project area.

        Args:
            user_id (str): The user ID to check.

        Returns:
            bool: True if the user is a member, False otherwise.
        """
        if not self.user_select_prj:
            return False

        area = self.user_select_prj['project_area']
        url = urljoin(self.alm_url, f"ccm/process/project-areas/{area}/members/{user_id}")

        try:
            res = self.__client.session.get(url, headers={"Accept": "application/xml"})
            if res.status_code == 200:
                return True
            if res.status_code == 404:
                return False
            res.raise_for_status()
            return False
        except requests.exceptions.HTTPError as e:
            logging.error(f"Failed to check membership for {user_id} in area {area}: {e}")
            return False
