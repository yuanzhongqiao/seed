/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * Controller for the Update Labels modal window.
 * Manages applying labels to a single Property or Tax Lot, as
 * well as allowing for the creation of new labels.
 * The Property or Tax Lot ID is passed in as 'inventory_id', identified by
 * inventory_type="properties" or inventory_type="taxlots"
 */
angular.module('BE.seed.controller.update_item_labels_modal', []).controller('update_item_labels_modal_controller', [
  '$scope',
  '$log',
  '$uibModalInstance',
  'label_service',
  'inventory_ids',
  'inventory_type',
  'Notification',
  'spinner_utility',
  // eslint-disable-next-line func-names
  function ($scope, $log, $uibModalInstance, label_service, inventory_ids, inventory_type, notification, spinner_utility) {
    $scope.inventory_ids = inventory_ids;
    $scope.inventory_type = inventory_type;
    // keep track of status of service call
    $scope.loading = false;

    // An array of all available labels in the system.
    // These label objects should have the is_applied property set so
    // the modal can show the Remove button if necessary. (Populated
    // during init function below.)
    $scope.labels = [];

    // new_label serves as model for the "Create a new label" UI
    $scope.new_label = {};

    // list of colors for the create label UI
    $scope.available_colors = label_service.get_available_colors();

    /* Initialize the label props for a 'new' label */
    $scope.initialize_new_label = function () {
      $scope.new_label = {
        color: 'gray',
        label: 'default',
        name: '',
        show_in_list: true
      };
    };

    /* Create a new label based on user input */
    $scope.submitNewLabelForm = function (form) {
      $scope.createdLabel = null;
      if (form.$invalid) return;
      label_service.create_label($scope.new_label).then(
        (data) => {
          // promise completed successfully
          const createdLabel = data;

          // Assume that user wants to apply a label they just created
          // in this modal...
          createdLabel.is_checked_add = true;

          $scope.newLabelForm.$setPristine();
          $scope.labels.unshift(createdLabel);
          $scope.initialize_new_label();
        },
        (data) => {
          // reject promise
          // label name already exists
          if (data.message === 'label already exists') {
            alert('label already exists');
          } else {
            alert('error creating new label');
          }
        }
      );
    };

    /* Toggle the add button for a label */
    $scope.toggle_add = function (label) {
      if (label.is_checked_remove && label.is_checked_add) {
        label.is_checked_remove = false;
      }
    };

    /* Toggle the remove button for a label */
    $scope.toggle_remove = function (label) {
      if (label.is_checked_remove && label.is_checked_add) {
        label.is_checked_add = false;
      }
    };

    $scope.modified = () => Boolean(_.filter($scope.labels, 'is_checked_add').length || _.filter($scope.labels, 'is_checked_remove').length);

    /* User has indicated 'Done' so perform selected label operations */
    $scope.done = function () {
      $scope.waiting = true;
      spinner_utility.show();
      const addLabelIDs = _.chain($scope.labels).filter('is_checked_add').map('id').value()
        .sort();
      const removeLabelIDs = _.chain($scope.labels).filter('is_checked_remove').map('id').value()
        .sort();

      if (inventory_type === 'properties') {
        label_service.update_property_labels(addLabelIDs, removeLabelIDs, inventory_ids).then(
          (data) => {
            if (data.num_updated === 1) {
              notification.primary(`${data.num_updated} property updated.`);
            } else {
              notification.primary(`${data.num_updated} properties updated.`);
            }
            $uibModalInstance.close();
          },
          (data, status) => {
            $log.error('error:', data, status);
          }
        ).finally(() => spinner_utility.hide());

      } else if (inventory_type === 'taxlots') {
        label_service.update_taxlot_labels(addLabelIDs, removeLabelIDs, inventory_ids).then(
          (data) => {
            if (data.num_updated === 1) {
              notification.primary(`${data.num_updated} tax lot updated.`);
            } else {
              notification.primary(`${data.num_updated} tax lots updated.`);
            }
            $uibModalInstance.close();
          },
          (data, status) => {
            $log.error('error:', data, status);
          }
        ).finally(() => spinner_utility.hide());
      }
    };

    /* User has cancelled dialog */
    $scope.cancel = function () {
      // don't do anything, just close modal.
      $uibModalInstance.dismiss('cancel');
    };

    /* init: Gets the list of labels. Sets up new label object. */
    const init = function () {
      $scope.initialize_new_label();
      // get labels with 'is_applied' property by passing in current search state
      $scope.loading = true;
      label_service.get_labels(inventory_type, inventory_ids).then((labels) => {
        $scope.labels = labels;
        $scope.loading = false;
      });
    };

    init();
  }
]);
