/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * directive sd-uploader: wraps Fine Uploader
 *   sourcetype: string - upon upload successful, send the sourcetype param to
 *                        the server to store the linked file
 *   eventfunc: callback function with three arguments: `message`, `filename`, `progress`
 *              `message` - string - options: "upload_submitted",
 *              "upload_in_progress", "upload_complete", "upload_error", and "invalid_extension"
 *              `filename` - string name of the file uploaded
 *              `progress` - JS object with keys `loaded` and `total` where
 *                           `loaded` / `total` * 100.0 is the percent uploaded
 *  importrecord - int or string - id of import record or dataset
 *
 */

const makeFileSystemUploader = (scope, element, allowed_extensions) => {
  const uploader = new qq.FineUploaderBasic({
    button: element[0],
    request: {
      endpoint: `/api/v3/upload/?organization_id=${scope.organizationId}`,
      paramsInBody: true,
      forceMultipart: true,
      customHeaders: {
        'X-CSRFToken': BE.csrftoken
      }
    },
    validation: {
      allowedExtensions: allowed_extensions
    },
    text: {
      fileInputTitle: '',
      uploadButton: scope.buttontext
    },
    retry: {
      enableAuto: true
    },
    iframeSupport: {
      localBlankPathPage: '/success.html'
    },
    /**
     * multiple: only allow one file to be uploaded at a time
     */
    multiple: false,
    maxConnections: 20,
    callbacks: {
      /**
       * onSubmitted: overloaded callback that calls the callback defined
       * in the element attribute. Passes as arguments to the callback
       * a message indicating upload has started, "upload_submitted", and
       * the filename.
       */
      onSubmitted(id, fileName) {
        scope.eventfunc({
          message: 'upload_submitted',
          file: {
            filename: fileName,
            source_type: scope.sourcetype
          }
        });
        const params = {
          csrf_token: BE.csrftoken,
          csrf_name: 'csrfmiddlewaretoken',
          csrf_xname: 'X-CSRFToken',
          import_record: scope.importrecord,
          file: fileName,
          source_type: scope.sourcetype,
          source_program: scope.sourceprog,
          source_program_version: scope.sourcever
        };

        uploader.setParams(params);
      },
      /**
       * onComplete: overloaded callback that calls the callback defined
       * in the element attribute unless the upload failed, which will
       * fire a window alert. Passes as arguments to the callback
       * a message indicating upload has completed, "upload_complete", and
       * the filename.
       */
      onComplete(id, fileName, responseJSON) {
        if (!responseJSON.success) {
          alert('Upload failed.');
        } else {
          scope.eventfunc({
            message: 'upload_complete',
            file: {
              filename: fileName,
              file_id: responseJSON.import_file_id,
              cycle_id: scope.sourceprog === 'PortfolioManager' && scope.$parent.useField ? 'year_ending' : scope.$parent.selectedCycle.id,
              source_type: scope.sourcetype,
              source_program: scope.sourceprog,
              source_program_version: scope.sourcever
            }
          });
        }
      },
      /**
       * onProgress: overloaded callback that calls the callback defined
       * in the element attribute. Passes as arguments to the callback
       * a message indicating upload is in progress, "upload_in_progress",
       * the filename, and a progress object with two keys: loaded - the
       * bytes of the file loaded, and total - the total number of bytes
       * for the file.
       */
      onProgress(id, fileName, loaded, total) {
        scope.eventfunc({
          message: 'upload_in_progress',
          file: {
            filename: fileName,
            source_type: scope.sourcetype
          },
          progress: {
            loaded,
            total
          }
        });
      },
      /**
       * onError: overloaded callback that calls the callback defined
       * in the element attribute. Primarily for non-conforming files
       * that return 400 from the backend and invalid file extensions.
       */
      onError(id, fileName, errorReason, xhr) {
        if (_.includes(errorReason, ' has an invalid extension.')) {
          scope.eventfunc({
            message: _.includes(allowed_extensions, 'geojson') ? 'invalid_geojson_extension' : 'invalid_extension'
          });
          return;
        }

        // Ignore this error handler if the network request hasn't taken place yet (e.g., invalid file extension)
        if (!xhr) {
          alert(errorReason);
          return;
        }

        let error = errorReason;
        try {
          const json = JSON.parse(xhr.responseText);
          if (_.has(json, 'message')) {
            error = json.message;
          }
        } catch (e) {
          // no-op
        }

        scope.eventfunc({
          message: 'upload_error',
          file: {
            filename: fileName,
            source_type: scope.sourcetype,
            error
          }
        });
      }
    }
  });
  return uploader;
};

