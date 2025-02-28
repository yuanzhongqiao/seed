/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.analyses', []).factory('analyses_service', [
  '$http',
  '$log',
  '$timeout',
  'user_service',
  'uploader_service',
  ($http, $log, $timeout, user_service, uploader_service) => {
    const get_analyses_for_org = (org_id) => $http.get(`/api/v3/analyses/?organization_id=${org_id}`).then((response) => response.data);

    const get_analyses_for_canonical_property = (property_id) => {
      const org = user_service.get_organization().id;
      return $http.get(`/api/v3/properties/${property_id}/analyses/?organization_id=${org}`).then((response) => response.data);
    };

    const get_analysis_for_org = (analysis_id, org_id) => $http.get(`/api/v3/analyses/${analysis_id}/?organization_id=${org_id}`).then((response) => response.data);

    const get_analysis_messages_for_org = (analysis_id, org_id) => $http.get(`/api/v3/analyses/${analysis_id}/messages/?organization_id=${org_id}`).then((response) => response.data);

    const get_analyses_messages_for_org = (org_id) => $http.get(`/api/v3/analyses/0/messages/?organization_id=${org_id}`).then((response) => response.data);

    const get_analysis_views_for_org = (analysis_id, org_id) => $http.get(`/api/v3/analyses/${analysis_id}/views/?organization_id=${org_id}`).then((response) => response.data);

    const get_analysis_view_for_org = (analysis_id, view_id, org_id) => $http.get(`/api/v3/analyses/${analysis_id}/views/${view_id}/?organization_id=${org_id}`).then((response) => response.data);

    const create_analysis = (name, service, configuration, property_view_ids) => {
      const organization_id = user_service.get_organization().id;
      return $http({
        url: '/api/v3/analyses/',
        method: 'POST',
        params: { organization_id, start_analysis: true },
        data: {
          name,
          service,
          configuration,
          property_view_ids
        }
      }).then((response) => response.data);
    };

    const start_analysis = (analysis_id) => {
      const organization_id = user_service.get_organization().id;
      return $http({
        url: `/api/v3/analyses/${analysis_id}/start/`,
        method: 'POST',
        params: { organization_id }
      })
        .then((response) => response.data)
        .catch((response) => response.data);
    };

    const stop_analysis = (analysis_id) => {
      const organization_id = user_service.get_organization().id;
      return $http({
        url: `/api/v3/analyses/${analysis_id}/stop/`,
        method: 'POST',
        params: { organization_id }
      })
        .then((response) => response.data)
        .catch((response) => response.data);
    };

    const delete_analysis = (analysis_id) => {
      const organization_id = user_service.get_organization().id;
      return $http({
        url: `/api/v3/analyses/${analysis_id}/`,
        method: 'DELETE',
        params: { organization_id }
      })
        .then((response) => response.data)
        .catch((response) => response.data);
    };

    const get_summary = (cycle_id) => {
      const organization_id = user_service.get_organization().id;
      return $http({
        url: '/api/v3/analyses/stats',
        method: 'GET',
        params: { organization_id, cycle_id }
      })
        .then((response) => response.data)
        .catch((response) => response.data);
    };

    const verify_token = (organization_id) => $http({
      url: '/api/v3/analyses/verify_better_token/',
      method: 'GET',
      params: { organization_id }
    })
      .then((response) => response.data)
      .catch((response) => response.data);

    const get_progress_key = (analysis_id) => {
      const organization_id = user_service.get_organization().id;
      return $http({
        url: `/api/v3/analyses/${analysis_id}/progress_key/`,
        method: 'GET',
        params: { organization_id }
      })
        .then((response) => response.data)
        .catch((response) => response.data);
    };

    /**
     * check_progress_loop: polls progress data of an analysis
     *
     * @param {obj} {id, status}: object containing id and status of the analysis to poll
     * @param {async fn} status_update_callback: called every time a progress data is completed. Provided one parameter, analysis id
     * @param {fn} no_current_task_callback: called when there are no more progress data for the analysis. Provided one parameter, analysis id
     * @returns {fn}: a function which when called stops the polling
     */
    const check_progress_loop = ({ id, status }, status_update_callback, no_current_task_callback) => {
      // These statuses are assumed to have no progress data
      const NOT_ACTIVE_STATUSES = ['Pending Creation', 'Ready', 'Completed', 'Stopped', 'Failed'];
      if (NOT_ACTIVE_STATUSES.indexOf(status) >= 0) {
        no_current_task_callback(id);
        return () => {};
      }

      // stop_func allows the caller of check_progress_loop to cancel the polling
      let stop = false;
      const stop_func = () => {
        stop = true;
      };

      const POLLING_DELAY_MS = 1500;
      // recursive func for checking the progress of the analysis.
      // Gets the key for the current progress data, polls it until it finishes
      // then starts over by getting the new key for the next progress data.
      // Termination condition is when there's no progress data (i.e., no progress key
      // returned by the get_progress_key service)
      const get_key_and_check_progress = () => {
        get_progress_key(id).then((data) => {
          const { progress_key } = data;
          if (!progress_key) {
            // analysis isn't in a trackable state/status, stop checking
            no_current_task_callback(id);
            return;
          }

          const check_progress_loop = () => {
            $timeout(() => {
              if (stop) {
                return;
              }

              uploader_service
                .check_progress(progress_key)
                .then((data) => {
                  if (data.progress < 100) {
                    // keep polling, not done yet
                    check_progress_loop();
                  } else {
                    // progress data has finished
                    // let caller know the task has finished
                    status_update_callback(id).then(() => {
                      // start tracking the next task
                      get_key_and_check_progress(id, status_update_callback);
                    });
                  }
                })
                .catch(() => {
                  // yikes, something went wrong. Let the caller know the status
                  // probably changed and let's bail
                  status_update_callback(id).then(() => no_current_task_callback(id));
                });
            }, POLLING_DELAY_MS);
          };

          // kick off polling the progress data
          check_progress_loop();
        });
      };

      // finally kick off the polling process
      get_key_and_check_progress();
      return stop_func;
    };

    const analyses_factory = {
      get_analyses_for_org,
      get_analyses_for_canonical_property,
      get_analysis_for_org,
      get_analysis_messages_for_org,
      get_analyses_messages_for_org,
      get_analysis_views_for_org,
      get_analysis_view_for_org,
      create_analysis,
      start_analysis,
      stop_analysis,
      delete_analysis,
      get_summary,
      get_progress_key,
      check_progress_loop,
      verify_token
    };

    return analyses_factory;
  }
]);
