from dtp.utils.config_loader import ConfigLoader
from dtp.irods.irods import IRODS
from dtp.gen3.auth import Auth
from dtp.gen3.querier import Querier

import pypacs


class Downloader(object):
    def __init__(self, data_storage_config, gen3_config=None, data_storage_type="pacs"):
        """
        Constructor

        :param data_storage_config: Path to the data storage (PACS or iRods) configuration file (json)
        :type data_storage_config: string
        :param gen3_config: (Optional)
        :type gen3_config: Path to the Gen3 configuration file (json)
        """
        self._data_storage_configs = ConfigLoader.load_from_json(data_storage_config)

        self._data_storage = self._data_storage_configs.get("storage")
        if data_storage_type:
            self._data_storage = data_storage_type
        else:
            self._data_storage = self._data_storage_configs.get("storage")

        if self._data_storage == "pacs":
            self._pacs_ip = self._data_storage_configs.get("pacs_ip")
            self._pacs_port = self._data_storage_configs.get("pacs_port")
            self._pacs_aec = self._data_storage_configs.get("pacs_aec")
            self._pacs_aet = self._data_storage_configs.get("pacs_aet")

            self._gen3_config = ConfigLoader.load_from_json(gen3_config)
            self._gen3_endpoint = self._gen3_config.get("gen3_endpoint")
            self._gen3_cred_file = self._gen3_config.get("gen3_cred_file")
            self._gen3_auth = Auth(self._gen3_endpoint, self._gen3_cred_file)
            self._gen3_queryer = Querier(self._gen3_auth)

        elif self._data_storage == "irods":
            self._irods = IRODS(data_storage_config)

    def download_dataset(self, dataset_id, dest):
        """
        Downloading dataset (including data from PACS/iRods & metadata from Gen3) in SDS format

        :param dataset_id: Dataset id/name on Gen3
        :type dataset_id: str
        :param dest: Path to the save folder
        :type dest: string
        """
        if self._data_storage == "pacs":
            self._download(dataset_id)
        elif self._data_storage == "irods":
            self._irods.download_data(data=dataset_id, save_dir=dest)

    def _download(self, dataset_id):
        gen3_query_string = """
        {
            experiment(submitter_id: "%s"){
                cases{
                    id
                    submitter_id,
                    subject_id,
                }
            }
        }
        """ % dataset_id

        results = self._queryer.graphql_query(gen3_query_string)
        datasets = results.get("experiment")

        study_uuids = list()
        for dataset in datasets:
            studies = dataset.get("cases")
            for study in studies:
                study_id = study.get("subject_id")
                study_uuid = study_id.replace("sub-", '')
                study_uuids.append(study_uuid)

        for study_uuid in study_uuids:
            pacs_query_settings = {
                "StudyInstanceUID": study_uuid
            }
            pypacs.move_files(server_ip=self._pacs_ip,
                              server_port=self._pacs_port,
                              aec=self._pacs_aec,
                              aet=self._pacs_aet,
                              query_settings=pacs_query_settings)