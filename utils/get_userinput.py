import pandas


INPUT_FILES = {
    "alm_06": r"input\alm_06_input.xlsx",
    "alm_28": r"input\alm_28_input.xlsx",
}


class GetUserInput:
    def __init__(self, server_key: str) -> None:
        """
        server_key: "alm_06" or "alm_28"
        """
        self.file_path = INPUT_FILES[server_key]

    def get_project_area_entities(self):
        """Read entity_id and project_area sheets and return {project_area: [{'Entity_Id': .., 'Name': ..}]}.
        Returns empty dict if either sheet has no valid data."""
        entities_df = pandas.read_excel(self.file_path, sheet_name="entity_id")
        entities_df = entities_df.dropna(subset=["Entity_Id", "Name"])

        areas_df = pandas.read_excel(self.file_path, sheet_name="project_area")
        areas_df = areas_df.dropna(subset=["Project_Area"])

        if entities_df.empty or areas_df.empty:
            return {}

        entities = [
            {"Entity_Id": str(row["Entity_Id"]).strip(), "Name": str(row["Name"]).strip()}
            for _, row in entities_df.iterrows()
        ]

        return {
            str(row["Project_Area"]).strip(): entities
            for _, row in areas_df.iterrows()
        }