const makeBuildingSyncUpdater = (scope, element, allowed_extensions) => {
  const uploader = new qq.FineUploaderBasic({
    button: element[0],
    request: {
      method: 'PUT',
      endpoint: `/api/v3/properties/${scope.importrecord}/update_with_building_sync/?cycle_id=${scope.cycleId}&organization_id=${scope.organizationId}`,
      inputName: 'file',
      paramsInBody: true,
      forceMultipart: true,
      customHeaders: {
        'X-CSRFToken': BE.csrftoken
      },
      params: {
        file_type: 1
      }
    },
    validation: {
      allowedExtensions: allowed_extensions
    },
    text: {
      fileInputTitle: '',
      uploadButton: scope.buttontext
    },
    retry: {
      enableAuto: false
    },
    iframeSupport: {
      localBlankPathPage: '/success.html'
    },
    /**
     * multiple: only allow one file to be uploaded at a time
     */
    multiple: false,
    maxConnections: 20,
    callbacks: {
      /**
       * onSubmitted: overloaded callback that calls the callback defined
       * in the element attribute. Passes as arguments to the callback
       * a message indicating upload has started, "upload_submitted", and
       * the filename.
       */
      onSubmitted(id, fileName) {
        scope.eventfunc({
          message: 'upload_submitted',
          file: {
            filename: fileName,
            source_type: scope.sourcetype
          }
        });
        const params = {
          csrf_token: BE.csrftoken,
          csrf_name: 'csrfmiddlewaretoken',
          csrf_xname: 'X-CSRFToken',
          file_type: 1,
          organization_id: scope.organizationId,
          cycle_id: scope.cycleId
        };

        uploader.setParams(params);
      },
      /**
       * onComplete: overloaded callback that calls the callback defined
       * in the element attribute unless the upload failed, which will
       * fire a window alert. Passes as arguments to the callback
       * a message indicating upload has completed, "upload_complete", and
       * the filename.
       */
      onComplete(id, fileName, responseJSON) {
        // Only handle success because error transition is in onError event handler
        if (responseJSON.status === 'success') {
          scope.eventfunc({
            message: 'upload_complete',
            file: {
              filename: fileName,
              view_id: _.get(responseJSON, 'data.property_view.id'),
              source_type: scope.sourcetype
            }
          });
        }
      },
      /**
       * onProgress: overloaded callback that calls the callback defined
       * in the element attribute. Passes as arguments to the callback
       * a message indicating upload is in progress, "upload_in_progress",
       * the filename, and a progress object with two keys: loaded - the
       * bytes of the file loaded, and total - the total number of bytes
       * for the file.
       */
      onProgress(id, fileName, loaded, total) {
        scope.eventfunc({
          message: 'upload_in_progress',
          file: {
            filename: fileName,
            source_type: scope.sourcetype
          },
          progress: {
            loaded,
            total
          }
        });
      },
      /**
       * onError: overloaded callback that calls the callback defined
       * in the element attribute. Primarily for non-conforming files
       * that return 400 from the backend and invalid file extensions.
       */
      onError(id, fileName, errorReason, xhr) {
        if (_.includes(errorReason, ' has an invalid extension.')) {
          scope.eventfunc({ message: 'invalid_xml_extension' });
          return;
        }

        // Ignore this error handler if the network request hasn't taken place yet (e.g., invalid file extension)
        if (!xhr) {
          alert(errorReason);
          return;
        }

        let error = errorReason;
        try {
          const json = JSON.parse(xhr.responseText);
          if (_.has(json, 'message')) {
            error = json.message;
          }
        } catch (e) {
          // no-op
        }

        scope.eventfunc({
          message: 'upload_error',
          file: {
            filename: fileName,
            source_type: scope.sourcetype,
            error
          }
        });
      }
    }
  });
  return uploader;
};

