/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.delete_document_modal', []).controller('delete_document_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'inventory_service',
  'view_id',
  'file',
  // eslint-disable-next-line func-names
  function ($scope, $state, $uibModalInstance, inventory_service, view_id, file) {
    $scope.file = file;
    $scope.view_id = view_id;
    $scope.delete_document = () => {
      inventory_service.delete_inventory_document($scope.view_id, $scope.file.id).then(() => {
        $state.reload();
        $uibModalInstance.close();
      });
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss();
    };
  }
]);
