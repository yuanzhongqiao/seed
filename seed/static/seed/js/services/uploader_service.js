/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.uploader', []).factory('uploader_service', [
  '$http',
  '$q',
  '$timeout',
  'user_service',
  ($http, $q, $timeout, user_service) => {
    const uploader_factory = {};

    /**
     * create_dataset: AJAX request to create a new dataset/import record
     * should have a response like:
     *  {
     *       "status": "success",
     *       "import_record_id": 4,
     *       "import_record_name": "2013 city compliance dataset"
     *  }
     * or
     *  {
     *        "status": "error",
     *        "message": "name already in use"
     *  }
     */
    uploader_factory.create_dataset = (
      dataset_name // timeout here for testing
    ) => $http
      .post(
        '/api/v3/datasets/',
        {
          name: dataset_name
        },
        {
          params: {
            organization_id: user_service.get_organization().id
          }
        }
      )
      .then((response) => response.data);

    /**
     * validate_use_cases
     * This service call will simply call a view on the backend to validate
     * BuildingSync files with use cases
     * @param file_id: the pk of a ImportFile object we're going to save raw.
     */
    uploader_factory.validate_use_cases = (file_id) => {
      const org_id = user_service.get_organization().id;
      return $http
        .post(`/api/v3/import_files/${file_id}/validate_use_cases/?organization_id=${org_id.toString()}`)
        .then((response) => response.data)
        .catch((err) => {
          if (err.data.status === 'error') {
            return err.data;
          }
          // something unexpected happened... throw it
          throw err;
        });
    };

    /**
     * save_raw_data
     * This service call will simply call a view on the backend to save raw
     * data into BuildingSnapshot instances.
     * @param file_id: the pk of a ImportFile object we're going to save raw.
     * @param {string} cycle_id: the id of the cycle
     * @param {boolean} multiple_cycle_upload: whether records can be imported into multiple cycles
     */
    uploader_factory.save_raw_data = (file_id, cycle_id, multiple_cycle_upload = false) => $http
      .post(
        `/api/v3/import_files/${file_id}/start_save_data/`,
        {
          cycle_id,
          multiple_cycle_upload
        },
        {
          params: { organization_id: user_service.get_organization().id }
        }
      )
      .then((response) => response.data);

    /**
     * check_progress: gets the progress for saves, maps, and matches
     * @param progress_key: progress_key to grab the progress
     */
    uploader_factory.check_progress = (progress_key) => $http.get(`/api/v3/progress/${progress_key}/`).then((response) => {
      if (response.data.status === 'error') return $q.reject(response);
      return response.data;
    });

    function update_progress_bar_obj(data, { multiplier, offset, progress_bar_obj }) {
      const right_now = Date.now();
      progress_bar_obj.progress_last_checked = right_now;

      const new_progress_value = _.clamp(data.progress * multiplier + offset, 0, 100);
      const updating_progress = new_progress_value != progress_bar_obj.progress || progress_bar_obj.status_message != data.status_message;
      if (updating_progress) {
        progress_bar_obj.progress_last_updated = right_now;
      }

      if (data.total_records) {
        progress_bar_obj.total_records = data.total_records;
      }
      if (data.completed_records) {
        progress_bar_obj.completed_records = data.completed_records;
      }
      progress_bar_obj.progress = new_progress_value;
      progress_bar_obj.status_message = data.status_message;
    }

    /**
     * check_progress_loop: check loop to update the progress bar
     *
     * @param {string} progress_key: key
     * @param {number} offset: where to start the progress bar
     * @param {number} multiplier: multiplier for progress val
     * @param {fn} success_fn: function to call when progress is done
     * @param {fn} failure_fn: function to call when progress is done and the result was not success
     * @param {obj} progress_bar_obj: progress bar object, attr 'progress'
     *   is set with the progress
     */
    uploader_factory.check_progress_loop = (progress_key, offset, multiplier, success_fn, failure_fn, progress_bar_obj) => {
      uploader_factory.check_progress(progress_key).then((data) => {
        $timeout(() => {
          update_progress_bar_obj(data, { multiplier, offset, progress_bar_obj });
          if (data.progress < 100) {
            uploader_factory.check_progress_loop(progress_key, offset, multiplier, success_fn, failure_fn, progress_bar_obj);
          } else {
            success_fn(data);
          }
        }, 750);
      }, failure_fn);
    };

    uploader_factory.check_progress_loop_main_sub = (progress_argument, success_fn, failure_fn, sub_progress_argument = null) => {
      const { progress_key } = progress_argument;
      const sub_progress_key = sub_progress_argument ? sub_progress_argument.progress_key : null;

      const progress_list = [uploader_factory.check_progress(progress_key)];
      if (sub_progress_argument) progress_list.push(uploader_factory.check_progress(sub_progress_key));

      Promise.all(progress_list).then((values) => {
        check_and_update_progress(values);
      });

      function check_and_update_progress(data) {
        $timeout(() => {
          update_progress_bar_obj(data[0], progress_argument);
          if (data[0].progress < 100) {
            data.length > 1 ?
              (update_progress_bar_obj(data[1], sub_progress_argument), uploader_factory.check_progress_loop_main_sub(progress_argument, success_fn, failure_fn, sub_progress_argument)) :
              uploader_factory.check_progress_loop_main_sub(progress_argument, success_fn, failure_fn);
          } else {
            success_fn(data[0]);
          }
        }, 750);
      }
    };

    uploader_factory.pm_meters_preview = (file_id, org_id) => $http.get(`/api/v3/import_files/${file_id}/pm_meters_preview/`, { params: { organization_id: org_id } }).then((response) => response.data);

    uploader_factory.greenbutton_meters_preview = (file_id, org_id, view_id) => $http.get(`/api/v3/import_files/${file_id}/greenbutton_meters_preview/`, { params: { organization_id: org_id, view_id } }).then((response) => response.data);

    uploader_factory.sensors_preview = (file_id, org_id, view_id, data_logger_id) => $http.get(`/api/v3/import_files/${file_id}/sensors_preview/`, { params: { organization_id: org_id, view_id, data_logger_id } }).then((response) => response.data);

    uploader_factory.sensor_readings_preview = (file_id, org_id, view_id, data_logger_id) => $http.get(`/api/v3/import_files/${file_id}/sensor_readings_preview/`, { params: { organization_id: org_id, view_id, data_logger_id } }).then((response) => response.data);

    return uploader_factory;
  }
]);