const makeESPMUpdater = (scope, element, allowed_extensions) => {
  const uploader = new qq.FineUploaderBasic({
    button: element[0],
    request: {
      method: 'PUT',
      endpoint: `/api/v3/properties/${scope.importrecord}/update_with_espm/?cycle_id=${scope.cycleId}&organization_id=${scope.organizationId}&mapping_profile_id=${scope.mappingProfileId}`,
      inputName: 'file',
      paramsInBody: true,
      forceMultipart: true,
      customHeaders: {
        'X-CSRFToken': BE.csrftoken
      },
      params: {}
    },
    validation: {
      allowedExtensions: allowed_extensions
    },
    text: {
      fileInputTitle: '',
      uploadButton: scope.buttontext
    },
    retry: {
      enableAuto: false
    },
    iframeSupport: {
      localBlankPathPage: '/success.html'
    },
    /**
     * multiple: only allow one file to be uploaded at a time
     */
    multiple: false,
    maxConnections: 20,
    callbacks: {
      /**
       * onSubmitted: overloaded callback that calls the callback defined
       * in the element attribute. Passes as arguments to the callback
       * a message indicating upload has started, "upload_submitted", and
       * the filename.
       */
      onSubmitted(id, fileName) {
        scope.eventfunc({
          message: 'upload_submitted',
          file: {
            filename: fileName,
            source_type: scope.sourcetype
          }
        });
        const params = {
          csrf_token: BE.csrftoken,
          csrf_name: 'csrfmiddlewaretoken',
          csrf_xname: 'X-CSRFToken',
          file_type: 1,
          organization_id: scope.organizationId,
          cycle_id: scope.cycleId
        };

        uploader.setParams(params);
      },
      /**
       * onComplete: overloaded callback that calls the callback defined
       * in the element attribute unless the upload failed, which will
       * fire a window alert. Passes as arguments to the callback
       * a message indicating upload has completed, "upload_complete", and
       * the filename.
       */
      onComplete(id, fileName, responseJSON) {
        // Only handle success because error transition is in onError event handler
        if (responseJSON.status === 'success') {
          scope.eventfunc({
            message: 'upload_complete',
            file: {
              filename: fileName,
              view_id: _.get(responseJSON, 'data.property_view.id'),
              source_type: scope.sourcetype
            }
          });
        }
      },
      /**
       * onProgress: overloaded callback that calls the callback defined
       * in the element attribute. Passes as arguments to the callback
       * a message indicating upload is in progress, "upload_in_progress",
       * the filename, and a progress object with two keys: loaded - the
       * bytes of the file loaded, and total - the total number of bytes
       * for the file.
       */
      onProgress(id, fileName, loaded, total) {
        scope.eventfunc({
          message: 'upload_in_progress',
          file: {
            filename: fileName,
            source_type: scope.sourcetype
          },
          progress: {
            loaded,
            total
          }
        });
      },
      /**
       * onError: overloaded callback that calls the callback defined
       * in the element attribute. Primarily for non-conforming files
       * that return 400 from the backend and invalid file extensions.
       */
      onError(id, fileName, errorReason, xhr) {
        if (_.includes(errorReason, ' has an invalid extension.')) {
          scope.eventfunc({ message: 'invalid_extension' });
          return;
        }

        // Ignore this error handler if the network request hasn't taken place yet (e.g., invalid file extension)
        if (!xhr) {
          alert(errorReason);
          return;
        }

        let error = errorReason;
        try {
          const json = JSON.parse(xhr.responseText);
          if (_.has(json, 'message')) {
            error = json.message;
          }
        } catch (e) {
          // no-op
        }

        scope.eventfunc({
          message: 'upload_error',
          file: {
            filename: fileName,
            source_type: scope.sourcetype,
            error
          }
        });
      }
    }
  });
  return uploader;
};

