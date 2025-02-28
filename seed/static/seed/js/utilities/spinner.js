/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 * :author - Nicholas Serra <nickserra@gmail.com>
 *
 * Eventually this may need to be refactored into a singleton factory that
 * instantiates new objects (spinners). - nicholasserra
 */
angular.module('BE.seed.utility.spinner', []).factory('spinner_utility', [
  () => {
    const spinner_utility = {};
    let _spinner;

    spinner_utility.show = (params, target) => {
      const refresh = !!(params || target);
      target = target || $('.display')[0];

      if (!_spinner) {
        _spinner = new Spinner(params).spin(target);
      } else if (_spinner && refresh) {
        _spinner.stop();
        _spinner = new Spinner(params).spin(target);
      } else {
        _spinner.spin(target);
      }

      $('.page')[0].style.opacity = 0.4;
    };

    spinner_utility.hide = () => {
      if (_spinner) {
        _spinner.stop();
        $('.page')[0].style.opacity = 1;
      }
    };

    return spinner_utility;
  }
]);