/* Inventory Document Uploader for files to attach to a property */
const makeDocumentUploader = (scope, element, allowed_extensions) => {
  const uploader = new qq.FineUploaderBasic({
    button: element[0],
    request: {
      method: 'PUT',
      endpoint: `/api/v3/properties/${scope.importrecord}/upload_inventory_document/?organization_id=${scope.organizationId}`,
      inputName: 'file',
      paramsInBody: true,
      forceMultipart: true,
      customHeaders: {
        'X-CSRFToken': BE.csrftoken
      },
      params: {
        file_type: 1
      }
    },
    validation: {
      allowedExtensions: allowed_extensions
    },
    text: {
      fileInputTitle: '',
      uploadButton: scope.buttontext
    },
    retry: {
      enableAuto: false
    },
    iframeSupport: {
      localBlankPathPage: '/success.html'
    },
    /**
     * multiple: only allow one file to be uploaded at a time
     */
    multiple: false,
    maxConnections: 20,
    callbacks: {
      /**
       * onSubmitted: overloaded callback that calls the callback defined
       * in the element attribute. Passes as arguments to the callback
       * a message indicating upload has started, "upload_submitted", and
       * the filename.
       */
      onSubmitted(id, fileName) {
        scope.eventfunc({
          message: 'upload_submitted',
          file: {
            filename: fileName,
            source_type: scope.sourcetype
          }
        });
        const extracted_filetype = fileName.split('.').pop();
        const params = {
          csrf_token: BE.csrftoken,
          csrf_name: 'csrfmiddlewaretoken',
          csrf_xname: 'X-CSRFToken',
          file_type: extracted_filetype,
          organization_id: scope.organizationId
        };

        uploader.setParams(params);
      },
      /**
       * onComplete: overloaded callback that calls the callback defined
       * in the element attribute unless the upload failed, which will
       * fire a window alert. Passes as arguments to the callback
       * a message indicating upload has completed, "upload_complete", and
       * the filename.
       */
      onComplete(id, fileName, responseJSON) {
        // Only handle success because error transition is in onError event handler
        if (responseJSON.status === 'success') {
          scope.eventfunc({
            message: 'upload_complete',
            file: {
              filename: fileName,
              view_id: _.get(responseJSON, 'data.property_view.id'),
              source_type: scope.sourcetype
            }
          });
        }
      },
      /**
       * onProgress: overloaded callback that calls the callback defined
       * in the element attribute. Passes as arguments to the callback
       * a message indicating upload is in progress, "upload_in_progress",
       * the filename, and a progress object with two keys: loaded - the
       * bytes of the file loaded, and total - the total number of bytes
       * for the file.
       */
      onProgress(id, fileName, loaded, total) {
        scope.eventfunc({
          message: 'upload_in_progress',
          file: {
            filename: fileName,
            source_type: scope.sourcetype
          },
          progress: {
            loaded,
            total
          }
        });
      },
      /**
       * onError: overloaded callback that calls the callback defined
       * in the element attribute. Primarily for non-conforming files
       * that return 400 from the backend and invalid file extensions.
       */
      onError(id, fileName, errorReason, xhr) {
        if (_.includes(errorReason, ' has an invalid extension.')) {
          scope.eventfunc({ message: 'invalid_extension' });
          return;
        }

        // Ignore this error handler if the network request hasn't taken place yet (e.g., invalid file extension)
        if (!xhr) {
          alert(errorReason);
          return;
        }

        let error = errorReason;
        try {
          const json = JSON.parse(xhr.responseText);
          if (_.has(json, 'message')) {
            error = json.message;
          }
        } catch (e) {
          // no-op
        }

        scope.eventfunc({
          message: 'upload_error',
          file: {
            filename: fileName,
            source_type: scope.sourcetype,
            error
          }
        });
      }
    }
  });
  return uploader;
};

const sdUploaderFineUploader = (scope, element /* , attrs, filename */) => {
  let uploader;
  if (scope.sourcetype === 'BuildingSyncUpdate') {
    uploader = makeBuildingSyncUpdater(scope, element, ['xml']);
  } else if (scope.sourcetype === 'ESPMUpdate') {
    uploader = makeESPMUpdater(scope, element, ['xlsx']);
  } else if (scope.sourcetype === 'GreenButton') {
    uploader = makeFileSystemUploader(scope, element, ['xml']);
  } else if (scope.sourcetype === 'SensorMetaData') {
    uploader = makeFileSystemUploader(scope, element, ['csv', 'xlsx']);
  } else if (scope.sourcetype === 'SensorReadings') {
    uploader = makeFileSystemUploader(scope, element, ['csv', 'xlsx']);
  } else if (scope.sourcetype === 'GeoJSON') {
    uploader = makeFileSystemUploader(scope, element, ['json', 'geojson']);
  } else if (scope.sourcetype === 'UploadFile') {
    uploader = makeDocumentUploader(scope, element, ['pdf', 'idf', 'osm', 'dxf']);
  } else {
    uploader = makeFileSystemUploader(scope, element, ['csv', 'xls', 'xlsx', 'zip', 'xml']);
  }
  return uploader;
};

// Test support
window.sdUploaderFineUploader = sdUploaderFineUploader;

angular.module('sdUploader', []).directive('sdUploader', () => ({
  scope: {
    cycleId: '=',
    eventfunc: '&',
    importrecord: '=',
    organizationId: '=',
    mappingProfileId: '=?',
    sourceprog: '@',
    sourcetype: '@',
    sourcever: '='
  },
  restrict: 'A',
  link: (scope, element, attrs) => {
    $(sdUploaderFineUploader(scope, element, attrs));
  }
}));
